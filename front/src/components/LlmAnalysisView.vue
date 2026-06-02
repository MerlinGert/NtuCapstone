<template>
  <div class="llm-analysis-view">
    <div class="analysis-toolbar">
      <div>
        <div class="analysis-title">Reasoning Forest</div>
        <div class="analysis-subtitle">
          Findings hierarchy under top-level hypotheses, with agent patch findings overlaid.
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="export-btn" :disabled="loading || !canExportAnalysis" @click="exportAnalysis">
          Export JSON
        </button>
        <button
          v-if="!isImportedMode"
          class="refresh-btn"
          :disabled="loading || !sessionId"
          @click="refreshAnalysis"
        >
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
        <span v-else class="imported-mode-badge">Imported JSON</span>
      </div>
    </div>
    <div v-if="artifactSummary" class="artifact-summary">{{ artifactSummary }}</div>
    <div v-if="validationWarnings.length" class="validation-warnings">
      <div class="validation-warning-title">Graph warnings</div>
      <ul>
        <li v-for="warning in validationWarnings" :key="warning">{{ warning }}</li>
      </ul>
    </div>

    <div class="legend-block">
      <div class="legend-row legend-row-single">
        <span class="legend-item legend-hypothesis">Hypothesis</span>
        <span class="legend-item legend-derived-hypothesis">Derived Hypothesis</span>
        <span class="legend-item legend-user">User Finding</span>
        <span class="legend-item legend-patch">Agent Finding</span>
        <span class="legend-item relation-legend relation-supports">Supports</span>
        <span class="legend-item relation-legend relation-answers">Answers</span>
        <span class="legend-item relation-legend relation-refines">Refines</span>
        <span class="legend-item relation-legend relation-contradicts">Contradicts</span>
      </div>
    </div>

    <div v-if="loading" class="empty-state">Loading LLM analysis artifacts...</div>
    <div v-else-if="error" class="empty-state error-state">{{ error }}</div>
    <div v-else-if="!hasAnalysis" class="empty-state">
      No reasoning forest artifacts are available for this session yet.
    </div>
    <div v-else class="forest-grid">
      <section
        v-for="tree in forestTrees"
        :key="tree.instanceId || tree.id"
        class="hypothesis-tree"
      >
        <ReasoningNodeCard :node="tree" @select-node="selectedNode = $event" />
      </section>
    </div>

    <teleport to="body">
      <div
        v-if="selectedNode"
        class="detail-modal-overlay"
        @click.self="closeSelectedNode"
      >
        <div class="detail-modal" role="dialog" aria-modal="true" :aria-label="selectedNode.label">
          <div class="detail-header">
            <div class="detail-header-copy">
              <div class="detail-badges">
                <span class="detail-type" :class="selectedNodeTypeClass">{{ selectedNodeTypeLabel }}</span>
                <span
                  v-if="selectedNodeRelationLabel"
                  class="detail-relation"
                  :class="selectedNodeRelationClass"
                >
                  {{ selectedNodeRelationLabel }}
                </span>
              </div>
              <div class="detail-title">{{ selectedNode.label }}</div>
            </div>
            <button class="detail-close" @click="closeSelectedNode">Close</button>
          </div>
          <div class="detail-body" :class="{ 'detail-body-single': !selectedNodeImageGroups.length }">
            <div class="detail-text-panel">
              <dl class="detail-list">
                <template v-for="item in selectedNodeDetails" :key="item.key">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </template>
              </dl>
              <div v-if="selectedNodeInternalFindings.length" class="detail-findings-section">
                <div class="detail-section-title">Internal Findings</div>
                <div class="detail-findings-list">
                  <article
                    v-for="finding in selectedNodeInternalFindings"
                    :key="finding.key"
                    class="detail-finding-card"
                    :class="[finding.sourceClass, finding.relationClass]"
                  >
                    <div class="detail-finding-header">
                      <span
                        v-if="finding.relationLabel"
                        class="detail-finding-relation"
                        :class="finding.relationClass"
                      >
                        {{ finding.relationLabel }}
                      </span>
                      <div class="detail-finding-title">{{ finding.label }}</div>
                    </div>
                    <p v-if="finding.explanation" class="detail-finding-copy">{{ finding.explanation }}</p>
                    <p v-if="finding.evidenceSummary" class="detail-finding-copy">
                      {{ finding.evidenceSummary }}
                    </p>
                    <p v-if="finding.reasoningRole" class="detail-finding-copy">{{ finding.reasoningRole }}</p>
                  </article>
                </div>
              </div>
            </div>
            <div v-if="selectedNodeImageGroups.length" class="detail-images-panel">
              <div class="detail-images-title">Evidence Images</div>
              <div class="detail-images-grid">
                <a
                  v-for="group in selectedNodeImageGroups"
                  :key="group.image.url"
                  class="detail-image-link"
                  :href="group.image.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  <img :src="group.image.url" :alt="group.image.label" class="detail-image" />
                  <span class="detail-image-label">{{ group.image.label }}</span>
                  <span v-if="group.findings.length" class="detail-image-finding-list">
                    {{ group.findings.map((finding) => finding.label).join(' | ') }}
                  </span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script>
import ReasoningNodeCard from './ReasoningNodeCard.vue'
import {
  applyReasoningPatches,
  orderPatchLayers,
  projectGraphToDisplayForest,
  validateReasoningGraph,
} from '../reasoning-graph'

const ARTIFACT_UPDATE_EVENT = 'maniscope-session-artifact-updated'
const POLL_INTERVAL_MS = 5000

export default {
  name: 'LlmAnalysisView',
  components: {
    ReasoningNodeCard,
  },
  props: {
    sessionId: {
      type: String,
      default: '',
    },
    sessionMode: {
      type: String,
      default: 'specialized',
      validator: (value) => ['specialized', 'baseline'].includes(value),
    },
    active: {
      type: Boolean,
      default: true,
    },
    analysisPayload: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      loading: false,
      error: '',
      manifest: null,
      reasoningGraph: null,
      augmentedReasoningGraph: null,
      graphPatches: [],
      validationWarnings: [],
      displayTrees: [],
      selectedNode: null,
      loadStarted: false,
      lastManifestSignature: '',
      pollTimer: null,
    }
  },
  computed: {
    isImportedMode() {
      return Boolean(this.analysisPayload)
    },
    sessionApiBase() {
      return this.sessionMode === 'baseline' ? '/api/base/sessions' : '/api/sessions'
    },
    hasAnalysis() {
      return this.forestTrees.length > 0
    },
    canExportAnalysis() {
      return this.hasAnalysis || Boolean(this.reasoningGraph) || Boolean(this.augmentedReasoningGraph)
    },
    forestTrees() {
      return this.displayTrees
    },
    artifactSummary() {
      if (this.analysisPayload?.artifactSummary) return this.analysisPayload.artifactSummary
      const current = this.manifest?.current || {}
      const graphName = current.reasoningGraph?.name || this.manifest?.reasoningGraph?.name
      const patches = Array.isArray(current.patches)
        ? current.patches
        : Array.isArray(this.manifest?.patches)
          ? this.manifest.patches
          : []
      const names = [graphName, ...patches.map((patch) => patch.name)].filter(Boolean)
      if (!names.length) return ''
      return `Showing ${names.join(' + ')}`
    },
    selectedNodeDetails() {
      if (!this.selectedNode) return []
      const explanation = this.preferredExplanation(this.selectedNode)
      const support = this.supportingExplanation(this.selectedNode)
      const reasoning = this.reasoningNarrative(this.selectedNode)
      const relation = this.relationLabel(this.selectedNode.displayRelation || this.selectedNode.relation)
      return [
        {
          key: 'relation',
          label: 'Relation To Parent',
          value: relation,
        },
        {
          key: 'story',
          label: 'Story',
          value: explanation,
        },
        {
          key: 'support',
          label: 'Visual / Evidence Pattern',
          value: support,
        },
        {
          key: 'reasoning',
          label: 'Reasoning Link',
          value: reasoning,
        },
      ].filter((item) => item.value)
    },
    selectedNodeRelationName() {
      if (!this.selectedNode) return ''
      return this.normalizedRelation(this.selectedNode.displayRelation || this.selectedNode.relation)
    },
    selectedNodeTypeLabel() {
      if (!this.selectedNode) return ''
      if (this.selectedNode.type === 'Hypothesis' && this.selectedNode.source === 'patch') {
        return 'Derived Hypothesis'
      }
      if (this.selectedNode.type === 'Finding') {
        return this.selectedNode.source === 'patch' ? 'Agent Finding' : 'User Finding'
      }
      return this.selectedNode.type || 'Node'
    },
    selectedNodeTypeClass() {
      if (!this.selectedNode) return ''
      if (this.selectedNode.type === 'Hypothesis' && this.selectedNode.source === 'patch') {
        return 'detail-type-derived-hypothesis'
      }
      if (this.selectedNode.type !== 'Finding') return ''
      return this.selectedNode.source === 'patch' ? 'detail-type-agent-finding' : 'detail-type-user-finding'
    },
    selectedNodeRelationLabel() {
      if (!this.selectedNode) return ''
      return this.relationLabel(this.selectedNode.displayRelation || this.selectedNode.relation)
    },
    selectedNodeRelationClass() {
      return this.selectedNodeRelationName ? `relation-${this.selectedNodeRelationName}` : ''
    },
    selectedNodeInternalFindings() {
      if (!this.shouldShowInternalFindings(this.selectedNode)) return []
      return this.collectConcreteDescendantFindings(this.selectedNode)
    },
    selectedNodeImageGroups() {
      if (!this.selectedNode) return []
      if (this.selectedNodeInternalFindings.length > 0) {
        return this.groupFindingImages(this.selectedNodeInternalFindings)
      }
      const images = Array.isArray(this.selectedNode.evidenceImages)
        ? this.selectedNode.evidenceImages
        : []
      return images.map((image) => ({
        image,
        findings: [],
      }))
    },
  },
  watch: {
    analysisPayload: {
      immediate: true,
      handler(payload) {
        if (payload) {
          this.stopPolling()
          this.applyImportedAnalysis(payload)
        }
      },
    },
    sessionId: {
      immediate: true,
      handler() {
        if (this.isImportedMode) return
        this.loadStarted = false
        this.manifest = null
        this.reasoningGraph = null
        this.augmentedReasoningGraph = null
        this.graphPatches = []
        this.validationWarnings = []
        this.displayTrees = []
        this.selectedNode = null
        this.lastManifestSignature = ''
        if (this.active) this.loadAnalysis({ force: true })
      },
    },
    active: {
      immediate: true,
      handler(isActive) {
        if (this.isImportedMode) return
        if (isActive) {
          this.startPolling()
          this.loadAnalysis({ force: true, silent: this.loadStarted })
        } else {
          this.stopPolling()
        }
      },
    },
  },
  mounted() {
    window.addEventListener(ARTIFACT_UPDATE_EVENT, this.handleArtifactUpdate)
    window.addEventListener('keydown', this.handleKeydown)
    if (this.active && !this.isImportedMode) this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
    window.removeEventListener(ARTIFACT_UPDATE_EVENT, this.handleArtifactUpdate)
    window.removeEventListener('keydown', this.handleKeydown)
  },
  methods: {
    manifestUrl() {
      return `${this.sessionApiBase}/${this.sessionId}/analysis-artifacts`
    },
    encodeRelativePath(path) {
      return String(path)
        .split('/')
        .filter(Boolean)
        .map((part) => encodeURIComponent(part))
        .join('/')
    },
    artifactUrl(name) {
      return `${this.sessionApiBase}/${this.sessionId}/artifacts/${this.encodeRelativePath(name)}`
    },
    cacheBustedUrl(url, token) {
      if (!token) return url
      const separator = String(url).includes('?') ? '&' : '?'
      return `${url}${separator}v=${encodeURIComponent(token)}`
    },
    imageUrl(name) {
      return `${this.sessionApiBase}/${this.sessionId}/images/${this.encodeRelativePath(name)}`
    },
    async fetchManifest() {
      const response = await fetch(this.manifestUrl(), { cache: 'no-store' })
      if (response.status === 404 || response.status === 400) return null
      if (!response.ok) throw new Error(`Failed to load analysis artifact manifest: HTTP ${response.status}`)
      return response.json()
    },
    artifactInfoUrl(info) {
      if (!info) return ''
      const url = info.url || this.artifactUrl(info.name)
      return this.cacheBustedUrl(url, info.modifiedAt || info.mtime || info.size)
    },
    async fetchArtifact(info) {
      if (!info) return null
      const response = await fetch(this.artifactInfoUrl(info), { cache: 'no-store' })
      if (response.status === 404 || response.status === 400) return null
      if (!response.ok) throw new Error(`Failed to load ${info.name}: HTTP ${response.status}`)
      return response.json()
    },
    manifestSignature(manifest) {
      const current = manifest?.current || {}
      const patches = Array.isArray(current.patches)
        ? current.patches
        : Array.isArray(manifest?.patches)
          ? manifest.patches
          : []
      return [
        current.reasoningGraph?.name || manifest?.reasoningGraph?.name || '',
        current.reasoningGraph?.modifiedAt || manifest?.reasoningGraph?.modifiedAt || '',
        ...patches.flatMap((patch) => [patch.name || '', patch.modifiedAt || '']),
        manifest?.latestModifiedAt || '',
      ].join('|')
    },
    async refreshAnalysis() {
      if (this.isImportedMode) {
        this.applyImportedAnalysis(this.analysisPayload)
        return
      }
      await this.loadAnalysis({ force: true })
    },
    cloneJson(value) {
      if (value == null) return value
      try {
        return JSON.parse(JSON.stringify(value))
      } catch (error) {
        return value
      }
    },
    applyImportedAnalysis(payload) {
      const snapshot = this.cloneJson(payload) || {}
      const displayForest = Array.isArray(snapshot.displayForest)
        ? snapshot.displayForest
          .map((tree) => this.prepareNodeForDisplay(this.attachEvidenceImages(tree)))
          .filter(Boolean)
        : []
      const patchLayers = Array.isArray(snapshot.graphPatches)
        ? snapshot.graphPatches
          .map((layer) => {
            if (!layer) return null
            const name = layer.name || 'reasoning-graph-patch.json'
            const patch = layer.patch || layer
            if (!patch || typeof patch !== 'object') return null
            return { name, patch }
          })
          .filter(Boolean)
        : []
      const currentArtifacts = snapshot.currentArtifacts || {}
      this.loading = false
      this.error = displayForest.length || snapshot.reasoningGraph || snapshot.augmentedReasoningGraph
        ? ''
        : 'Imported analysis JSON does not contain a displayable reasoning forest.'
      this.manifest = {
        current: currentArtifacts,
        reasoningGraph: currentArtifacts.reasoningGraph || null,
        patches: Array.isArray(currentArtifacts.patches) ? currentArtifacts.patches : [],
      }
      this.reasoningGraph = snapshot.reasoningGraph || null
      this.augmentedReasoningGraph = snapshot.augmentedReasoningGraph || snapshot.reasoningGraph || null
      this.graphPatches = patchLayers
      this.validationWarnings = []
      this.displayTrees = displayForest
      this.selectedNode = null
      this.lastManifestSignature = ''
      this.loadStarted = true
    },
    exportAnalysis() {
      if (!this.canExportAnalysis) return
      const payload = {
        exportVersion: 1,
        exportFormat: 'maniscope-llm-analysis-json',
        exportedAt: new Date().toISOString(),
        sessionId: this.sessionId || this.analysisPayload?.sessionId || null,
        artifactSummary: this.artifactSummary || null,
        currentArtifacts: this.currentAnalysisArtifacts(),
        reasoningGraph: this.reasoningGraph,
        graphPatches: this.graphPatches.map((layer) => ({
          name: layer.name,
          patch: layer.patch,
        })),
        augmentedReasoningGraph: this.augmentedReasoningGraph,
        displayForest: this.displayTrees,
      }
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = this.buildAnalysisExportFileName()
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    },
    currentAnalysisArtifacts() {
      if (this.analysisPayload?.currentArtifacts) {
        return this.cloneJson(this.analysisPayload.currentArtifacts)
      }
      const current = this.manifest?.current || {}
      const graphInfo = current.reasoningGraph || this.manifest?.reasoningGraph || null
      const patchInfos = Array.isArray(current.patches)
        ? current.patches
        : Array.isArray(this.manifest?.patches)
          ? this.manifest.patches
          : []
      return {
        reasoningGraph: graphInfo,
        patches: patchInfos,
      }
    },
    buildAnalysisExportFileName() {
      const date = new Date()
      const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
      ].join('') + '-'
        + [
          String(date.getHours()).padStart(2, '0'),
          String(date.getMinutes()).padStart(2, '0'),
          String(date.getSeconds()).padStart(2, '0'),
        ].join('')
      const sessionPart = String(this.sessionId || this.analysisPayload?.sessionId || 'session')
        .replace(/[^a-z0-9_-]+/gi, '-')
        .replace(/^-+|-+$/g, '')
      return `maniscope-llm-analysis-${sessionPart || 'session'}-${stamp}.json`
    },
    async loadAnalysis(options = {}) {
      if (this.isImportedMode) return
      if (!this.sessionId) {
        this.error = 'No active ManiScope session.'
        return
      }
      const { force = false, silent = false } = options
      if (this.loading && silent) return
      if (!silent) {
        this.loading = true
        this.error = ''
      }
      this.loadStarted = true
      let previousSignature = this.lastManifestSignature
      try {
        const manifest = await this.fetchManifest()
        const signature = this.manifestSignature(manifest)
        if (!force && signature && signature === this.lastManifestSignature && this.reasoningGraph) return
        previousSignature = this.lastManifestSignature
        this.manifest = manifest
        this.lastManifestSignature = signature
        const current = manifest?.current || {}
        const graphInfo = current.reasoningGraph || manifest?.reasoningGraph
        const patchInfos = Array.isArray(current.patches)
          ? current.patches
          : Array.isArray(manifest?.patches)
            ? manifest.patches
            : []
        const [reasoningGraph, ...patches] = await Promise.all([
          this.fetchArtifact(graphInfo),
          ...patchInfos.map((patchInfo) => this.fetchArtifact(patchInfo)),
        ])
        if (!reasoningGraph) {
          this.reasoningGraph = null
          this.augmentedReasoningGraph = null
          this.graphPatches = []
          this.validationWarnings = []
          this.displayTrees = []
          return
        }
        const baseValidation = validateReasoningGraph(reasoningGraph, {
          answeredQuestions: 'warn',
          fileName: graphInfo?.path || graphInfo?.name || 'reasoning-graph.json',
        })
        const patchLayers = orderPatchLayers(
          patches
            .map((patch, index) => (patch ? {
              name: patchInfos[index]?.name || `reasoning-graph-patch-${index + 1}.json`,
              patch,
            } : null))
            .filter(Boolean),
        )
        const augmentedGraph = applyReasoningPatches(reasoningGraph, patchLayers)
        const augmentedValidation = validateReasoningGraph(augmentedGraph, {
          answeredQuestions: 'warn',
          fileName: 'augmented reasoning graph',
        })
        this.reasoningGraph = reasoningGraph
        this.augmentedReasoningGraph = augmentedGraph
        this.graphPatches = patchLayers
        this.validationWarnings = Array.from(new Set([
          ...baseValidation.warnings,
          ...augmentedValidation.warnings,
        ]))
        this.displayTrees = projectGraphToDisplayForest(augmentedGraph)
          .map((tree) => this.prepareNodeForDisplay(this.attachEvidenceImages(tree)))
          .filter(Boolean)
      } catch (error) {
        console.error('Failed to load LLM analysis artifacts:', error)
        if (this.hasAnalysis) {
          this.lastManifestSignature = previousSignature || this.lastManifestSignature
        } else {
          this.displayTrees = []
          this.validationWarnings = []
        }
        this.error = ''
      } finally {
        if (!silent) this.loading = false
      }
    },
    startPolling() {
      this.stopPolling()
      if (this.isImportedMode) return
      if (!this.sessionId) return
      this.pollTimer = window.setInterval(() => {
        this.loadAnalysis({ silent: true })
      }, POLL_INTERVAL_MS)
    },
    stopPolling() {
      if (!this.pollTimer) return
      window.clearInterval(this.pollTimer)
      this.pollTimer = null
    },
    handleArtifactUpdate(event) {
      if (this.isImportedMode) return
      const detail = event?.detail || {}
      if (detail.sessionId && detail.sessionId !== this.sessionId) return
      if (detail.sessionMode && detail.sessionMode !== this.sessionMode) return
      const name = detail.artifact?.title || detail.artifact?.name || ''
      if (!this.isAnalysisArtifactName(name)) return
      if (this.active) this.loadAnalysis({ force: true, silent: true })
    },
    handleKeydown(event) {
      if (event?.key === 'Escape' && this.selectedNode) this.closeSelectedNode()
    },
    closeSelectedNode() {
      this.selectedNode = null
    },
    isAnalysisArtifactName(name) {
      return name === 'reasoning-graph.json'
        || name === 'user-reasoning-forest.json'
        || name === 'reasoning-graph-patch.json'
        || /^reasoning-graph-patch(?:-.+)?\.json$/.test(name)
    },
    attachEvidenceImages(node) {
      if (!node) return null
      return {
        ...node,
        evidenceImages: this.nodeEvidenceImages(node),
        children: Array.isArray(node.children)
          ? node.children.map((child) => this.attachEvidenceImages(child)).filter(Boolean)
          : [],
      }
    },
    prepareNodeForDisplay(node) {
      if (!node) return null
      const rawChildren = Array.isArray(node.children) ? node.children : []
      const siblingSeenImages = new Set()
      const children = rawChildren
        .map((child) => this.prepareNodeForDisplay(child))
        .filter(Boolean)
        .map((child) => this.withSiblingDisplayImages(child, siblingSeenImages))
      return this.withSiblingDisplayImages({
        ...node,
        children,
      })
    },
    withSiblingDisplayImages(node, siblingSeenImages = null) {
      const ownImages = Array.isArray(node?.evidenceImages) ? node.evidenceImages : []
      if (!this.shouldRenderNodeImages(node)) {
        return {
          ...node,
          displayEvidenceImages: [],
        }
      }
      if (!siblingSeenImages) {
        return {
          ...node,
          displayEvidenceImages: ownImages,
        }
      }
      return {
        ...node,
        displayEvidenceImages: ownImages.filter((image) => {
          if (!image?.url || siblingSeenImages.has(image.url)) return false
          siblingSeenImages.add(image.url)
          return true
        }),
      }
    },
    nodeType(node) {
      return node.type || node.kind || node.nodeType || 'Node'
    },
    isSynthesisFindingNode(node) {
      if (this.nodeType(node) !== 'Finding') return false
      const children = Array.isArray(node?.children) ? node.children : []
      return children.some((child) => this.nodeType(child) === 'Finding')
    },
    isConcreteFindingNode(node) {
      return this.nodeType(node) === 'Finding' && !this.isSynthesisFindingNode(node)
    },
    shouldRenderNodeImages(node) {
      return this.isConcreteFindingNode(node)
    },
    shouldShowInternalFindings(node) {
      if (!node) return false
      return this.nodeType(node) === 'Hypothesis' || this.isSynthesisFindingNode(node)
    },
    collectConcreteDescendantFindings(node) {
      const results = []
      const seen = new Set()
      const visit = (current) => {
        const children = Array.isArray(current?.children) ? current.children : []
        for (const child of children) {
          if (this.isConcreteFindingNode(child)) {
            const key = child.instanceId || child.canonicalId || child.id
            if (key && !seen.has(key)) {
              seen.add(key)
              results.push({
                key,
                label: child.label,
                relationLabel: this.relationLabel(child.displayRelation || child.relation),
                sourceClass: child.source === 'patch' ? 'detail-finding-agent' : 'detail-finding-user',
                relationClass: this.normalizedRelation(child.displayRelation || child.relation)
                  ? `relation-${this.normalizedRelation(child.displayRelation || child.relation)}`
                  : '',
                explanation: this.preferredExplanation(child),
                evidenceSummary: this.supportingExplanation(child),
                reasoningRole: this.reasoningNarrative(child),
                images: Array.isArray(child.evidenceImages) ? child.evidenceImages : [],
              })
            }
            continue
          }
          visit(child)
        }
      }
      visit(node)
      return results
    },
    groupFindingImages(findings) {
      const grouped = new Map()
      for (const finding of findings) {
        const images = Array.isArray(finding.images) ? finding.images : []
        for (const image of images) {
          if (!image?.url) continue
          if (!grouped.has(image.url)) {
            grouped.set(image.url, {
              image,
              findings: [],
            })
          }
          const group = grouped.get(image.url)
          if (!group.findings.some((item) => item.key === finding.key)) {
            group.findings.push({
              key: finding.key,
              label: finding.label,
            })
          }
        }
      }
      return Array.from(grouped.values())
    },
    nodeLabel(node) {
      const label = node.label || node.title || node.explanation || node.evidenceSummary || node.id || 'Untitled node'
      return this.cleanNarrativeText(this.humanReadableValue(label), { preserveShort: true })
    },
    preferredExplanation(node) {
      return this.firstReadableNarrative(
        node?.displayExplanation,
        node?.explanation,
        node?.label,
        node?.title,
        node?.evidenceSummary,
      )
    },
    supportingExplanation(node) {
      return this.firstReadableNarrative(
        node?.displayEvidenceSummary,
        node?.evidenceSummary,
        node?.evidence,
        node?.provenance,
      )
    },
    reasoningNarrative(node) {
      return this.firstReadableNarrative(
        node?.displayReasoningRole,
        node?.reasoningRole,
        node?.patchRationale,
      )
    },
    firstReadableNarrative(...values) {
      for (const value of values) {
        const text = this.cleanNarrativeText(this.humanReadableValue(value))
        if (text) return text
      }
      return ''
    },
    cleanNarrativeText(value, options = {}) {
      if (!value) return ''
      const { preserveShort = false } = options
      const compact = String(value).replace(/\s+/g, ' ').trim()
      if (!compact) return ''
      const sentences = compact
        .split(/(?<=[.?!])\s+/)
        .map((item) => item.trim())
        .filter(Boolean)

      const cleaned = sentences.filter((sentence) => !this.isMetaProcessSentence(sentence))
      let text = cleaned.join(' ').trim() || compact
      text = text
        .replace(/^(This (finding|hypothesis|analysis)\s+(suggests|indicates|shows|means)\s+that\s+)/i, '')
        .replace(/^(Based on (the )?(LLM|agent|assistant|model)[^,]*,\s*)/i, '')
        .replace(/^(The (LLM|agent|assistant|model)\s+(analysis|reasoning|output)\s+(suggests|indicates|shows)\s+that\s+)/i, '')
        .replace(/^(The (LLM|agent|assistant|model)\s+(analyzes?|analyzed|checked|examined|observed|identified|reasoned|concluded)\s+that\s+)/i, '')
        .replace(/^(The (LLM|agent|assistant|model)\s+(analyzes?|analyzed|checked|examined|observed|identified|reasoned|concluded)\b[^.?!]*[.?!]\s*)/i, '')
        .trim()

      if (!preserveShort) {
        text = text.replace(/^(There (is|are)\s+)/i, '')
      }
      return text
    },
    isMetaProcessSentence(sentence) {
      return /^(As an? (LLM|assistant)|The (LLM|agent|assistant|model)\s+(analyzes?|analyzed|checked|examined|looked|reviewed|observed|identified|reasoned|concluded|generated)|This analysis\b|The analysis\b|We (analyze|observed|check|checked)\b|I (analyze|checked|observed)\b)/i.test(sentence)
    },
    humanReadableValue(value) {
      if (!value) return ''
      if (typeof value === 'string') return value.trim()
      if (Array.isArray(value)) {
        return value
          .map((item) => this.humanReadableValue(item))
          .filter(Boolean)
          .join('; ')
      }
      if (typeof value === 'object') {
        const preferredKeys = [
          'explanation',
          'summary',
          'text',
          'label',
          'title',
          'evidenceSummary',
          'reason',
          'rationale',
        ]
        for (const key of preferredKeys) {
          const text = this.humanReadableValue(value[key])
          if (text) return text
        }
        return Object.entries(value)
          .filter(([key, item]) =>
            ['string', 'number', 'boolean'].includes(typeof item)
            && !['actor', 'source', 'kind', 'type', 'space', 'scope', 'confidence'].includes(key),
          )
          .map(([key, item]) => `${key}: ${item}`)
          .join('; ')
      }
      return String(value)
    },
    formatValue(value) {
      if (Array.isArray(value)) return value.join(', ')
      if (value && typeof value === 'object') return JSON.stringify(value)
      return value
    },
    nodeEvidenceImages(node) {
      const refs = []
      this.collectEvidenceImageRefs(node.provenance, refs)
      this.collectEvidenceImageRefs(node.evidenceImages, refs)
      this.collectEvidenceImageRefs(node.images, refs)
      this.collectEvidenceImageRefs(node.evidence, refs)

      const images = []
      const seen = new Set()
      for (const ref of refs) {
        const image = this.resolveEvidenceImageRef(ref)
        if (!image || seen.has(image.url)) continue
        seen.add(image.url)
        images.push(image)
      }
      return images
    },
    collectEvidenceImageRefs(value, refs) {
      if (!value) return
      if (Array.isArray(value)) {
        for (const item of value) this.collectEvidenceImageRefs(item, refs)
        return
      }
      if (typeof value === 'object') {
        this.collectEvidenceImageRefs(value.url || value.path || value.src || value.href, refs)
        return
      }
      if (typeof value !== 'string') return
      for (const part of value.split('|')) {
        const text = part.trim()
        if (this.evidenceImagePathFromText(text)) refs.push(text)
      }
    },
    evidenceImagePathFromText(text) {
      if (!text) return ''
      const prefixed = text.match(/^(?:screenshot|render|image):(.+\.(?:png|jpe?g|webp))$/i)
      if (prefixed) return prefixed[1].trim()
      const bare = text.match(/^(.+\.(?:png|jpe?g|webp))$/i)
      return bare ? bare[1].trim() : ''
    },
    resolveEvidenceImageRef(ref) {
      let path = this.evidenceImagePathFromText(ref).replace(/\\/g, '/')
      if (!path) return null
      if (/^(https?:|data:|blob:)/i.test(path)) {
        return { url: path, label: this.basename(path) }
      }
      if (path.startsWith('/api/sessions/') || path.startsWith('/api/base/sessions/')) {
        return { url: path, label: this.basename(path) }
      }
      if (/^(file:|[a-z]+:)/i.test(path)) return null
      while (path.startsWith('./')) path = path.slice(2)

      if (path.startsWith('../images/')) {
        const imagePath = path.slice('../images/'.length)
        return { url: this.imageUrl(imagePath), label: this.basename(imagePath) }
      }
      if (path.startsWith('images/')) {
        const imagePath = path.slice('images/'.length)
        return { url: this.imageUrl(imagePath), label: this.basename(imagePath) }
      }
      if (path.startsWith('../artifacts/')) {
        const artifactPath = path.slice('../artifacts/'.length)
        return { url: this.artifactUrl(artifactPath), label: this.basename(artifactPath) }
      }
      if (path.startsWith('artifacts/')) {
        const artifactPath = path.slice('artifacts/'.length)
        return { url: this.artifactUrl(artifactPath), label: this.basename(artifactPath) }
      }
      if (path.includes('..')) return null
      return { url: this.artifactUrl(path), label: this.basename(path) }
    },
    basename(path) {
      const cleanPath = String(path).split(/[?#]/)[0]
      return cleanPath.split('/').filter(Boolean).pop() || 'evidence image'
    },
    normalizedRelation(relation) {
      const normalized = String(relation || '').trim().toLowerCase().replace(/[\s-]+/g, '_')
      const aliases = {
        answer: 'answers',
        contradict: 'contradicts',
        counterevidence: 'contradicts',
        refine: 'refines',
        support: 'supports',
        synthesize: 'synthesizes',
      }
      return aliases[normalized] || normalized
    },
    relationLabel(relation) {
      const normalized = this.normalizedRelation(relation)
      const labels = {
        answers: 'Answers',
        contains: 'Contains',
        contradicts: 'Contradicts',
        derived_from: 'Derived from',
        motivates: 'Motivates',
        produces: 'Produces',
        refines: 'Refines',
        supports: 'Supports',
        synthesizes: 'Synthesizes',
      }
      if (labels[normalized]) return labels[normalized]
      const text = String(relation || '').trim()
      if (!text) return ''
      return text
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    },
  },
}
</script>

<style scoped>
.llm-analysis-view {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #1f2937;
}

.analysis-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.toolbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.imported-mode-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #ddd6fe;
  background: #f5f3ff;
  color: #6d28d9;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  padding: 2px 8px;
}

.analysis-title {
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.analysis-subtitle {
  color: #718096;
  font-size: 11px;
  line-height: 1.3;
  margin-top: 2px;
}

.artifact-summary {
  color: #64748b;
  font-size: 10px;
  margin: -2px 0 8px;
}

.validation-warnings {
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 10px;
  line-height: 1.4;
  margin: 0 0 8px;
  padding: 8px 10px;
}

.validation-warning-title {
  font-weight: 800;
  margin-bottom: 4px;
}

.validation-warnings ul {
  margin: 0;
  padding-left: 16px;
}

.refresh-btn,
.export-btn,
.detail-close {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
}

.refresh-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

.export-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

.legend-block {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.legend-row-single {
  align-items: center;
}

.legend-item {
  border-radius: 999px;
  border: 1px solid #d8e0ec;
  font-size: 10px;
  font-weight: 800;
  line-height: 16px;
  padding: 2px 7px;
}

.legend-hypothesis {
  background: #d9e3ff;
  color: #334155;
}

.legend-derived-hypothesis {
  background: #fff0f7;
  border-color: #f3b4d0;
  color: #be185d;
}

.legend-user {
  background: #edf4ff;
  border-color: #b8cdf8;
  color: #1d4ed8;
}

.legend-patch {
  background: #fff0f7;
  border-color: #f3b4d0;
  color: #be185d;
}

.relation-legend {
  background: #ffffff;
}

.relation-supports {
  background: #ecfdf3;
  border-color: #86efac;
  color: #166534;
}

.relation-answers {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.relation-refines {
  background: #fffbeb;
  border-color: #fbbf24;
  color: #92400e;
}

.relation-contradicts {
  background: #fff1f2;
  border-color: #fb7185;
  color: #be123c;
}

.forest-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 2px;
  min-height: 0;
}

.hypothesis-tree {
  width: 100%;
}

.empty-state {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.45;
  text-align: center;
  margin-top: 20px;
  padding: 0 12px;
}

.error-state {
  color: #b91c1c;
}

.detail-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.54);
  backdrop-filter: blur(3px);
}

.detail-modal {
  width: min(1120px, calc(100vw - 48px));
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 18px;
  background: #ffffff;
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.24),
    0 10px 26px rgba(15, 23, 42, 0.14);
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.detail-header-copy {
  min-width: 0;
}

.detail-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.detail-type,
.detail-relation {
  display: inline-flex;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  line-height: 18px;
  padding: 2px 9px;
}

.detail-type {
  background: #d9e3ff;
  color: #334155;
  border: 1px solid #aabce8;
}

.detail-type-user-finding {
  color: #1d4ed8;
  background: #edf4ff;
  border: 1px solid #b8cdf8;
}

.detail-type-derived-hypothesis {
  color: #be185d;
  background: #fff0f7;
  border: 1px solid #f3b4d0;
}

.detail-type-agent-finding {
  color: #be185d;
  background: #fff0f7;
  border: 1px solid #f3b4d0;
}

.detail-relation {
  border: 1px solid #d8e0ec;
}

.detail-title {
  color: #111827;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.35;
  margin-top: 12px;
  overflow-wrap: anywhere;
}

.detail-body {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(340px, 1.1fr);
  gap: 0;
  min-height: 0;
  overflow: hidden;
}

.detail-body-single {
  grid-template-columns: minmax(0, 1fr);
}

.detail-text-panel,
.detail-images-panel {
  min-height: 0;
  overflow-y: auto;
}

.detail-text-panel {
  padding: 24px;
}

.detail-images-panel {
  padding: 24px;
  border-left: 1px solid #e2e8f0;
  background: #f8fafc;
}

.detail-list {
  display: grid;
  gap: 12px;
  margin: 0;
}

.detail-list dt {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.detail-list dd {
  color: #334155;
  font-size: 15px;
  line-height: 1.72;
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-findings-section {
  margin-top: 24px;
}

.detail-section-title {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 12px;
}

.detail-findings-list {
  display: grid;
  gap: 12px;
}

.detail-finding-card {
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.detail-finding-card.detail-finding-user {
  background: #edf4ff;
  border-color: #b8cdf8;
}

.detail-finding-card.detail-finding-agent {
  background: #fff0f7;
  border-color: #f3b4d0;
}

.detail-finding-card.relation-answers {
  border-color: #93c5fd;
}

.detail-finding-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-finding-relation {
  align-self: flex-start;
  border: 1px solid #d8e0ec;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  line-height: 16px;
  padding: 1px 7px;
}

.detail-finding-title {
  color: #111827;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.45;
}

.detail-finding-copy {
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
  margin: 8px 0 0;
  overflow-wrap: anywhere;
}

.detail-images-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 14px;
}

.detail-images-title {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.detail-image-link {
  display: block;
  color: #2563eb;
  text-decoration: none;
}

.detail-image {
  display: block;
  width: 100%;
  max-height: 72vh;
  object-fit: contain;
  border: 1px solid #d8e0ec;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.detail-image-label {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.detail-image-finding-list {
  display: block;
  margin-top: 6px;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

@media (max-width: 960px) {
  .detail-modal-overlay {
    padding: 12px;
  }

  .detail-modal {
    width: min(100vw - 24px, 920px);
    max-height: calc(100vh - 24px);
  }

  .detail-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-images-panel {
    border-left: none;
    border-top: 1px solid #e2e8f0;
  }
}
</style>

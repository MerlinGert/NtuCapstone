<template>
  <div class="llm-analysis-view">
    <div class="analysis-toolbar">
      <div>
        <div class="analysis-title">Reasoning Forest</div>
        <div class="analysis-subtitle">
          Showing only each hypothesis and its supporting hierarchical findings.
        </div>
      </div>
      <button class="refresh-btn" :disabled="loading || !sessionId" @click="refreshAnalysis">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>
    <div v-if="artifactSummary" class="artifact-summary">{{ artifactSummary }}</div>

    <div class="legend-row">
      <span class="legend-item legend-hypothesis">Hypothesis</span>
      <span class="legend-item legend-finding">Finding</span>
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
              <span class="detail-type">{{ selectedNode.type }}</span>
              <div class="detail-title">{{ selectedNode.label }}</div>
            </div>
            <button class="detail-close" @click="closeSelectedNode">Close</button>
          </div>
          <div class="detail-body" :class="{ 'detail-body-single': !selectedNodeEvidenceImages.length }">
            <div class="detail-text-panel">
              <dl class="detail-list">
                <template v-for="item in selectedNodeDetails" :key="item.key">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </template>
              </dl>
            </div>
            <div v-if="selectedNodeEvidenceImages.length" class="detail-images-panel">
              <div class="detail-images-title">Evidence Images</div>
              <div class="detail-images-grid">
                <a
                  v-for="image in selectedNodeEvidenceImages"
                  :key="image.url"
                  class="detail-image-link"
                  :href="image.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  <img :src="image.url" :alt="image.label" class="detail-image" />
                  <span class="detail-image-label">{{ image.label }}</span>
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
    active: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      loading: false,
      error: '',
      manifest: null,
      userForest: null,
      graphPatch: null,
      selectedNode: null,
      loadStarted: false,
      lastManifestSignature: '',
      pollTimer: null,
    }
  },
  computed: {
    hasAnalysis() {
      return this.forestTrees.length > 0
    },
    forestTrees() {
      if (!this.userForest) return []
      const patchGraph = this.normalizedPatchGraph()
      const patchChildrenByTarget = this.buildPatchChildrenByTarget(patchGraph.nodes, patchGraph.edges)
      const existingRootIds = new Set()
      let userTrees = []
      if (Array.isArray(this.userForest.trees)) {
        userTrees = this.userForest.trees
          .map((tree, index) => this.buildGeneratedForestTree(tree, {
            patchChildrenByTarget,
            patchNodes: patchGraph.nodes,
            path: `tree-${index}`,
          }))
          .filter(Boolean)
        for (const tree of this.userForest.trees) {
          if (tree?.root) existingRootIds.add(tree.root)
        }
        return [
          ...userTrees,
          ...this.buildPatchRootTrees(patchGraph, patchChildrenByTarget, existingRootIds),
        ]
          .map((tree) => this.extractHypothesisTree(tree))
          .filter(Boolean)
      }
      if (!Array.isArray(this.userForest.roots)) return []
      const userNodes = this.userForest.nodes && typeof this.userForest.nodes === 'object'
        ? this.userForest.nodes
        : {}
      userTrees = this.userForest.roots.map((root, index) =>
        this.buildDisplayNode(root, {
          userNodes,
          patchChildrenByTarget,
          patchNodes: patchGraph.nodes,
          path: `root-${index}`,
          visited: new Set(),
        }),
      )
      for (const root of this.userForest.roots) {
        const id = typeof root === 'string' ? root : root?.id
        if (id) existingRootIds.add(id)
      }
      return [
        ...userTrees,
        ...this.buildPatchRootTrees(patchGraph, patchChildrenByTarget, existingRootIds),
      ]
        .map((tree) => this.extractHypothesisTree(tree))
        .filter(Boolean)
    },
    artifactSummary() {
      const current = this.manifest?.current || {}
      const names = [
        current.userReasoningForest?.name,
        current.reasoningGraphPatch?.name,
      ].filter(Boolean)
      if (!names.length) return ''
      return `Showing ${names.join(' + ')}`
    },
    selectedNodeDetails() {
      if (!this.selectedNode) return []
      const explanation = this.preferredExplanation(this.selectedNode)
      const support = this.supportingExplanation(this.selectedNode)
      const reasoning = this.reasoningNarrative(this.selectedNode)
      return [
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
    selectedNodeEvidenceImages() {
      return Array.isArray(this.selectedNode?.evidenceImages)
        ? this.selectedNode.evidenceImages
        : []
    },
  },
  watch: {
    sessionId: {
      immediate: true,
      handler() {
        this.loadStarted = false
        this.manifest = null
        this.userForest = null
        this.graphPatch = null
        this.selectedNode = null
        this.lastManifestSignature = ''
        if (this.active) this.loadAnalysis({ force: true })
      },
    },
    active: {
      immediate: true,
      handler(isActive) {
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
    if (this.active) this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
    window.removeEventListener(ARTIFACT_UPDATE_EVENT, this.handleArtifactUpdate)
    window.removeEventListener('keydown', this.handleKeydown)
  },
  methods: {
    manifestUrl() {
      return `/api/sessions/${this.sessionId}/analysis-artifacts`
    },
    encodeRelativePath(path) {
      return String(path)
        .split('/')
        .filter(Boolean)
        .map((part) => encodeURIComponent(part))
        .join('/')
    },
    artifactUrl(name) {
      return `/api/sessions/${this.sessionId}/artifacts/${this.encodeRelativePath(name)}`
    },
    imageUrl(name) {
      return `/api/sessions/${this.sessionId}/images/${this.encodeRelativePath(name)}`
    },
    async fetchManifest() {
      const response = await fetch(this.manifestUrl())
      if (response.status === 404 || response.status === 400) return null
      if (!response.ok) throw new Error(`Failed to load analysis artifact manifest: HTTP ${response.status}`)
      return response.json()
    },
    artifactInfoUrl(info) {
      if (!info) return ''
      return info.url || this.artifactUrl(info.name)
    },
    async fetchArtifact(info) {
      if (!info) return null
      const response = await fetch(this.artifactInfoUrl(info))
      if (response.status === 404 || response.status === 400) return null
      if (!response.ok) throw new Error(`Failed to load ${info.name}: HTTP ${response.status}`)
      return response.json()
    },
    manifestSignature(manifest) {
      const current = manifest?.current || {}
      return [
        current.userReasoningForest?.name || '',
        current.userReasoningForest?.modifiedAt || '',
        current.reasoningGraphPatch?.name || '',
        current.reasoningGraphPatch?.modifiedAt || '',
        manifest?.latestModifiedAt || '',
      ].join('|')
    },
    async refreshAnalysis() {
      await this.loadAnalysis({ force: true })
    },
    async loadAnalysis(options = {}) {
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
      try {
        const manifest = await this.fetchManifest()
        const signature = this.manifestSignature(manifest)
        if (!force && signature && signature === this.lastManifestSignature && this.userForest) return
        this.manifest = manifest
        this.lastManifestSignature = signature
        const current = manifest?.current || {}
        const [userForest, graphPatch] = await Promise.all([
          this.fetchArtifact(current.userReasoningForest),
          this.fetchArtifact(current.reasoningGraphPatch),
        ])
        this.userForest = userForest
        this.graphPatch = graphPatch
      } catch (error) {
        if (!silent) this.error = error && error.message ? error.message : String(error)
      } finally {
        if (!silent) this.loading = false
      }
    },
    startPolling() {
      this.stopPolling()
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
      const detail = event?.detail || {}
      if (detail.sessionId && detail.sessionId !== this.sessionId) return
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
      return name === 'user-reasoning-forest.json'
        || name === 'reasoning-graph-patch.json'
        || /^reasoning-graph-patch-[^.]+\.json$/.test(name)
    },
    normalizedPatchGraph() {
      if (Array.isArray(this.graphPatch?.nodes) || Array.isArray(this.graphPatch?.edges)) {
        return {
          nodes: new Map(
            Array.isArray(this.graphPatch.nodes)
              ? this.graphPatch.nodes.map((node) => [node.id, node])
              : [],
          ),
          edges: Array.isArray(this.graphPatch.edges) ? this.graphPatch.edges : [],
          roots: Array.isArray(this.graphPatch.roots) ? this.graphPatch.roots : [],
        }
      }
      const nodes = new Map()
      const edges = []
      const roots = []
      const operations = Array.isArray(this.graphPatch?.operations) ? this.graphPatch.operations : []
      for (const operation of operations) {
        if (operation?.op === 'add_node' && operation.node?.id) {
          nodes.set(operation.node.id, operation.node)
        } else if (operation?.op === 'update_node' && operation.node?.id) {
          nodes.set(operation.node.id, {
            ...(nodes.get(operation.node.id) || {}),
            ...operation.node,
          })
        } else if (operation?.op === 'add_edge' && operation.edge) {
          edges.push(operation.edge)
        } else if (operation?.op === 'add_root' && operation.id) {
          roots.push(operation.id)
        }
      }
      return { nodes, edges, roots }
    },
    buildPatchRootTrees(patchGraph, patchChildrenByTarget, existingRootIds) {
      return patchGraph.roots
        .filter((rootId) => patchGraph.nodes.has(rootId) && !existingRootIds.has(rootId))
        .map((rootId, index) => {
          const rootNode = this.normalizeDisplayNode(patchGraph.nodes.get(rootId), {
            source: 'patch',
            relation: '',
            instanceId: `patch-root-${index}-${rootId}`,
          })
          this.appendPatchChildren(rootNode, {
            patchChildrenByTarget,
            patchNodes: patchGraph.nodes,
            path: `patch-root-${index}`,
            visited: new Set([rootNode.id]),
          })
          return rootNode
        })
    },
    extractHypothesisTree(tree) {
      if (!tree || this.nodeType(tree) !== 'Hypothesis') return null
      return {
        ...tree,
        children: this.collectHierarchicalFindings(tree),
      }
    },
    collectHierarchicalFindings(node) {
      const children = Array.isArray(node?.children) ? node.children : []
      const results = []
      for (const child of children) {
        const type = this.nodeType(child)
        if (type === 'Finding') {
          results.push(this.pruneFindingNode(child))
          continue
        }
        results.push(...this.collectHierarchicalFindings(child))
      }
      return this.dedupeNodes(results)
    },
    pruneFindingNode(node) {
      const children = Array.isArray(node?.children) ? node.children : []
      const findingChildren = []
      for (const child of children) {
        const type = this.nodeType(child)
        if (type === 'Finding') {
          findingChildren.push(this.pruneFindingNode(child))
          continue
        }
        findingChildren.push(...this.collectHierarchicalFindings(child))
      }
      return {
        ...node,
        children: this.dedupeNodes(findingChildren),
      }
    },
    dedupeNodes(nodes) {
      const seen = new Set()
      const results = []
      for (const node of nodes) {
        const key = node?.canonicalId || node?.id || node?.instanceId
        if (!key || seen.has(key)) continue
        seen.add(key)
        results.push(node)
      }
      return results
    },
    buildPatchChildrenByTarget(patchNodes, edges) {
      const grouped = new Map()
      for (const edge of edges) {
        if (!edge || !patchNodes.has(edge.source) || !edge.target) continue
        const children = grouped.get(edge.target) || []
        children.push({
          node: patchNodes.get(edge.source),
          relation: edge.relation || '',
        })
        grouped.set(edge.target, children)
      }
      const nested = new Map()
      for (const [targetId, children] of grouped.entries()) {
        const synthesisNodes = children.filter(
          (child) => child.relation === 'synthesizes' && this.nodeType(child.node) === 'Finding',
        )
        if (synthesisNodes.length === 0) {
          nested.set(targetId, children)
          continue
        }

        const containedChildren = children.filter(
          (child) => !(child.relation === 'synthesizes' && this.nodeType(child.node) === 'Finding'),
        )
        nested.set(targetId, [
          {
            ...synthesisNodes[0],
            nestedPatchChildren: containedChildren,
          },
          ...synthesisNodes.slice(1),
        ])
      }
      return nested
    },
    buildGeneratedForestTree(tree, context) {
      const nodes = Array.isArray(tree?.nodes) ? tree.nodes : []
      if (!nodes.length) return null
      const nodesByInstance = new Map()
      for (const rawNode of nodes) {
        const displayNode = this.normalizeDisplayNode(rawNode, {
          source: 'user',
          relation: rawNode.relationToParent || '',
          instanceId: rawNode.instanceId || rawNode.id || rawNode.canonicalId,
        })
        displayNode.children = []
        nodesByInstance.set(displayNode.instanceId, displayNode)
      }

      for (const rawNode of nodes) {
        if (!rawNode.parentInstanceId) continue
        const parent = nodesByInstance.get(rawNode.parentInstanceId)
        const child = nodesByInstance.get(rawNode.instanceId || rawNode.id || rawNode.canonicalId)
        if (parent && child) parent.children.push(child)
      }

      for (const displayNode of nodesByInstance.values()) {
        this.appendPatchChildren(displayNode, {
          ...context,
          visited: new Set([displayNode.id]),
        })
      }

      return nodesByInstance.get(tree.root)
        || Array.from(nodesByInstance.values()).find((node) => !node.parentInstanceId)
        || nodesByInstance.values().next().value
    },
    buildDisplayNode(rawNode, context) {
      const canonical = context.patchNodes.has(rawNode.id)
        ? {
            ...context.patchNodes.get(rawNode.id),
            ...rawNode,
          }
        : {
            ...(context.userNodes[rawNode.id] || {}),
            ...rawNode,
          }
      const isPatch = context.patchNodes.has(canonical.id)
      const displayNode = this.normalizeDisplayNode(canonical, {
        source: isPatch ? 'patch' : 'user',
        relation: rawNode.relation || '',
        instanceId: `${context.path}-${canonical.id}`,
      })

      if (context.visited.has(canonical.id)) return displayNode
      const nextVisited = new Set(context.visited)
      nextVisited.add(canonical.id)

      const userChildren = Array.isArray(canonical.children)
        ? canonical.children
        : []
      displayNode.children.push(
        ...userChildren
          .map((childId, index) => {
            const childRaw = context.userNodes[childId]
            if (!childRaw) return null
            return this.buildDisplayNode(
              { ...childRaw, id: childId },
              {
                ...context,
                path: `${context.path}-u${index}`,
                visited: nextVisited,
              },
            )
          })
          .filter(Boolean),
      )

      const patchChildren = context.patchChildrenByTarget.get(canonical.id) || []
      displayNode.children.push(
        ...patchChildren.map((patchChild, index) =>
          this.buildPatchDisplayNode(patchChild, {
            ...context,
            path: `${context.path}-p${index}`,
            visited: nextVisited,
          }),
        ),
      )

      const nestedPatchChildren = Array.isArray(canonical.nestedPatchChildren)
        ? canonical.nestedPatchChildren
        : []
      displayNode.children.push(
        ...nestedPatchChildren.map((patchChild, index) =>
          this.buildPatchDisplayNode(patchChild, {
            ...context,
            path: `${context.path}-nested${index}`,
            visited: nextVisited,
          }),
        ),
      )

      return displayNode
    },
    buildPatchDisplayNode(patchChild, context) {
      const rawNode = {
        ...patchChild.node,
        relation: patchChild.relation,
        nestedPatchChildren: patchChild.nestedPatchChildren || [],
      }
      const displayNode = this.normalizeDisplayNode(rawNode, {
        source: 'patch',
        relation: patchChild.relation || '',
        instanceId: `${context.path}-${rawNode.id}`,
      })
      if (context.visited.has(displayNode.id)) return displayNode
      const nextVisited = new Set(context.visited)
      nextVisited.add(displayNode.id)
      this.appendPatchChildren(displayNode, {
        ...context,
        visited: nextVisited,
      })
      return displayNode
    },
    appendPatchChildren(displayNode, context) {
      const targetIds = [displayNode.id, displayNode.canonicalId, displayNode.instanceId].filter(Boolean)
      const seenChildren = new Set()
      for (const targetId of targetIds) {
        const patchChildren = context.patchChildrenByTarget.get(targetId) || []
        for (const patchChild of patchChildren) {
          const childId = patchChild.node?.id
          if (!childId || seenChildren.has(childId)) continue
          seenChildren.add(childId)
          displayNode.children.push(this.buildPatchDisplayNode(patchChild, {
            ...context,
            path: `${displayNode.instanceId || displayNode.id}-patch-${displayNode.children.length}`,
          }))
        }
      }

      const nestedPatchChildren = Array.isArray(displayNode.nestedPatchChildren)
        ? displayNode.nestedPatchChildren
        : []
      for (const patchChild of nestedPatchChildren) {
        const childId = patchChild.node?.id
        if (!childId || seenChildren.has(childId)) continue
        seenChildren.add(childId)
        displayNode.children.push(this.buildPatchDisplayNode(patchChild, {
          ...context,
          path: `${displayNode.instanceId || displayNode.id}-nested-${displayNode.children.length}`,
        }))
      }
    },
    normalizeDisplayNode(node, overrides = {}) {
      const id = node.id || node.canonicalId || node.instanceId || 'unknown'
      const type = this.nodeType(node)
      const mergedNode = {
        ...node,
        ...overrides,
      }
      const label = this.nodeLabel({ ...node, type })
      const displayExplanation = this.preferredExplanation(mergedNode)
      const displayEvidenceSummary = this.supportingExplanation(mergedNode)
      const displayReasoningRole = this.reasoningNarrative(mergedNode)
      return {
        ...mergedNode,
        id,
        canonicalId: node.canonicalId || node.id || id,
        type,
        relation: overrides.relation || node.relation || node.relationToParent || '',
        label,
        displayExplanation,
        displayEvidenceSummary,
        displayReasoningRole,
        children: Array.isArray(node.children) ? [...node.children] : [],
        evidenceImages: this.nodeEvidenceImages(mergedNode),
      }
    },
    nodeType(node) {
      return node.type || node.kind || node.nodeType || 'Node'
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
      if (path.startsWith('/api/sessions/')) {
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

.refresh-btn,
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

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
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

.legend-finding {
  background: #ecfeef;
  border-color: #9ae6b4;
  color: #166534;
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

.detail-type {
  display: inline-flex;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  line-height: 18px;
  padding: 2px 9px;
}

.detail-type {
  background: #eef2ff;
  color: #4338ca;
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

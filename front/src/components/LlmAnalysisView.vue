<template>
  <div class="llm-analysis-view">
    <div class="analysis-toolbar">
      <div>
        <div class="analysis-title">Reasoning Forest</div>
        <div class="analysis-subtitle">
          User forest with agent patch nodes overlaid as supporting or qualifying evidence.
        </div>
      </div>
      <button class="refresh-btn" :disabled="loading || !sessionId" @click="refreshAnalysis">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>
    <div v-if="artifactSummary" class="artifact-summary">{{ artifactSummary }}</div>

    <div class="legend-row">
      <span class="legend-item legend-hypothesis">Hypothesis</span>
      <span class="legend-item legend-user">User reasoning node</span>
      <span class="legend-item legend-patch">Agent patch node</span>
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

    <div v-if="selectedNode" class="node-detail-panel">
      <div class="detail-header">
        <div>
          <span class="detail-type">{{ selectedNode.type }}</span>
          <span v-if="selectedNode.source === 'patch'" class="detail-patch">Patch</span>
        </div>
        <button class="detail-close" @click="selectedNode = null">Close</button>
      </div>
      <div class="detail-title">{{ selectedNode.label }}</div>
      <dl class="detail-list">
        <template v-for="item in selectedNodeDetails" :key="item.key">
          <dt>{{ item.label }}</dt>
          <dd>{{ item.value }}</dd>
        </template>
      </dl>
    </div>
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
      return [
        { key: 'id', label: 'ID', value: this.selectedNode.id },
        { key: 'relation', label: 'Relation', value: this.selectedNode.relation },
        { key: 'evidence', label: 'Evidence', value: this.formatValue(this.selectedNode.evidence) },
        { key: 'explanation', label: 'Explanation', value: this.selectedNode.explanation },
        { key: 'evidenceSummary', label: 'Evidence Summary', value: this.selectedNode.evidenceSummary },
        { key: 'reasoningRole', label: 'Reasoning Role', value: this.selectedNode.reasoningRole },
        { key: 'patchRationale', label: 'Patch Rationale', value: this.selectedNode.patchRationale },
      ].filter((item) => item.value)
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
    if (this.active) this.startPolling()
  },
  beforeUnmount() {
    this.stopPolling()
    window.removeEventListener(ARTIFACT_UPDATE_EVENT, this.handleArtifactUpdate)
  },
  methods: {
    manifestUrl() {
      return `/api/sessions/${this.sessionId}/analysis-artifacts`
    },
    artifactUrl(name) {
      return `/api/sessions/${this.sessionId}/artifacts/${encodeURIComponent(name)}`
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
      return {
        ...node,
        ...overrides,
        id,
        canonicalId: node.canonicalId || node.id || id,
        type,
        relation: overrides.relation || node.relation || node.relationToParent || '',
        label: this.nodeLabel({ ...node, type }),
        children: Array.isArray(node.children) ? [...node.children] : [],
      }
    },
    nodeType(node) {
      return node.type || node.kind || node.nodeType || 'Node'
    },
    nodeLabel(node) {
      return node.label || node.title || node.explanation || node.evidenceSummary || node.id || 'Untitled node'
    },
    formatValue(value) {
      if (Array.isArray(value)) return value.join(', ')
      if (value && typeof value === 'object') return JSON.stringify(value)
      return value
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

.legend-user {
  background: #ffffff;
  color: #475569;
}

.legend-patch {
  background: #fff1f5;
  border-color: #f7b7ca;
  color: #be185d;
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

.node-detail-panel {
  flex: 0 0 auto;
  margin-top: 10px;
  border: 1px solid #d8e0ec;
  border-radius: 8px;
  background: #ffffff;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.12),
    0 2px 8px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(148, 163, 184, 0.08);
  padding: 10px;
  max-height: 38%;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.detail-type,
.detail-patch {
  display: inline-flex;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  line-height: 16px;
  padding: 1px 7px;
}

.detail-type {
  background: #eef2ff;
  color: #4338ca;
}

.detail-patch {
  margin-left: 5px;
  background: #fff1f5;
  border: 1px solid #f7b7ca;
  color: #be185d;
}

.detail-title {
  color: #111827;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: 8px;
}

.detail-list {
  display: grid;
  gap: 5px;
  margin: 0;
}

.detail-list dt {
  color: #64748b;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.detail-list dd {
  color: #334155;
  font-size: 11px;
  line-height: 1.35;
  margin: 0 0 4px;
  overflow-wrap: anywhere;
}
</style>

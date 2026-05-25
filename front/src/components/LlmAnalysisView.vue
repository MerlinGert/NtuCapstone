<template>
  <div class="llm-analysis-view">
    <div class="analysis-toolbar">
      <div>
        <div class="analysis-title">Reasoning Forest</div>
        <div class="analysis-subtitle">
          User forest with agent patch nodes overlaid as supporting or qualifying evidence.
        </div>
      </div>
      <button class="refresh-btn" :disabled="loading || !sessionId" @click="loadAnalysis">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <div class="legend-row">
      <span class="legend-item legend-hypothesis">Hypothesis</span>
      <span class="legend-item legend-user">User reasoning node</span>
      <span class="legend-item legend-patch">Agent patch node</span>
    </div>

    <div v-if="loading" class="empty-state">Loading LLM analysis artifacts...</div>
    <div v-else-if="error" class="empty-state error-state">{{ error }}</div>
    <div v-else-if="!hasAnalysis" class="empty-state">
      No `user-reasoning-forest.json` and `reasoning-graph-patch.json` artifacts are available for this session yet.
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

const USER_ARTIFACT = 'user-reasoning-forest.json'
const PATCH_ARTIFACT = 'reasoning-graph-patch.json'

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
  },
  data() {
    return {
      loading: false,
      error: '',
      userForest: null,
      graphPatch: null,
      selectedNode: null,
      loadStarted: false,
    }
  },
  computed: {
    hasAnalysis() {
      return this.forestTrees.length > 0
    },
    forestTrees() {
      if (!this.userForest || !Array.isArray(this.userForest.roots)) return []
      const userNodes = this.userForest.nodes && typeof this.userForest.nodes === 'object'
        ? this.userForest.nodes
        : {}
      const patchNodes = new Map(
        Array.isArray(this.graphPatch?.nodes)
          ? this.graphPatch.nodes.map((node) => [node.id, node])
          : [],
      )
      const patchChildrenByTarget = this.buildPatchChildrenByTarget(patchNodes)
      return this.userForest.roots.map((root, index) =>
        this.buildDisplayNode(root, {
          userNodes,
          patchChildrenByTarget,
          patchNodes,
          path: `root-${index}`,
          visited: new Set(),
        }),
      )
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
        this.userForest = null
        this.graphPatch = null
        this.selectedNode = null
        this.loadAnalysis()
      },
    },
  },
  methods: {
    artifactUrl(name) {
      return `/api/sessions/${this.sessionId}/artifacts/${encodeURIComponent(name)}`
    },
    async fetchArtifact(name) {
      const response = await fetch(this.artifactUrl(name))
      if (response.status === 404 || response.status === 400) return null
      if (!response.ok) throw new Error(`Failed to load ${name}: HTTP ${response.status}`)
      return response.json()
    },
    async loadAnalysis() {
      if (!this.sessionId) {
        this.error = 'No active ManiScope session.'
        return
      }
      this.loading = true
      this.error = ''
      this.loadStarted = true
      try {
        const [userForest, graphPatch] = await Promise.all([
          this.fetchArtifact(USER_ARTIFACT),
          this.fetchArtifact(PATCH_ARTIFACT),
        ])
        this.userForest = userForest
        this.graphPatch = graphPatch
      } catch (error) {
        this.error = error && error.message ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    buildPatchChildrenByTarget(patchNodes) {
      const grouped = new Map()
      const edges = Array.isArray(this.graphPatch?.edges) ? this.graphPatch.edges : []
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
          (child) => child.relation === 'synthesizes' && child.node.type === 'Insight',
        )
        if (synthesisNodes.length === 0) {
          nested.set(targetId, children)
          continue
        }

        const containedChildren = children.filter(
          (child) => !(child.relation === 'synthesizes' && child.node.type === 'Insight'),
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
      const displayNode = {
        ...canonical,
        source: isPatch ? 'patch' : 'user',
        relation: rawNode.relation || '',
        label: this.nodeLabel(canonical),
        instanceId: `${context.path}-${canonical.id}`,
        children: [],
      }

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
          this.buildDisplayNode(
            {
              ...patchChild.node,
              relation: patchChild.relation,
              nestedPatchChildren: patchChild.nestedPatchChildren || [],
            },
            {
              ...context,
              path: `${context.path}-p${index}`,
              visited: nextVisited,
            },
          ),
        ),
      )

      const nestedPatchChildren = Array.isArray(canonical.nestedPatchChildren)
        ? canonical.nestedPatchChildren
        : []
      displayNode.children.push(
        ...nestedPatchChildren.map((patchChild, index) =>
          this.buildDisplayNode(
            { ...patchChild.node, relation: patchChild.relation },
            {
              ...context,
              path: `${context.path}-nested${index}`,
              visited: nextVisited,
            },
          ),
        ),
      )

      return displayNode
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
  box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.08);
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

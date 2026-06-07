<template>
  <div
    class="reasoning-node-card"
    :class="cardClasses"
    @click.stop="$emit('select-node', node)"
  >
    <div class="node-meta-row">
      <span class="node-type" :class="nodeTypeClass">{{ nodeTypeLabel }}</span>
      <label
        v-if="isEvaluableNode"
        class="node-evaluation-toggle"
        title="Mark as valuable and valid"
        aria-label="Mark this finding or hypothesis as valuable and valid"
        @click.stop
      >
        <input
          type="checkbox"
          :checked="isNodeEvaluated"
          @change.stop="$emit('toggle-evaluation', node)"
        />
      </label>
      <span v-if="relationLabel" class="relation-pill" :class="relationClass">
        {{ relationLabel }}
      </span>
      <span class="meta-spacer"></span>
      <button
        v-if="hasChildren"
        class="collapse-btn"
        type="button"
        :aria-label="collapsed ? 'Expand node' : 'Collapse node'"
        @click.stop="collapsed = !collapsed"
      >
        {{ collapsed ? '+' : '-' }}
      </button>
    </div>
    <div class="node-title" :title="node.label">{{ node.label }}</div>
    <div v-if="displayExplanation" class="node-explanation">
      {{ displayExplanation }}
    </div>
    <div v-if="showThumbnails" class="node-thumbnails">
      <div
        v-for="image in visibleEvidenceImages"
        :key="image.url"
        class="node-thumbnail-wrap"
      >
        <img
          class="node-thumbnail"
          :src="image.url"
          :alt="image.label"
          :title="image.label"
          loading="lazy"
        />
      </div>
      <div v-if="extraImageCount > 0" class="thumbnail-count">+{{ extraImageCount }} more images</div>
    </div>
    <div
      v-if="hasChildren && !collapsed"
      class="node-children"
      :class="{ 'node-children-single': node.children.length === 1 }"
    >
      <ReasoningNodeCard
        v-for="child in node.children"
        :key="child.instanceId || child.id"
        :node="child"
        :nesting-level="nestingLevel + 1"
        :hide-patch-label="childHidePatchLabel"
        :node-evaluations="nodeEvaluations"
        @select-node="$emit('select-node', $event)"
        @toggle-evaluation="$emit('toggle-evaluation', $event)"
      />
    </div>
  </div>
</template>

<script>
import {
  evaluationKeyForNode,
  isEvaluableAnalysisNode,
} from '../utils/llmAnalysisEvaluations.js'

export default {
  name: 'ReasoningNodeCard',
  emits: ['select-node', 'toggle-evaluation'],
  props: {
    node: {
      type: Object,
      required: true,
    },
    nestingLevel: {
      type: Number,
      default: 0,
    },
    hidePatchLabel: {
      type: Boolean,
      default: false,
    },
    nodeEvaluations: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      collapsed: this.shouldCollapseByDefault(),
    }
  },
  watch: {
    node: {
      handler() {
        this.collapsed = this.shouldCollapseByDefault()
      },
    },
  },
  computed: {
    hasChildren() {
      return Array.isArray(this.node.children) && this.node.children.length > 0
    },
    isEvaluableNode() {
      return isEvaluableAnalysisNode(this.node)
    },
    evaluationKey() {
      return evaluationKeyForNode(this.node)
    },
    isNodeEvaluated() {
      return Boolean(this.evaluationKey && this.nodeEvaluations?.[this.evaluationKey]?.checked)
    },
    childHidePatchLabel() {
      return this.hidePatchLabel
    },
    evidenceImages() {
      return Array.isArray(this.node.displayEvidenceImages)
        ? this.node.displayEvidenceImages
        : Array.isArray(this.node.evidenceImages)
          ? this.node.evidenceImages
          : []
    },
    isSynthesisFinding() {
      if (this.node.type !== 'Finding') return false
      const children = Array.isArray(this.node.children) ? this.node.children : []
      return children.some((child) => child.type === 'Finding')
    },
    showThumbnails() {
      return this.node.type === 'Finding'
        && !this.isSynthesisFinding
        && this.evidenceImages.length > 0
        && !this.collapsed
    },
    visibleEvidenceImages() {
      return this.evidenceImages.slice(0, 3)
    },
    extraImageCount() {
      return Math.max(0, this.evidenceImages.length - this.visibleEvidenceImages.length)
    },
    displayExplanation() {
      const candidates = [
        this.node.displayExplanation,
        this.node.displayEvidenceSummary,
        this.node.displayReasoningRole,
        this.node.explanation,
        this.node.evidenceSummary,
        this.node.patchRationale,
      ]
      const text = candidates.find(
        (item) => typeof item === 'string' && item.trim() && item.trim() !== this.node.label,
      )
      return text ? text.trim() : ''
    },
    cardClasses() {
      return {
        'source-user': this.node.source !== 'patch',
        'source-patch': this.node.source === 'patch',
        'type-hypothesis': this.node.type === 'Hypothesis',
        'derived-hypothesis': this.isDerivedHypothesis,
        'root-hypothesis': this.node.type === 'Hypothesis' && !this.node.parentInstanceId,
        'type-question': this.node.type === 'AnalyticQuestion',
        'type-finding': this.node.type === 'Finding',
        [`relation-${this.relationName}`]: Boolean(this.relationName),
      }
    },
    isDerivedHypothesis() {
      return this.node.type === 'Hypothesis' && this.node.source === 'patch'
    },
    nodeTypeLabel() {
      if (this.isDerivedHypothesis) return 'Derived Hypothesis'
      if (this.node.type === 'Finding') {
        return this.node.source === 'patch' ? 'Agent Finding' : 'User Finding'
      }
      return this.node.type || 'Node'
    },
    nodeTypeClass() {
      return {
        'node-type-derived-hypothesis': this.isDerivedHypothesis,
        'node-type-user-finding': this.node.type === 'Finding' && this.node.source !== 'patch',
        'node-type-agent-finding': this.node.type === 'Finding' && this.node.source === 'patch',
      }
    },
    relationName() {
      return this.normalizedRelation(this.node.displayRelation || this.node.relation)
    },
    relationLabel() {
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
      return labels[this.relationName] || this.humanizeRelation(this.node.displayRelation || this.node.relation)
    },
    relationClass() {
      return this.relationName ? `relation-pill-${this.relationName}` : ''
    },
  },
  methods: {
    shouldCollapseByDefault() {
      if (this.node.type === 'AnalyticActivity') return true
      const children = Array.isArray(this.node.children) ? this.node.children : []
      if (this.node.type === 'Finding' && this.nestingLevel === 1 && children.length > 0) {
        return true
      }
      return children.length > 0 && children.every((child) => child.type === 'Interaction')
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
    humanizeRelation(relation) {
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
.reasoning-node-card {
  width: 100%;
  min-width: 0;
  border: 1px solid #d8e0ec;
  border-radius: 7px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  padding: 8px;
}

.reasoning-node-card + .reasoning-node-card {
  margin-top: 8px;
}

.root-hypothesis {
  background: #d9e3ff;
  border-color: #aabce8;
}

.derived-hypothesis {
  background: #fff0f7;
  border-color: #f3b4d0;
}

.source-user.type-finding {
  background: #edf4ff;
  border-color: #b8cdf8;
}

.source-patch.type-finding {
  background: #fff0f7;
  border-color: #f3b4d0;
}

.source-user.type-question {
  background: #ffffff;
  border-color: #cbd5e1;
}

.node-meta-row {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  min-width: 0;
}

.node-type,
.relation-pill,
.collapse-btn {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  border-radius: 999px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.node-type,
.relation-pill,
.collapse-btn {
  padding: 1px 6px;
}

.node-evaluation-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  cursor: pointer;
}

.node-evaluation-toggle input {
  width: 13px;
  height: 13px;
  margin: 0;
  cursor: pointer;
  accent-color: #2563eb;
}

.node-type {
  color: #334155;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.45);
}

.node-type-user-finding {
  color: #1d4ed8;
  background: #dbeafe;
  border-color: #93c5fd;
}

.node-type-derived-hypothesis {
  color: #be185d;
  background: #fce7f3;
  border-color: #f9a8d4;
}

.node-type-agent-finding {
  color: #be185d;
  background: #fce7f3;
  border-color: #f9a8d4;
}

.relation-pill {
  max-width: 58%;
  overflow: hidden;
  text-overflow: ellipsis;
  border: 1px solid rgba(148, 163, 184, 0.38);
}

.relation-pill-supports {
  color: #166534;
  background: #ecfdf3;
  border-color: #86efac;
}

.relation-pill-answers {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #93c5fd;
}

.relation-pill-contradicts {
  color: #be123c;
  background: #fff1f2;
  border-color: #fb7185;
}

.relation-pill-refines {
  color: #92400e;
  background: #fffbeb;
  border-color: #fbbf24;
}

.relation-pill-synthesizes {
  color: #5b21b6;
  background: #f5f3ff;
  border-color: #c4b5fd;
}

.relation-pill-produces,
.relation-pill-motivates,
.relation-pill-contains,
.relation-pill-derived_from {
  color: #475569;
  background: #f8fafc;
  border-color: #cbd5e1;
}

.meta-spacer {
  flex: 1 1 auto;
  min-width: 12px;
}

.collapse-btn {
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: rgba(255, 255, 255, 0.8);
  color: #475569;
  cursor: pointer;
}

.collapse-btn:hover {
  background: #ffffff;
  border-color: #94a3b8;
}

.node-title {
  color: #111827;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.node-explanation {
  color: #475569;
  font-size: 12px;
  line-height: 1.45;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.node-thumbnails {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
  min-width: 0;
  width: 100%;
}

.node-thumbnail-wrap {
  width: 100%;
}

.node-thumbnail {
  display: block;
  width: 100%;
  max-height: 240px;
  object-fit: contain;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 5px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.thumbnail-count {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  line-height: 18px;
  padding: 4px 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.78);
  align-self: flex-start;
}

.node-children {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 9px;
  padding: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(148, 163, 184, 0.28);
}

.node-children-single {
  padding: 0;
  border: 0;
  background: transparent;
}
</style>

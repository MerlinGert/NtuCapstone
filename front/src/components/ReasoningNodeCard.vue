<template>
  <div
    class="reasoning-node-card"
    :class="cardClasses"
    @click.stop="handleCardClick"
  >
    <div class="node-meta-row">
      <span class="node-type" :class="nodeTypeClass">{{ nodeTypeLabel }}</span>
      <span v-if="isNewNode" class="node-new-badge">New</span>
      <span v-if="relationLabel" class="relation-pill" :class="relationClass">
        {{ relationLabel }}
      </span>
      <span class="meta-spacer"></span>
      <button
        v-if="hasChildren"
        class="collapse-btn"
        type="button"
        :aria-label="collapsed ? 'Expand node' : 'Collapse node'"
        @click.stop="toggleCollapsed"
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
      v-if="showEvaluationSection"
      class="node-evaluation-panel"
      @click.stop
    >
      <template v-if="node.type === 'Hypothesis'">
        <div class="node-evaluation-field">
          <div class="node-evaluation-label">Aligned with my analysis?</div>
          <div class="node-evaluation-options">
            <label
              v-for="option in hypothesisAlignmentOptions"
              :key="`align-${option.value}`"
              class="node-evaluation-option"
              @click.stop
            >
              <input
                type="radio"
                :name="`${evaluationKey || node.id}-aligned`"
                :value="option.value"
                :checked="activeEvaluation.hypothesisAligned === option.value"
                @click.stop
                @change.stop="updateHypothesisEvaluation('hypothesisAligned', option.value)"
              />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>
        <div class="node-evaluation-field">
          <div class="node-evaluation-label">Associated findings sufficient for evaluation?</div>
          <div class="node-evaluation-options node-evaluation-options-wide">
            <label
              v-for="option in hypothesisSufficiencyOptions"
              :key="`sufficient-${option.value}`"
              class="node-evaluation-option"
              @click.stop
            >
              <input
                type="radio"
                :name="`${evaluationKey || node.id}-sufficiency`"
                :value="option.value"
                :checked="activeEvaluation.findingsSufficiency === option.value"
                @click.stop
                @change.stop="updateHypothesisEvaluation('findingsSufficiency', option.value)"
              />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>
      </template>
      <template v-else-if="node.type === 'Finding'">
        <div class="node-evaluation-field">
          <div class="node-evaluation-label">Associated hypothesis</div>
          <select
            class="node-evaluation-select"
            :value="selectedAssociatedHypothesisValue"
            @click.stop
            @change.stop="updateFindingAssociation($event)"
          >
            <option value="" disabled>Select hypothesis</option>
            <option
              v-for="option in findingAssociationOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="node-evaluation-field">
          <div class="node-evaluation-label">Relevant to the associated hypothesis?</div>
          <div class="node-evaluation-options">
            <label
              v-for="option in findingRelevanceOptions"
              :key="`relevant-${option.value}`"
              class="node-evaluation-option"
              @click.stop
            >
              <input
                type="radio"
                :name="`${evaluationKey || node.id}-relevance`"
                :value="option.value"
                :checked="activeEvaluation.relevanceToHypothesis === option.value"
                @click.stop
                @change.stop="updateFindingEvaluation('relevanceToHypothesis', option.value)"
              />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>
      </template>
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
        :new-node-ids="newNodeIds"
        :hypothesis-options="hypothesisOptions"
        :finding-associations="findingAssociations"
        :expansion-command="expansionCommand"
        :show-evaluation-ui="showEvaluationUi"
        @select-node="$emit('select-node', $event)"
        @update-evaluation="$emit('update-evaluation', $event)"
        @toggle-node="$emit('toggle-node', $event)"
      />
    </div>
  </div>
</template>

<script>
import {
  evaluationKeyForNode,
  isEvaluableAnalysisNode,
} from '../utils/llmAnalysisEvaluations.js'

const HYPOTHESIS_ALIGNMENT_OPTIONS = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'unsure', label: 'Unsure' },
]

const HYPOTHESIS_SUFFICIENCY_OPTIONS = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'partially', label: 'Partially' },
  { value: 'unsure', label: 'Unsure' },
]

const FINDING_RELEVANCE_OPTIONS = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'unsure', label: 'Unsure' },
]

const NONE_ASSOCIATED_HYPOTHESIS = '__none__'
const EMPTY_EVALUATION = Object.freeze({})

function cloneEvaluation(value) {
  return value && typeof value === 'object' ? { ...value } : {}
}

export default {
  name: 'ReasoningNodeCard',
  emits: ['select-node', 'update-evaluation', 'toggle-node'],
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
    newNodeIds: {
      type: Object,
      default: () => ({}),
    },
    hypothesisOptions: {
      type: Array,
      default: () => [],
    },
    findingAssociations: {
      type: Object,
      default: () => ({}),
    },
    expansionCommand: {
      type: Object,
      default: null,
    },
    showEvaluationUi: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      collapsed: this.shouldCollapseByDefault(),
      localEvaluation: cloneEvaluation(this.nodeEvaluations?.[evaluationKeyForNode(this.node)]),
    }
  },
  watch: {
    node: {
      handler() {
        this.collapsed = this.shouldCollapseByDefault()
        this.localEvaluation = cloneEvaluation(this.currentEvaluation)
      },
    },
    expansionCommand: {
      handler(command) {
        if (!command || !this.hasChildren) return
        if (command.mode === 'expand') this.collapsed = false
        if (command.mode === 'collapse') this.collapsed = true
      },
      deep: true,
    },
    currentEvaluation: {
      handler(nextValue) {
        this.localEvaluation = cloneEvaluation(nextValue)
      },
      deep: true,
      immediate: true,
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
    currentEvaluation() {
      return this.evaluationKey && this.nodeEvaluations?.[this.evaluationKey]
        ? this.nodeEvaluations[this.evaluationKey]
        : EMPTY_EVALUATION
    },
    activeEvaluation() {
      return this.localEvaluation && typeof this.localEvaluation === 'object'
        ? this.localEvaluation
        : {}
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
    showEvaluationSection() {
      return this.showEvaluationUi && this.isEvaluableNode && !this.collapsed
    },
    hypothesisAlignmentOptions() {
      return HYPOTHESIS_ALIGNMENT_OPTIONS
    },
    hypothesisSufficiencyOptions() {
      return HYPOTHESIS_SUFFICIENCY_OPTIONS
    },
    findingRelevanceOptions() {
      return FINDING_RELEVANCE_OPTIONS
    },
    selectedAssociatedHypothesisValue() {
      if (Object.prototype.hasOwnProperty.call(this.activeEvaluation, 'associatedHypothesisId')) {
        return this.activeEvaluation.associatedHypothesisId == null
          ? NONE_ASSOCIATED_HYPOTHESIS
          : this.activeEvaluation.associatedHypothesisId
      }
      const fallback = this.defaultAssociatedHypothesis
      return fallback?.value || ''
    },
    findingAssociationOptions() {
      const options = (this.hypothesisOptions || []).map((option) => ({
        value: option.value,
        label: option.label,
      }))
      options.push({ value: NONE_ASSOCIATED_HYPOTHESIS, label: 'None' })
      return options
    },
    defaultAssociatedHypothesis() {
      return this.evaluationKey ? this.findingAssociations?.[this.evaluationKey] || null : null
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
    isNewNode() {
      if (!this.isEvaluableNode) return false
      const key = evaluationKeyForNode(this.node)
      return Boolean(key && this.newNodeIds?.[key])
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
    handleCardClick(event) {
      const target = event?.target
      if (target instanceof Element && target.closest('input, select, option, label, button, a, textarea')) {
        return
      }
      this.$emit('select-node', this.node)
    },
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
    toggleCollapsed() {
      this.collapsed = !this.collapsed
      this.$emit('toggle-node', {
        node: this.node,
        collapsed: this.collapsed,
        nestingLevel: this.nestingLevel,
      })
    },
    updateHypothesisEvaluation(field, value) {
      this.localEvaluation = {
        ...this.activeEvaluation,
        nodeKind: 'Hypothesis',
        [field]: value,
      }
      this.$emit('update-evaluation', {
        node: this.node,
        patch: {
          [field]: value,
        },
      })
    },
    updateFindingEvaluation(field, value) {
      const patch = { [field]: value }
      if (!Object.prototype.hasOwnProperty.call(this.activeEvaluation, 'associatedHypothesisId') && this.defaultAssociatedHypothesis) {
        patch.associatedHypothesisId = this.defaultAssociatedHypothesis.value
        patch.associatedHypothesisLabel = this.defaultAssociatedHypothesis.label
      }
      this.localEvaluation = {
        ...this.activeEvaluation,
        nodeKind: 'Finding',
        ...patch,
      }
      this.$emit('update-evaluation', {
        node: this.node,
        patch,
      })
    },
    updateFindingAssociation(event) {
      const value = event?.target?.value || ''
      if (!value) return
      if (value === NONE_ASSOCIATED_HYPOTHESIS) {
        this.localEvaluation = {
          ...this.activeEvaluation,
          nodeKind: 'Finding',
          associatedHypothesisId: null,
          associatedHypothesisLabel: 'None',
        }
        this.$emit('update-evaluation', {
          node: this.node,
          patch: {
            associatedHypothesisId: null,
            associatedHypothesisLabel: 'None',
          },
        })
        return
      }
      const option = this.findingAssociationOptions.find((item) => item.value === value)
      this.localEvaluation = {
        ...this.activeEvaluation,
        nodeKind: 'Finding',
        associatedHypothesisId: value,
        associatedHypothesisLabel: option?.label || value,
      }
      this.$emit('update-evaluation', {
        node: this.node,
        patch: {
          associatedHypothesisId: value,
          associatedHypothesisLabel: option?.label || value,
        },
      })
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
.node-new-badge,
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
.node-new-badge,
.relation-pill,
.collapse-btn {
  padding: 1px 6px;
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

.node-new-badge {
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #93c5fd;
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

.node-evaluation-panel {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
}

.node-evaluation-field {
  display: grid;
  gap: 6px;
}

.node-evaluation-label {
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

.node-evaluation-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
}

.node-evaluation-options-wide {
  gap: 8px;
}

.node-evaluation-option {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #334155;
  font-size: 11px;
}

.node-evaluation-option input {
  margin: 0;
  accent-color: #2563eb;
}

.node-evaluation-select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #1f2937;
  font-size: 12px;
  padding: 6px 8px;
  box-sizing: border-box;
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

<template>
  <n-card
    size="small"
    class="panel-card notes-panel"
    style="width:100%;height:100%;display:flex;flex-direction:column;"
    header-style="text-align:left;height:50px;font-size:1.2em;padding:10px;"
    :content-style="{ padding: 0, height: 'calc(100% - 50px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
  >
    <template #header>
      <div style="display:flex; gap:10px; margin-top: 5px;">
        <button
          v-if="!analysisOnly"
          class="tab-btn"
          :class="{ active: activeTab === 'actions' }"
          @click="setActiveTab('actions')"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'actions' ? 'color:#3182ce; border-bottom-color:#3182ce;' : ''"
        >User Actions</button>
        <button
          v-if="!analysisOnly"
          class="tab-btn"
          :class="{ active: activeTab === 'annotations' }"
          @click="setActiveTab('annotations')"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'annotations' ? 'color:#d97706; border-bottom-color:#d97706;' : ''"
        >Annotations</button>
        <button
          v-if="!analysisOnly"
          class="tab-btn"
          :class="{ active: activeTab === 'tree' }"
          @click="setActiveTab('tree')"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'tree' ? 'color:#059669; border-bottom-color:#059669;' : ''"
        >Action Tree</button>
        <button
          v-if="showLlmAnalysis"
          class="tab-btn"
          :class="{ active: activeTab === 'llm_analysis' }"
          @click="setActiveTab('llm_analysis')"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'llm_analysis' ? 'color:#805ad5; border-bottom-color:#805ad5;' : ''"
        >LLM Analysis</button>
      </div>
    </template>

    <div v-if="!analysisOnly" v-show="activeTab === 'actions'" style="flex:1; overflow:hidden;">
      <UserActionTimeline
          :actions="actions"
          :snapshot-categories="snapshotCategories"
          :snapshot-quality="snapshotQuality"
          @toggle-category="$emit('toggle-category', $event)"
          @change-quality="$emit('change-quality', $event)"
          style="height:100%;"
      />
    </div>

    <div v-if="!analysisOnly" v-show="activeTab === 'annotations'" style="flex:1; overflow:hidden;">
      <AnnotationTimeline
          :annotations="annotations"
          style="height:100%;"
      />
    </div>

    <div
      v-if="!analysisOnly"
      v-show="activeTab === 'tree'"
      style="flex:1; display:flex; flex-direction:column; overflow:hidden;"
    >
      <UserActionTree
          :actions="actions"
          :annotations="annotations"
          :read-only="readOnly"
          @add-finding-annotation="$emit('add-finding-annotation', $event)"
          @delete-annotation="$emit('delete-annotation', $event)"
          @delete-action="$emit('delete-action', $event)"
          @update-annotation="$emit('update-annotation', $event)"
          @add-custom-annotation="$emit('add-custom-annotation', $event)"
          @reorder-action="$emit('reorder-action', $event)"
      />
    </div>

    <div v-if="showLlmAnalysis" v-show="activeTab === 'llm_analysis'" style="flex:1; padding:10px; overflow:hidden;">
      <LlmAnalysisView
        ref="llmAnalysisView"
        :session-id="sessionId"
        :session-mode="sessionMode"
        :active="activeTab === 'llm_analysis'"
        :analysis-payload="analysisPayload"
        @log-action="$emit('log-action', $event)"
        @analysis-trace="$emit('analysis-trace', $event)"
      />
    </div>
  </n-card>
</template>

<script>
import { NCard } from 'naive-ui'
import UserActionTree from './UserActionTree.vue'
import UserActionTimeline from './UserActionTimeline.vue'
import AnnotationTimeline from './AnnotationTimeline.vue'
import LlmAnalysisView from './LlmAnalysisView.vue'

export default {
  name: 'NotesPanel',
  components: {
    NCard,
    UserActionTree,
    UserActionTimeline,
    AnnotationTimeline,
    LlmAnalysisView
  },
  emits: ['tab-change', 'log-action', 'analysis-trace'],
  props: {
    sessionId: {
      type: String,
      default: ''
    },
    sessionMode: {
      type: String,
      default: 'specialized',
      validator: (value) => ['specialized', 'baseline'].includes(value),
    },
    actions: {
      type: Array,
      default: () => []
    },
    annotations: {
      type: Array,
      default: () => []
    },
    readOnly: {
      type: Boolean,
      default: false
    },
    snapshotCategories: {
      type: Array,
      default: () => []
    },
    snapshotQuality: {
      type: Number,
      default: 0.8
    },
    analysisPayload: {
      type: Object,
      default: null
    },
    initialTab: {
      type: String,
      default: 'tree'
    },
    analysisOnly: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      activeTab: this.analysisOnly
        ? 'llm_analysis'
        : (this.sessionMode === 'baseline' && this.initialTab === 'llm_analysis' ? 'tree' : this.initialTab)
    }
  },
  computed: {
    showLlmAnalysis() {
      return this.analysisOnly || this.sessionMode !== 'baseline'
    }
  },
  watch: {
    initialTab(nextTab) {
      if (!this.analysisOnly && nextTab) {
        this.activeTab = this.resolveActiveTab(nextTab)
      }
    },
    analysisOnly(enabled) {
      if (enabled) this.activeTab = 'llm_analysis'
      else this.activeTab = this.resolveActiveTab(this.activeTab)
    },
    sessionMode() {
      this.activeTab = this.resolveActiveTab(this.activeTab)
    }
  },
  methods: {
    async getAnalysisExportPayload() {
      if (!this.showLlmAnalysis) return null
      if (!this.$refs.llmAnalysisView?.buildAnalysisExportPayload) return null
      if (this.$refs.llmAnalysisView?.refreshAnalysis) {
        await this.$refs.llmAnalysisView.refreshAnalysis()
      }
      return this.$refs.llmAnalysisView.buildAnalysisExportPayload()
    },
    setActiveTab(tab) {
      const nextTab = this.resolveActiveTab(tab)
      if (nextTab === this.activeTab) return
      this.activeTab = nextTab
      this.$emit('tab-change', nextTab)
    },
    resolveActiveTab(tab) {
      if (tab === 'llm_analysis' && !this.showLlmAnalysis) return 'tree'
      return tab || 'tree'
    }
  }
}
</script>

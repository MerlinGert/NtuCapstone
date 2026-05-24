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
          class="tab-btn"
          :class="{ active: activeTab === 'actions' }"
          @click="activeTab = 'actions'"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'actions' ? 'color:#3182ce; border-bottom-color:#3182ce;' : ''"
        >User Actions</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'annotations' }"
          @click="activeTab = 'annotations'"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'annotations' ? 'color:#d97706; border-bottom-color:#d97706;' : ''"
        >Annotations</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'tree' }"
          @click="activeTab = 'tree'"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'tree' ? 'color:#059669; border-bottom-color:#059669;' : ''"
        >Action Tree</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'llm_analysis' }"
          @click="activeTab = 'llm_analysis'"
          style="padding:4px 8px; border:none; background:none; cursor:pointer; font-size:14px; font-weight:600; color:#718096; border-bottom:2px solid transparent;"
          :style="activeTab === 'llm_analysis' ? 'color:#805ad5; border-bottom-color:#805ad5;' : ''"
        >LLM Analysis</button>
      </div>
    </template>

    <div v-show="activeTab === 'actions'" style="flex:1; overflow:hidden;">
      <UserActionTimeline
          :actions="actions"
          :snapshot-categories="snapshotCategories"
          :snapshot-quality="snapshotQuality"
          @toggle-category="$emit('toggle-category', $event)"
          @change-quality="$emit('change-quality', $event)"
          style="height:100%;"
      />
    </div>

    <div v-show="activeTab === 'annotations'" style="flex:1; overflow:hidden;">
      <AnnotationTimeline
          :annotations="annotations"
          style="height:100%;"
      />
    </div>

    <div v-show="activeTab === 'tree'" style="flex:1; display:flex; flex-direction:column; overflow:hidden;">
      <UserActionTree
          :actions="actions"
          :annotations="annotations"
          :read-only="readOnly"
          @add-insight-annotation="$emit('add-insight-annotation', $event)"
          @delete-annotation="$emit('delete-annotation', $event)"
          @delete-action="$emit('delete-action', $event)"
          @update-annotation="$emit('update-annotation', $event)"
          @add-custom-annotation="$emit('add-custom-annotation', $event)"
          @reorder-action="$emit('reorder-action', $event)"
          style="height:100%;"
      />
    </div>

    <div v-show="activeTab === 'llm_analysis'" style="flex:1; padding:10px; overflow-y:auto;">
      <!-- LLM Analysis is initially blank -->
      <div style="color:#a0aec0; font-size:12px; text-align:center; margin-top:20px;">
        LLM Analysis will appear here...
      </div>
    </div>
  </n-card>
</template>

<script>
import { NCard } from 'naive-ui'
import UserActionTree from './UserActionTree.vue'
import UserActionTimeline from './UserActionTimeline.vue'
import AnnotationTimeline from './AnnotationTimeline.vue'

export default {
  name: 'NotesPanel',
  components: {
    NCard,
    UserActionTree,
    UserActionTimeline,
    AnnotationTimeline
  },
  props: {
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
    }
  },
  data() {
    return {
      activeTab: 'tree'
    }
  }
}
</script>

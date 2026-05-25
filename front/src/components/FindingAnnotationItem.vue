<template>
  <div class="finding-anno-item" style="margin-bottom: 8px; border-left: 2px solid #cbd5e1; padding-left: 8px; margin-left: 4px;">
    <template v-if="itemData">
      <div class="anno-time">
        <span v-if="isFinding" style="background: #3182ce; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; margin-right: 4px;">Finding</span>
        <span style="font-weight: bold; color: #718096; margin-right: 4px;">#{{ itemId !== undefined ? itemId : 'N/A' }}</span>
        {{ new Date(itemData.timestamp || Date.now()).toLocaleString() }}
      </div>
      <div class="anno-text" :style="isFinding ? 'font-weight: 600; color: #2b6cb0;' : ''">{{ text }}</div>
      <div v-if="sketchUrl" class="popup-image-container" style="max-width: 100%; margin-top: 8px;">
        <img :src="sketchUrl" class="popup-image" alt="Annotation Sketch" style="border: 1px solid #e2e8f0; border-radius: 4px;" />
      </div>
      
      <div v-if="isFinding && refAnnotations && refAnnotations.length > 0" class="nested-findings" style="margin-top: 8px;">
        <FindingAnnotationItem 
          v-for="childId in refAnnotations" 
          :key="childId" 
          :item-id="childId" 
          :annotations="annotations" 
          :actions="actions" 
        />
      </div>
    </template>
    <template v-else>
      <div class="anno-text" style="color: #a0aec0; font-style: italic;">Reference (ID: {{ itemId }}) not found</div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'FindingAnnotationItem',
  props: {
    itemId: { type: [String, Number], required: true },
    annotations: { type: Array, required: true },
    actions: { type: Array, required: true }
  },
  computed: {
    annoRecord() {
      return this.annotations.find(a => a.id === this.itemId);
    },
    actionRecord() {
      return this.actions.find(a => a.actionInfo && a.actionInfo.id === this.itemId);
    },
    itemData() {
      if (this.annoRecord) return this.annoRecord;
      if (this.actionRecord) {
        return {
          ...this.actionRecord.actionInfo,
          timestamp: this.actionRecord.timestamp // fallback to action timestamp if missing in actionInfo
        };
      }
      return null;
    },
    isFinding() {
      if (this.annoRecord) return !!this.annoRecord.isFinding;
      if (this.actionRecord) return !!this.actionRecord.actionInfo.isFinding;
      return false;
    },
    text() {
      return this.itemData ? (this.itemData.text || 'No text provided') : '';
    },
    sketchUrl() {
      return this.itemData ? this.itemData.sketchDataUrl : null;
    },
    refAnnotations() {
      return this.itemData ? (this.itemData.selectedItems || this.itemData.refAnnotations || []) : [];
    }
  }
}
</script>

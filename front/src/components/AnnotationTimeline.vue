<template>
  <!-- ezio: Annotation Timeline - displays snapshot annotation records -->
  <div class="annotation-timeline-container">
    <div class="header-panel">
      <div class="panel-title">Annotations</div>
      <div class="count-badge">{{ annotations.length }}</div>
    </div>

    <div class="timeline-content" ref="scrollContainer">
      <div v-if="annotations.length === 0" class="empty-state">
        No annotations recorded yet.
      </div>

      <div v-else class="timeline-list">
        <div
          v-for="(anno, index) in annotations"
          :key="anno.id"
          class="timeline-item"
        >
          <div class="timeline-marker annotation-marker"></div>
          <div class="timeline-connector" v-if="index !== annotations.length - 1"></div>

          <div class="timeline-card" :class="{ 'is-expanded': expandedStates[index] }">
            <div class="action-header" @click="toggleExpand(index)" style="cursor: pointer;">
              <div class="action-header-left">
                <span class="expand-icon">{{ expandedStates[index] ? '▼' : '▶' }}</span>
                <span class="action-type annotation">Annotation</span>
              </div>
              <span class="action-time">{{ formatTime(anno.timestamp) }}</span>
            </div>

            <div class="action-body" @click="toggleExpand(index)" style="cursor: pointer;">
              <!-- ezio: source view -->
              <div class="action-detail">
                <span class="detail-label">Source View:</span>
                <span class="detail-value">{{ formatViewName(anno.sourceView) }}</span>
              </div>

              <!-- ezio: annotation text -->
              <div v-if="anno.text" class="action-detail">
                <span class="detail-label">Note:</span>
                <span class="detail-value">{{ anno.text }}</span>
              </div>

              <!-- ezio: selected entities summary -->
              <div v-if="anno.selectedItems && anno.selectedItems.length > 0" class="action-detail">
                <span class="detail-label">Selected:</span>
                <span class="detail-value">{{ formatSelections(anno.selectedItems) }}</span>
              </div>

              <!-- ezio: sketch thumbnail (collapsed) -->
              <div v-if="anno.sketchDataUrl && !expandedStates[index]" class="sketch-preview">
                <img :src="anno.sketchDataUrl" alt="Sketch" class="sketch-thumbnail" />
              </div>
            </div>

            <!-- ezio: Expanded Details Area -->
            <div v-if="expandedStates[index]" class="expanded-details">
              <!-- ezio: full sketch image -->
              <div v-if="anno.sketchDataUrl" class="detail-section">
                <div class="detail-section-title">Screenshot / Sketch</div>
                <img :src="anno.sketchDataUrl" alt="Sketch" class="sketch-full" />
              </div>

              <!-- ezio: selected items detail -->
              <div v-if="anno.selectedItems && anno.selectedItems.length > 0" class="detail-section">
                <div class="detail-section-title">Selected Items</div>
                <pre class="json-viewer">{{ formatJSON(anno.selectedItems) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// ezio: AnnotationTimeline component for displaying snapshot annotations
export default {
  name: 'AnnotationTimeline',
  props: {
    annotations: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      expandedStates: {}
    }
  },
  watch: {
    annotations: {
      handler(newVal) {
        if (newVal && newVal.length > 0) {
          this.$nextTick(() => {
            requestAnimationFrame(() => {
              this.scrollToBottom()
            })
          })
        }
      },
      deep: true
    }
  },
  methods: {
    toggleExpand(index) {
      this.expandedStates = {
        ...this.expandedStates,
        [index]: !this.expandedStates[index]
      }
    },
    scrollToBottom() {
      const container = this.$refs.scrollContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },
    formatTime(isoString) {
      if (!isoString) return ''
      const date = new Date(isoString)
      return date.toLocaleTimeString(undefined, {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    },
    formatViewName(view) {
      if (!view) return 'Unknown'
      return view.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    },
    // ezio: format selected items/ids for display
    formatSelections(items) {
      if (!items || items.length === 0) return ''
      if (typeof items[0] === 'string') {
        return `${items.length} node(s)`
      }
      return `${items.length} item(s)`
    },
    formatJSON(obj) {
      if (!obj) return '[]'
      try {
        return JSON.stringify(obj, null, 2)
      } catch (e) {
        return String(obj)
      }
    }
  }
}
</script>

<style scoped>
/* ezio: reuse UserActionTimeline styles for visual consistency */
.annotation-timeline-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #ffffff;
}

.header-panel {
  flex-shrink: 0;
  height: 32px;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a5568;
}

.count-badge {
  margin-left: 8px;
  background: #e2e8f0;
  color: #4a5568;
  font-size: 10px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
}

.timeline-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a0aec0;
  font-size: 12px;
  font-style: italic;
}

.timeline-list {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  position: relative;
  padding-left: 20px;
  padding-bottom: 12px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-marker {
  position: absolute;
  left: 4px;
  top: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid #fff;
  z-index: 2;
}

/* ezio: amber marker for annotations */
.annotation-marker {
  background-color: #d97706;
  box-shadow: 0 0 0 1px #d97706;
}

.timeline-connector {
  position: absolute;
  left: 7px;
  top: 14px;
  bottom: 0;
  width: 2px;
  background-color: #e2e8f0;
  z-index: 1;
}

.timeline-card {
  background: #f8fafc;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  padding: 8px 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.action-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.expand-icon {
  font-size: 10px;
  color: #a0aec0;
  width: 12px;
  text-align: center;
}

.action-type {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

/* ezio: amber badge for annotation type */
.action-type.annotation {
  background: #fef3c7;
  color: #92400e;
}

.action-time {
  font-size: 10px;
  color: #a0aec0;
}

.action-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-detail {
  display: flex;
  align-items: center;
  font-size: 11px;
}

.detail-label {
  color: #718096;
  margin-right: 4px;
}

.detail-value {
  color: #2d3748;
}

/* ezio: sketch thumbnail styles */
.sketch-preview {
  margin-top: 4px;
}

.sketch-thumbnail {
  max-width: 100%;
  max-height: 60px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  object-fit: contain;
  background: #f7fafc;
}

.sketch-full {
  max-width: 100%;
  max-height: 300px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  object-fit: contain;
  background: #f7fafc;
}

.timeline-card.is-expanded {
  border-color: #cbd5e1;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.expanded-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-section-title {
  font-size: 10px;
  font-weight: bold;
  color: #718096;
  text-transform: uppercase;
}

.json-viewer {
  margin: 0;
  padding: 8px;
  background: #2d3748;
  color: #e2e8f0;
  border-radius: 4px;
  font-family: monospace;
  font-size: 10px;
  line-height: 1.4;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}

.json-viewer::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.json-viewer::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 3px;
}
.json-viewer::-webkit-scrollbar-track {
  background: #1a202c;
  border-radius: 3px;
}
</style>

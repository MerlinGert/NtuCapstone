<template>
  <div class="user-action-timeline-container">
    <div class="header-panel">
      <div class="panel-title">User Actions</div>
      <div class="count-badge">{{ actions.length }}</div>
    </div>
    
    <div class="timeline-content" ref="scrollContainer">
      <div v-if="actions.length === 0" class="empty-state">
        No actions recorded yet.
      </div>
      
      <div v-else class="timeline-list">
        <div 
          v-for="(action, index) in actions" 
          :key="index" 
          class="timeline-item"
        >
          <div class="timeline-marker"></div>
          <div class="timeline-connector" v-if="index !== actions.length - 1"></div>
          
          <div class="timeline-card" :class="{ 'is-expanded': expandedStates[index] }">
            <div class="action-header" @click="toggleExpand(index)" style="cursor: pointer;">
              <div class="action-header-left">
                <span class="expand-icon">{{ expandedStates[index] ? '▼' : '▶' }}</span>
                <span class="action-type" :class="getActionClass(action.actionType)">
                  {{ formatActionType(action.actionType) }}
                </span>
              </div>
              <span class="action-time">{{ formatTime(action.timestamp) }}</span>
            </div>
            
            <div class="action-body" @click="toggleExpand(index)" style="cursor: pointer;">
              <div v-if="action.userId && action.userId !== 'system'" class="action-detail">
                <span class="detail-label">User:</span>
                <span class="detail-value user-id" :title="action.userId">{{ truncateId(action.userId) }}</span>
              </div>
              
              <div v-if="action.sourceView" class="action-detail">
                <span class="detail-label">Source View:</span>
                <span class="detail-value">{{ formatViewName(action.sourceView) }}</span>
              </div>
              
              <div v-if="action.targetView && action.targetView !== action.sourceView" class="action-detail">
                <span class="detail-label">Target View:</span>
                <span class="detail-value">{{ formatViewName(action.targetView) }}</span>
              </div>
              
              <div v-if="action.actionInfo" class="action-detail info-detail">
                <span class="detail-value">{{ formatActionInfo(action.actionType, action.actionInfo) }}</span>
              </div>
            </div>

            <!-- Expanded Details Area -->
            <div v-if="expandedStates[index]" class="expanded-details">
              <div class="detail-section">
                <div class="detail-section-title">Action Info</div>
                <pre class="json-viewer">{{ formatJSON(action.actionInfo) }}</pre>
              </div>
              
              <div class="detail-section" v-if="action.relatedViewWithViewState">
                <div class="detail-section-title">View State</div>
                <pre class="json-viewer">{{ formatJSON(action.relatedViewWithViewState) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserActionTimeline',
  props: {
    actions: {
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
    actions: {
      handler(newVal, oldVal) {
        // Because `actions` is often modified by pushing or by modifying the last element,
        // we always trigger a scroll if there are items, but only delay slightly for rendering.
        // We use requestAnimationFrame combined with nextTick to ensure the DOM has updated.
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
    formatJSON(obj) {
      if (!obj) return '{}'
      try {
        return JSON.stringify(obj, null, 2)
      } catch (e) {
        return String(obj)
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
    truncateId(id) {
      if (!id) return ''
      return id.length > 8 ? `${id.substring(0, 4)}..${id.substring(id.length - 4)}` : id
    },
    formatActionType(type) {
      if (!type) return 'Unknown'
      return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    },
    formatViewName(view) {
      if (!view) return 'Unknown'
      return view.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    },
    getActionClass(type) {
      if (!type) return 'default'
      if (type.includes('zoom')) return 'zoom'
      if (type.startsWith('hover_')) return 'hover'
      if (type.includes('select') || type.includes('click')) return 'interaction'
      if (type.includes('run') || type.includes('update')) return 'system'
      return 'default'
    },
    formatActionInfo(type, info) {
      if (!info) return ''
      
      // Handle the case where info was merged into an array of continuous actions
      const isMergedArray = Array.isArray(info)
      const count = isMergedArray ? info.length : 1
      const countStr = count > 1 ? ` (${count} continuous events)` : ''
      
      // Get the most relevant single item to summarize
      const summaryInfo = isMergedArray ? info[info.length - 1].data : info
      
      try {
        if (type === 'zoom_kline_chart' || type === 'zoom_behavior_chart') {
          return `Adjusted view time window${countStr}`
        }
        if (type === 'change_coin') {
          return `Changed to ${summaryInfo.coin}`
        }
        if (type === 'select_user_from_network' || type === 'select_user_from_behavior_details') {
          return `Selected for detailed view${countStr}`
        }
        if (type === 'click_manipulation_card') {
          const userCount = summaryInfo.cardUsers ? summaryInfo.cardUsers.length : 0
          return `Viewed manipulation group (${userCount} users)`
        }
        if (type === 'update_snapshot') {
          return 'Updated snapshot configuration'
        }
        if (type.includes('detection')) {
          return 'Ran detection process'
        }
        if (type.startsWith('hover_')) {
          return `Hovered elements${countStr}`
        }
        
        if (type === 'click_kline_align_cards') {
          return `Clicked K-line to align manipulation cards`
        }
        if (type === 'change_kline_granularity') {
          return `Changed K-line granularity to ${summaryInfo.label || summaryInfo.granularity}`
        }
        if (type === 'toggle_show_related_users') {
          return `${summaryInfo.enabled ? 'Enabled' : 'Disabled'} "Show Related Users"`
        }
        if (type === 'toggle_show_manipulation_boxes') {
          return `${summaryInfo.enabled ? 'Enabled' : 'Disabled'} "Show Manipulation Boxes"`
        }
        if (type === 'sync_time_window') {
          return `Synchronized time window from ${summaryInfo.source === 'kline_chart' ? 'K-line Chart' : 'Behavior Details'}`
        }
        
        // Fallback for unknown info
        const str = JSON.stringify(summaryInfo)
        return str.length > 40 ? str.substring(0, 40) + '...' : str
      } catch (e) {
        return `Details available${countStr}`
      }
    }
  }
}
</script>

<style scoped>
.user-action-timeline-container {
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
  background-color: #3182ce;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #3182ce;
  z-index: 2;
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

.action-type {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.action-type.interaction {
  background: #ebf8ff;
  color: #2b6cb0;
}

.action-type.zoom {
  background: #f0fff4;
  color: #2c7a7b;
}

.action-type.hover {
  background: #faf5ff;
  color: #2f855a;
}

.action-type.system {
  background: #fff5f5;
  color: #c53030;
}

.action-type.default {
  background: #edf2f7;
  color: #4a5568;
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

.user-id {
  font-family: monospace;
  background: #edf2f7;
  padding: 1px 4px;
  border-radius: 3px;
  cursor: help;
}

.info-detail {
  color: #4a5568;
  font-style: italic;
  margin-top: 2px;
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

/* Scrollbar styling for json viewer */
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

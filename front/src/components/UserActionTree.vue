<template>
  <div class="user-action-tree-container" ref="container">
    <div class="header-panel">
      <div class="panel-title">Action Tree</div>
      <div class="count-badge">{{ nodesCount }}</div>
      
      <!-- ezio: Multi-select insight buttons -->
      <div class="insight-controls" style="margin-left: 16px; display: flex; gap: 8px;">
        <button v-if="!isMultiSelectMode" class="insight-btn" @click="startMultiSelect" title="Create Insight" style="padding: 4px 8px; display: flex; align-items: center; justify-content: center; gap: 4px;">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
        </button>
        <template v-else>
          <button class="insight-btn cancel-btn" @click="cancelMultiSelect">Cancel</button>
          <button class="insight-btn confirm-btn" @click="openInsightPopup" :disabled="selectedInsightAnnotations.length === 0">
            Confirm ({{ selectedInsightAnnotations.length }})
          </button>
        </template>
      </div>

      <button class="insight-btn" @click="openAddNodeDialog" title="Add Custom Node" style="margin-left:8px;padding:2px 8px;font-size:11px;">+ Node</button>

      <div style="flex: 1"></div>
      <div class="tree-legend">
        <div class="legend-item"><div class="legend-box" style="background:#fee2e2; border-color:#fca5a5"></div>System</div>
        <div class="legend-item"><div class="legend-box" style="background:#dbeafe; border-color:#93c5fd"></div>Interact</div>
        <div class="legend-item"><div class="legend-box" style="background:#dcfce7; border-color:#86efac"></div>Zoom/Scroll</div>
        <div class="legend-item"><div class="legend-box" style="background:#f3e8ff; border-color:#d8b4fe"></div>Hover</div>
        <div class="legend-item"><div class="legend-box" style="background:#fde68a; border-color:#fcd34d"></div>Annotation</div>
        <div class="legend-item"><div class="legend-box" style="background:#edf2f7; border-color:#e2e8f0"></div>Other</div>
      </div>
    </div>
    <div class="tree-content" ref="svgContainer">
      <svg ref="svg"></svg>
    </div>
    <!-- Tooltip div moved outside tree-content to avoid overflow clipping -->
    <div ref="tooltip" class="tree-tooltip" style="opacity: 0; display: none;"></div>

    <!-- ezio: Popup for annotation details -->
    <div v-if="selectedAnnotation" class="annotation-popup-overlay" @click.self="closeAnnotationPopup">
      <div class="annotation-popup">
        <div class="popup-header">
          <h3>Annotation Details</h3>
          <button class="close-btn" @click="closeAnnotationPopup">×</button>
        </div>
        <div class="popup-body">
          <div class="popup-time">
            <span style="font-weight: bold; color: #718096; margin-right: 4px;">#{{ selectedAnnotation.id !== undefined ? selectedAnnotation.id : 'N/A' }}</span>
            {{ new Date(selectedAnnotation.timestamp || Date.now()).toLocaleString() }}
          </div>
          <div class="popup-text" v-if="selectedAnnotation.text">{{ selectedAnnotation.text }}</div>
          <div class="popup-empty-text" v-else>No text provided</div>
          
          <div v-if="selectedAnnotation.sketchDataUrl" class="popup-image-container">
            <img :src="selectedAnnotation.sketchDataUrl" class="popup-image" alt="Annotation Sketch" />
          </div>
        </div>
      </div>
    </div>

    <!-- ezio: Popup for High-level Insight Creation -->
    <div v-if="showInsightPopup" class="annotation-popup-overlay" @click.self="closeInsightPopup">
      <div class="annotation-popup insight-popup">
        <div class="popup-header">
          <h3>Create High-Level Insight</h3>
          <button class="close-btn" @click="closeInsightPopup">×</button>
        </div>
        <div class="popup-body">
          <div class="insight-annotations-list">
            <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #4a5568;">Selected Annotations ({{ selectedInsightAnnotations.length }})</h4>
            <InsightAnnotationItem 
              v-for="(anno, idx) in selectedInsightAnnotations" 
              :key="anno.id !== undefined ? anno.id : idx" 
              :item-id="anno.id" 
              :annotations="annotations" 
              :actions="actions" 
            />
          </div>
          <div class="insight-input-area">
            <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #4a5568;">Insight Notes</h4>
            <textarea v-model="insightText" placeholder="Enter high-level insights here..." class="insight-textarea"></textarea>
          </div>
        </div>
        <div class="popup-footer">
          <button class="insight-btn cancel-btn" @click="closeInsightPopup">Cancel</button>
          <button class="insight-btn confirm-btn" @click="saveInsight" :disabled="!insightText.trim()">Save Insight</button>
        </div>
      </div>
    </div>

    <!-- ezio: Popup for High-level Insight Viewing -->
    <div v-if="selectedInsightToView" class="annotation-popup-overlay" @click.self="closeInsightViewPopup">
      <div class="annotation-popup insight-popup">
        <div class="popup-header">
          <h3>High-Level Insight</h3>
          <button class="close-btn" @click="closeInsightViewPopup">×</button>
        </div>
        <div class="popup-body">
          <div class="popup-time">
            <span style="background: #3182ce; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; margin-right: 4px;">Insight</span>
            <span style="font-weight: bold; color: #718096; margin-right: 4px;">#{{ selectedInsightToView.id !== undefined ? selectedInsightToView.id : (selectedInsightToView.actionInfo?.id !== undefined ? selectedInsightToView.actionInfo.id : 'N/A') }}</span>
            {{ new Date(selectedInsightToView.timestamp).toLocaleString() }}
          </div>
          
          <div class="insight-input-area" style="margin-top: 0; margin-bottom: 16px;">
            <div class="popup-text" style="background: #eef2f7; border-left-color: #3182ce;">
              {{ selectedInsightToView.actionInfo ? selectedInsightToView.actionInfo.text : '' }}
            </div>
          </div>
          
          <div class="insight-annotations-list" v-if="selectedInsightToView.actionInfo && selectedInsightToView.actionInfo.refAnnotations && selectedInsightToView.actionInfo.refAnnotations.length > 0">
            <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #4a5568;">Referenced Annotations ({{ selectedInsightToView.actionInfo.refAnnotations.length }})</h4>
            <InsightAnnotationItem 
              v-for="refId in selectedInsightToView.actionInfo.refAnnotations" 
              :key="refId" 
              :item-id="refId" 
              :annotations="annotations" 
              :actions="actions" 
            />
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Context Menu -->
  <div v-if="contextMenu.visible" class="ctx-overlay" @click="hideContextMenu" @contextmenu.prevent="hideContextMenu"></div>
  <div v-if="contextMenu.visible" class="ctx-menu" :style="{left: contextMenu.x+'px', top: contextMenu.y+'px'}">
    <div v-if="contextMenu.node && contextMenu.node.data.type === 'annotation'" class="ctx-item" @click="openEditDialog">✏️ Edit</div>
    <div v-if="contextMenu.node && contextMenu.node.data.type !== 'root'" class="ctx-item" @click="insertAfterContextNode">➕ Insert After</div>
    <div v-if="contextMenu.node && contextMenu.node.data.type !== 'root'" class="ctx-item" @click="moveContextNode('up')">⬆️ Move Up</div>
    <div v-if="contextMenu.node && contextMenu.node.data.type !== 'root'" class="ctx-item" @click="moveContextNode('down')">⬇️ Move Down</div>
    <div class="ctx-item ctx-danger" @click="deleteContextNode">🗑️ Delete</div>
  </div>

  <!-- Edit Annotation Dialog -->
  <div v-if="editDialog.visible" class="annotation-popup-overlay" @click.self="closeEditDialog">
    <div class="annotation-popup">
      <div class="popup-header">
        <h3>Edit Annotation</h3>
        <button class="close-btn" @click="closeEditDialog">×</button>
      </div>
      <div class="popup-body">
        <div class="edit-field">
          <label class="edit-label">Text</label>
          <textarea v-model="editDialog.text" class="insight-textarea" rows="4" placeholder="Annotation text..."></textarea>
        </div>
        <div class="edit-field">
          <label class="edit-label">Node Color</label>
          <div class="color-row">
            <div v-for="c in colorPresets" :key="c.value" class="color-dot"
              :style="{background: c.value, outline: editDialog.color === c.value ? '2px solid #2d3748' : 'none'}"
              :title="c.label" @click="editDialog.color = c.value"></div>
            <input type="color" v-model="editDialog.color" title="Custom color" style="width:28px;height:28px;border:none;cursor:pointer;border-radius:4px;" />
          </div>
        </div>
        <div class="edit-field">
          <label class="edit-label">Screenshot</label>
          <input type="file" accept="image/*" @change="editDialog_onImageChange" />
          <div v-if="editDialog.imageUrl" class="popup-image-container" style="margin-top:8px;">
            <img :src="editDialog.imageUrl" class="popup-image" alt="Preview" />
            <button class="insight-btn cancel-btn" style="margin-top:6px;font-size:11px;" @click="editDialog.imageUrl = null">Remove Image</button>
          </div>
        </div>
      </div>
      <div class="popup-footer">
        <button class="insight-btn cancel-btn" @click="closeEditDialog">Cancel</button>
        <button class="insight-btn confirm-btn" @click="saveEdit">Save</button>
      </div>
    </div>
  </div>

  <!-- Add Custom Node Dialog -->
  <div v-if="addNodeDialog.visible" class="annotation-popup-overlay" @click.self="closeAddNodeDialog">
    <div class="annotation-popup">
      <div class="popup-header">
        <h3>Add Custom Node</h3>
        <button class="close-btn" @click="closeAddNodeDialog">×</button>
      </div>
      <div class="popup-body">
        <div class="edit-field">
          <label class="edit-label">Text / Label</label>
          <textarea v-model="addNodeDialog.text" class="insight-textarea" rows="3" placeholder="Enter annotation text..."></textarea>
        </div>
        <div class="edit-field">
          <label class="edit-label">Source View</label>
          <select v-model="addNodeDialog.sourceView" class="edit-select">
            <option value="token_distribution">Token Distribution (TD)</option>
            <option value="kline_chart">K-Line Chart (KL)</option>
            <option value="behavior_details">Behavior Details (BD)</option>
            <option value="system">System</option>
          </select>
        </div>
        <div class="edit-field">
          <label class="edit-label">Node Color</label>
          <div class="color-row">
            <div v-for="c in colorPresets" :key="c.value" class="color-dot"
              :style="{background: c.value, outline: addNodeDialog.color === c.value ? '2px solid #2d3748' : 'none'}"
              :title="c.label" @click="addNodeDialog.color = c.value"></div>
            <input type="color" v-model="addNodeDialog.color" title="Custom color" style="width:28px;height:28px;border:none;cursor:pointer;border-radius:4px;" />
          </div>
        </div>
        <div class="edit-field">
          <label class="edit-label">Image (optional)</label>
          <input type="file" accept="image/*" @change="addNode_onImageChange" />
          <div v-if="addNodeDialog.imageUrl" class="popup-image-container" style="margin-top:8px;">
            <img :src="addNodeDialog.imageUrl" class="popup-image" alt="Preview" />
            <button class="insight-btn cancel-btn" style="margin-top:6px;font-size:11px;" @click="addNodeDialog.imageUrl = null">Remove Image</button>
          </div>
        </div>
      </div>
      <div class="popup-footer">
        <button class="insight-btn cancel-btn" @click="closeAddNodeDialog">Cancel</button>
        <button class="insight-btn confirm-btn" @click="saveNewNode" :disabled="!addNodeDialog.text.trim()">Add</button>
      </div>
    </div>
  </div>

</template>

<script>
import * as d3 from 'd3'
import InsightAnnotationItem from './InsightAnnotationItem.vue'

export default {
  name: 'UserActionTree',
  components: {
    InsightAnnotationItem
  },
  emits: ['add-insight-annotation', 'log-action', 'delete-action', 'delete-annotation', 'update-annotation', 'add-custom-annotation', 'reorder-action'],
  props: {
    actions: {
      type: Array,
      default: () => []
    },
    annotations: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      nodesCount: 0,
      selectedAnnotation: null,
      selectedInsightToView: null,
      // ezio: high-level insight state
      isMultiSelectMode: false,
      selectedInsightAnnotations: [],
      showInsightPopup: false,
      insightText: '',
      // ezio: node editing state
      contextMenu: { visible: false, x: 0, y: 0, node: null },
      editDialog: { visible: false, annotationId: null, text: '', color: '#fde68a', imageUrl: null },
      addNodeDialog: { visible: false, text: '', sourceView: 'token_distribution', color: '#fde68a', imageUrl: null, afterTimestamp: null },
      colorPresets: [
        { value: '#fde68a', label: 'Yellow' },
        { value: '#fee2e2', label: 'Red' },
        { value: '#dbeafe', label: 'Blue' },
        { value: '#dcfce7', label: 'Green' },
        { value: '#f3e8ff', label: 'Purple' },
        { value: '#fbcfe8', label: 'Pink' },
        { value: '#fed7aa', label: 'Orange' },
        { value: '#b2f5ea', label: 'Teal' },
      ],
    }
  },
  watch: {
    actions: {
      handler() {
        this.drawTree()
      },
      deep: true
    },
    annotations: {
      handler() {
        this.drawTree()
      },
      deep: true
    }
  },
  mounted() {
    this.resizeObserver = new ResizeObserver(() => {
      if (this.$refs.container && this.$refs.container.clientWidth > 0) {
        this.drawTree()
      }
    })
    this.resizeObserver.observe(this.$refs.container)
    this.drawTree()
  },
  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
    }
  },
  methods: {
    closeAnnotationPopup() {
      this.selectedAnnotation = null
    },
    // ezio: high level insight methods
    startMultiSelect() {
      this.isMultiSelectMode = true
      this.selectedInsightAnnotations = []
      this.drawTree()
    },
    cancelMultiSelect() {
      this.isMultiSelectMode = false
      this.selectedInsightAnnotations = []
      this.drawTree()
    },
    openInsightPopup() {
      if (this.selectedInsightAnnotations.length > 0) {
        this.showInsightPopup = true
        this.insightText = ''
      }
    },
    closeInsightPopup() {
      this.showInsightPopup = false
    },
    closeInsightViewPopup() {
      this.selectedInsightToView = null
    },
    saveInsight() {
      if (!this.insightText.trim()) return
      
      const payload = {
        refAnnotations: this.selectedInsightAnnotations.map(a => a.id),
        text: this.insightText
      }
      
      this.$emit('log-action', 'high_level_insight', payload)
      
      // Also emit to add to annotation records
      this.$emit('add-insight-annotation', {
        text: this.insightText,
        sourceView: 'system',
        selectedItems: payload.refAnnotations
      })
      
      this.showInsightPopup = false
      this.cancelMultiSelect()
    },

    // ezio: context menu helpers
    hideContextMenu() {
      this.contextMenu.visible = false
    },
    deleteContextNode() {
      const node = this.contextMenu.node
      this.hideContextMenu()
      if (!node) return
      const d = node.data
      if (d.type === 'annotation' && d.data) {
        const id = d.data.isAnnotation ? d.data.id : (d.data.actionInfo ? d.data.actionInfo.id : null)
        if (id !== null && id !== undefined) {
          this.$emit('delete-annotation', id)
        } else {
          // It's an action node — emit index to delete from userActionSequence
          const ts = d.data.timestamp
          this.$emit('delete-action', ts)
        }
      } else if (d.data) {
        this.$emit('delete-action', d.data.timestamp)
      }
    },
    openEditDialog() {
      const node = this.contextMenu.node
      this.hideContextMenu()
      if (!node) return
      const d = node.data
      if (d.type === 'annotation' && d.data) {
        const ann = d.data.isAnnotation ? d.data : d.data.actionInfo
        if (!ann) return
        this.editDialog = {
          visible: true,
          annotationId: ann.id,
          text: ann.text || '',
          color: ann.customColor || '#fde68a',
          imageUrl: ann.sketchDataUrl || null
        }
      }
    },
    closeEditDialog() {
      this.editDialog.visible = false
    },
    editDialog_onImageChange(e) {
      const file = e.target.files && e.target.files[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = ev => { this.editDialog.imageUrl = ev.target.result }
      reader.readAsDataURL(file)
    },
    saveEdit() {
      this.$emit('update-annotation', {
        id: this.editDialog.annotationId,
        text: this.editDialog.text,
        customColor: this.editDialog.color,
        sketchDataUrl: this.editDialog.imageUrl
      })
      this.closeEditDialog()
    },

    // ezio: add custom annotation node
    openAddNodeDialog() {
      this.addNodeDialog = { visible: true, text: '', sourceView: 'token_distribution', color: '#fde68a', imageUrl: null, afterTimestamp: null }
    },
    insertAfterContextNode() {
      const node = this.contextMenu.node
      this.hideContextMenu()
      if (!node || !node.data.data) return
      const ts = node.data.data.timestamp
      this.addNodeDialog = { visible: true, text: '', sourceView: 'token_distribution', color: '#fde68a', imageUrl: null, afterTimestamp: ts }
    },
    moveContextNode(direction) {
      const node = this.contextMenu.node
      this.hideContextMenu()
      if (!node || !node.data.data) return
      const ts = node.data.data.timestamp
      this.$emit('reorder-action', { timestamp: ts, direction })
    },
    closeAddNodeDialog() {
      this.addNodeDialog.visible = false
    },
    addNode_onImageChange(e) {
      const file = e.target.files && e.target.files[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = ev => { this.addNodeDialog.imageUrl = ev.target.result }
      reader.readAsDataURL(file)
    },
    saveNewNode() {
      if (!this.addNodeDialog.text.trim()) return
      this.$emit('add-custom-annotation', {
        text: this.addNodeDialog.text,
        sourceView: this.addNodeDialog.sourceView,
        customColor: this.addNodeDialog.color,
        sketchDataUrl: this.addNodeDialog.imageUrl || null,
        afterTimestamp: this.addNodeDialog.afterTimestamp || null
      })
      this.closeAddNodeDialog()
    },
    getAnnotationById(id) {
      return this.annotations.find(a => a.id === id);
    },
    getActionByAnnotationId(id) {
      return this.actions.find(a => a.actionType === 'annotation' && a.actionInfo && a.actionInfo.id === id);
    },
    buildTreeData() {
      // Merge actions and annotations, sort by time
      // Filter out high_level_insight from actions to avoid duplicates with annotationRecords
      let allEvents = this.actions.filter(a => a.actionType !== 'high_level_insight')
      
      this.annotations.forEach(anno => {
        allEvents.push({
          ...anno,
          actionType: anno.isInsight ? 'high_level_insight' : 'annotation',
          customColor: anno.customColor || null,
          actionInfo: { 
            id: anno.id, 
            text: anno.text, 
            refAnnotations: anno.isInsight ? anno.selectedItems : undefined,
            selectedItems: anno.selectedItems, 
            sketchDataUrl: anno.sketchDataUrl, 
            timestamp: anno.timestamp 
          },
          isAnnotation: true,
          targetView: anno.sourceView
        })
      })
      
      allEvents.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

      // Root node
      const root = {
        id: 'root',
        name: 'Start Session',
        type: 'root',
        children: [],
        parent: null
      }
      
      this.nodesCount = 0

      // Global context actions that start a new branch from root
      const rootLevelActions = [
        'change_coin', 
        'run_entity_detection', 
        'update_link_detection', 
        'run_manipulation_detection'
      ]

      let currentParent = root;
      // ezio: track the last 'change_coin' node so update_snapshot can be attached under it
      let lastCoinNode = root;

      allEvents.forEach((event, i) => {
        this.nodesCount++
        const isRootConfig = rootLevelActions.includes(event.actionType)
        const isUpdateSnapshot = event.actionType === 'update_snapshot'
        const isHighLevelInsight = event.actionType === 'high_level_insight'
        
        const newNode = {
          id: `node_${i}`,
          name: this.formatActionType(event.actionType),
          type: (event.actionType === 'annotation' || isHighLevelInsight) ? 'annotation' : 'action',
          data: event,
          children: [],
          parent: null // will be set below
        }
        
        if (isRootConfig) {
          newNode.parent = root
          root.children.push(newNode)
          currentParent = newNode
          if (event.actionType === 'change_coin') {
             lastCoinNode = newNode;
          }
        } else if (isUpdateSnapshot) {
          // Attach update_snapshot to the last change_coin branch (or root if none exists)
          newNode.parent = lastCoinNode
          lastCoinNode.children.push(newNode)
          currentParent = newNode
        } else {
          newNode.parent = currentParent
          currentParent.children.push(newNode)
          currentParent = newNode
        }
      })
      
      return root
    },
    formatActionType(type) {
      if (!type) return 'Unknown'
      return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    },
    formatActionSummary(type, info) {
      if (!info) return ''
      
      const isMergedArray = Array.isArray(info)
      const count = isMergedArray ? info.length : 1
      const countStr = count > 1 ? ` (${count} continuous events)` : ''
      const summaryInfo = isMergedArray ? info[info.length - 1].data : info
      
      try {
        if (type === 'zoom_kline_chart' || type === 'zoom_behavior_chart') {
          return `Adjusted view time window${countStr}`
        }
        if (type === 'scroll_manipulation_cards') {
          const cardsCount = summaryInfo.visibleCards ? summaryInfo.visibleCards.length : 0
          return `Scrolled ${summaryInfo.type === 'round_trip' ? 'Top' : 'Bottom'} Manipulation Cards (Viewing ${cardsCount} cards)${countStr}`
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
        if (type === 'toggle_show_links') {
          return `${summaryInfo.enabled ? 'Enabled' : 'Disabled'} "Show Links"`
        }
        if (type === 'scale_change') {
          return `Changed Scale to ${summaryInfo.scaleFactor}`
        }
        if (type === 'sync_time_window') {
          return `Synchronized time window from ${summaryInfo.source === 'kline_chart' ? 'K-line Chart' : 'Behavior Details'}`
        }
        
        if (type === 'high_level_insight') {
          return `Insight: ${summaryInfo.text || 'No text provided'}`
        }
        
        // Fallback
        const str = JSON.stringify(summaryInfo)
        return str.length > 40 ? str.substring(0, 40) + '...' : str
      } catch (e) {
        return `Details available${countStr}`
      }
    },
    drawTree() {
      const container = this.$refs.svgContainer
      if (!container) return
      
      const width = container.clientWidth
      const height = container.clientHeight || 400
      
      const svg = d3.select(this.$refs.svg)
      svg.selectAll('*').remove()
      svg.attr('width', width).attr('height', height)
      
      const treeData = this.buildTreeData()
      if (!treeData.children || treeData.children.length === 0) {
        svg.append('text')
           .attr('x', width/2)
           .attr('y', height/2)
           .attr('text-anchor', 'middle')
           .attr('fill', '#a0aec0')
           .text('No actions to display yet')
        return
      }

      const root = d3.hierarchy(treeData)
      
      // Compute tree layout. We use a tidy tree layout.
      // dx is the vertical distance between branches, dy is the horizontal
      const dx = 75 // Exactly enough for 3 lanes (+/- 25) plus a standard 25px gap to match the inter-lane spacing
      const baseDy = 35 // Reduced horizontal distance to make tree more compact
      const tree = d3.tree().nodeSize([dx, baseDy])
      tree(root)

      // Post-process the tree to compact consecutive nodes of the same type on the same branch
      // and adjust their vertical (x) positions based on their sourceView
      
      // Reduced the vertical offsets to compress the 3 views into a tighter group
      const viewLanes = {
        'token_distribution': -25,
        'kline_chart': 0,
        'behavior_details': 25,
        'system': 0,
        'control_panel': 0,
        'header_panel': 0
      };

      root.eachBefore(d => {
        // Adjust horizontal (y) spacing for compacting
        if (d.parent) {
          const isContinuousSameType = 
            d.parent.children.length === 1 && 
            d.data.data && d.parent.data.data && 
            d.data.data.actionType === d.parent.data.data.actionType &&
            d.data.type !== 'root' && d.parent.data.type !== 'root';
            
          if (isContinuousSameType) {
            d.customY = d.parent.customY + 14;
          } else {
            d.customY = d.parent.customY + baseDy;
          }
        } else {
          d.customY = 0;
        }
        
        // Adjust vertical (x) spacing based on source view
        if (d.data.type !== 'root' && d.data.data && d.data.data.sourceView) {
           const sv = d.data.data.sourceView;
           // Offset the node vertically based on the view it belongs to
           d.customX = (d.parent && d.parent.data.type === 'root' ? d.x : (d.parent ? d.parent.customX : d.x)) + (viewLanes[sv] !== undefined ? viewLanes[sv] : 0);
           // Actually, since we want them to form absolute lanes relative to their system root parent:
           
           // Find the closest system root ancestor
           let systemAncestor = d;
           while(systemAncestor.parent && systemAncestor.parent.data.type !== 'root') {
             systemAncestor = systemAncestor.parent;
           }
           
           // The base X is the X coordinate of the system action that started this branch
           const baseX = systemAncestor.x;
           
           // Apply lane offset
           const laneOffset = viewLanes[sv] !== undefined ? viewLanes[sv] : 0;
           d.customX = baseX + laneOffset;
        } else {
           d.customX = d.x;
        }
      })

      // Replace the default D3 computed coordinates
      root.each(d => {
        d.y = d.customY;
        d.x = d.customX;
      })

      // Center the tree in the SVG initially based on vertical (x) bounds
      let x0 = Infinity
      let x1 = -x0
      let maxY = 0
      root.each(d => {
        if (d.x > x1) x1 = d.x
        if (d.x < x0) x0 = d.x
        if (d.y > maxY) maxY = d.y
      })

      // Add a slight padding so root isn't right against the left edge
      const g = svg.append('g')
        .attr('transform', `translate(20,${height/2 - (x0 + x1)/2})`)

      // Add zoom capabilities
      const zoom = d3.zoom()
        .scaleExtent([0.1, 3])
        .on('zoom', (event) => {
          g.attr('transform', event.transform)
        })
      svg.call(zoom)
      // ezio: Disable double-click to zoom on the entire SVG canvas
      svg.on('dblclick.zoom', null)

      // Draw background swimlane segments behind everything
      const bgGroup = g.append('g').attr('class', 'swimlane-backgrounds')
      
      // We traverse the tree and identify consecutive segments of nodes in the same lane
      const laneSegments = []
      
      // Colors for the rounded segments (all the same light gray)
      const bandColors = {
        'token_distribution': '#f8fafc',
        'kline_chart': '#f8fafc',
        'behavior_details': '#f8fafc'
      }

      // To ensure we break the capsule if the user switches to a different view and then comes back,
      // we need to process nodes chronologically and track the last active view lane for the current system branch.
      
      // We sort the descendants chronologically based on their ID/order to guarantee we trace the user's path correctly
      const sortedNodes = root.descendants().sort((a, b) => {
        // Root is always first
        if (a.data.type === 'root') return -1;
        if (b.data.type === 'root') return 1;
        // Extract the index from id (e.g. "node_5")
        const aId = parseInt(a.data.id.split('_')[1]);
        const bId = parseInt(b.data.id.split('_')[1]);
        return aId - bId;
      });

      let currentActiveSegment = null;
      // Track which view lanes have already been labeled for each system branch (using system branch y-coord as key)
      const labeledLanes = {};

      sortedNodes.forEach(d => {
        // Only process nodes that actually belong to a specific view lane
        if (d.data.type !== 'root') {
          const sv = d.data.data.sourceView || 'system'
          
          // Find the closest system root ancestor to use its x (vertical pos) as a unique identifier for the current system branch
          let systemAncestor = d;
          while(systemAncestor.parent && systemAncestor.parent.data.type !== 'root') {
            systemAncestor = systemAncestor.parent;
          }
          const branchId = systemAncestor.x;
          
          // Initialize tracking for this system branch if it doesn't exist
          if (!labeledLanes[branchId]) {
            labeledLanes[branchId] = new Set();
          }
          
          // Determine if this is the very first time we see this view lane in this system branch
          let isFirstInBranch = false;
          if (sv !== 'system' && sv !== 'control_panel' && sv !== 'header_panel') {
            if (!labeledLanes[branchId].has(sv)) {
              isFirstInBranch = true;
              labeledLanes[branchId].add(sv);
            }
          }

          // System actions, control panel actions, and global configs do NOT get a capsule
          // They also break any active capsule
          if (sv === 'system' || sv === 'control_panel' || sv === 'header_panel') {
            currentActiveSegment = null;
            return;
          }
          
          // Ensure that actionType 'click_kline_align_cards' specifically acts as a valid node for grouping
          // by not doing anything special to exclude it. It has sourceView 'kline_chart'.
          
          // Check if we can append to the currently active segment
          // It must be the exact same lane (same yCenter) AND the user hasn't switched to another view in between
          if (currentActiveSegment && currentActiveSegment.view === sv && Math.abs(currentActiveSegment.yCenter - d.x) < 5) {
             currentActiveSegment.nodes.push(d)
             currentActiveSegment.minX = Math.min(currentActiveSegment.minX, d.y)
             currentActiveSegment.maxX = Math.max(currentActiveSegment.maxX, d.y)
             // We don't overwrite isFirstInBranch for appended nodes, it only applies to the segment start
          } else {
             // Either there is no active segment, OR the user switched to a different view/branch
             // So we MUST start a brand new capsule
             currentActiveSegment = {
               view: sv,
               yCenter: d.x,
               minX: d.y,
               maxX: d.y,
               nodes: [d],
               isFirstInBranch: isFirstInBranch, // tag the segment if it's the very first of its kind
               branchId: branchId // track the branch to connect later
             }
             laneSegments.push(currentActiveSegment)
          }
        } else {
          // Root nodes also break any active capsule
          currentActiveSegment = null;
        }
      })

      // Calculate bounds for each view lane within each system branch to draw connecting dashed lines
      const laneBounds = {};
      laneSegments.forEach(seg => {
        if (seg.branchId === undefined) return;
        const key = `${seg.branchId}_${seg.view}`;
        if (!laneBounds[key]) {
          laneBounds[key] = {
            yCenter: seg.yCenter,
            minX: seg.minX,
            maxX: seg.maxX
          };
        } else {
          laneBounds[key].minX = Math.min(laneBounds[key].minX, seg.minX);
          laneBounds[key].maxX = Math.max(laneBounds[key].maxX, seg.maxX);
        }
      });

      // Draw dashed connecting lines underneath the capsules
      Object.values(laneBounds).forEach(bound => {
        if (bound.minX < bound.maxX) {
          bgGroup.append('line')
            .attr('x1', bound.minX)
            .attr('y1', bound.yCenter)
            .attr('x2', bound.maxX)
            .attr('y2', bound.yCenter)
            .attr('stroke', '#e2e8f0') // Very subtle light gray (slate-200)
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '4,4') // Dashed pattern
        }
      });

      // Draw the computed segments as rounded rectangles
      laneSegments.forEach(seg => {
        if (seg.nodes.length === 0) return
        
        // Pad the bounding box a bit so it wraps the 16x16 node rects nicely
        const paddingX = 14
        const paddingY = 14
        // The segment bounding box width is simply the span of the node centers
        // plus padding on both left and right sides.
        const width = (seg.maxX - seg.minX) + paddingX * 2
        
        bgGroup.append('rect')
          .attr('x', seg.minX - paddingX)
          .attr('y', seg.yCenter - paddingY)
          .attr('width', width)
          .attr('height', paddingY * 2)
          .attr('rx', paddingY) // Fully rounded capsule shape
          .attr('fill', bandColors[seg.view] || '#f8fafc')
          .attr('stroke', 'none')
          
        // If this is the first capsule for this view in the current system branch, draw a label before it
        if (seg.isFirstInBranch) {
          let labelText = '';
          if (seg.view === 'token_distribution') labelText = 'TD';
          else if (seg.view === 'kline_chart') labelText = 'KL';
          else if (seg.view === 'behavior_details') labelText = 'BD';
          
          if (labelText) {
            bgGroup.append('text')
              .attr('x', seg.minX - paddingX - 6) // Slightly to the left of the capsule
              .attr('y', seg.yCenter) // Center vertically with the lane
              .attr('dy', '0.32em') // Vertical alignment adjustment
              .attr('text-anchor', 'end') // Right-align text so it flows leftward away from the capsule
              .attr('font-size', '10px')
              .attr('font-weight', '600')
              .attr('fill', '#94a3b8') // slate-400 color for a subtle look
              .text(labelText)
          }
        }
      })

      // Links
      g.append('g')
        .attr('fill', 'none')
        .attr('stroke', '#cbd5e1')
        .attr('stroke-width', 1.5)
        .selectAll('path')
        .data(root.links())
        .join('path')
        .attr('d', d3.linkHorizontal()
            .x(d => d.y)
            .y(d => d.x))
      const getActionClass = (type) => {
        if (!type) return 'default'
        if (type.includes('zoom') || type.includes('scroll') || type.includes('scale')) return 'zoom'
        if (type.startsWith('hover_')) return 'hover'
        if (type.includes('select') || type.includes('click') || type.includes('toggle')) return 'interaction'
        if (type.includes('run') || type.includes('update') || type === 'change_coin') return 'system'
        if (type === 'high_level_insight') return 'annotation'
        return 'default'
      }

      // Colors mapping based on UserActionTimeline classes
      const typeColors = {
        interaction: { bg: '#dbeafe', text: '#2b6cb0', border: '#93c5fd' },
        zoom: { bg: '#dcfce7', text: '#2c7a7b', border: '#86efac' },
        hover: { bg: '#f3e8ff', text: '#2f855a', border: '#d8b4fe' },
        system: { bg: '#fee2e2', text: '#c53030', border: '#fca5a5' },
        default: { bg: '#edf2f7', text: '#4a5568', border: '#e2e8f0' },
        annotation: { bg: '#fde68a', text: '#92400e', border: '#fcd34d' }, // Amber from AnnotationTimeline
        view_branch: { bg: '#f8fafc', text: '#4a5568', border: '#cbd5e1' } // Special color for structural view nodes
      }

      // Links
      g.append('g')
        .attr('fill', 'none')
        .attr('stroke', '#cbd5e1')
        .attr('stroke-width', 1.5)
        .selectAll('path')
        .data(root.links())
        .join('path')
        .attr('d', d3.linkHorizontal()
            .x(d => d.y)
            .y(d => d.x))
        .attr('stroke-dasharray', d => d.target.data.type === 'view_branch' ? '4,4' : 'none') // Dashed lines for view branches

      // Nodes
      const node = g.append('g')
        .selectAll('g')
        .data(root.descendants())
        .join('g')
        .attr('transform', d => `translate(${d.y},${d.x})`)

      const getStrokeColor = d => {
        if (this.isMultiSelectMode && d.data.type === 'annotation' && d.data.data && d.data.data.actionInfo) {
          const isSelected = this.selectedInsightAnnotations.some(a => a.id === d.data.data.actionInfo.id);
          if (isSelected) return '#e53e3e';
        }
        if (d.data.type === 'root') return '#2d3748'
        if (d.data.type === 'annotation') return typeColors.annotation.border
        if (d.data.type === 'view_branch') return typeColors.view_branch.border
        const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
        return typeColors[cat] ? typeColors[cat].border : typeColors.default.border
      };

      const getStrokeWidth = d => {
        if (this.isMultiSelectMode && d.data.type === 'annotation' && d.data.data && d.data.data.actionInfo) {
          const isSelected = this.selectedInsightAnnotations.some(a => a.id === d.data.data.actionInfo.id);
          if (isSelected) return 3;
        }
        return 1.5;
      };

      // Node Rectangles based on type
      node.append('rect')
        .attr('class', 'node-rect')
        .attr('x', -8)
        .attr('y', d => (d.data.data && d.data.data.actionType === 'high_level_insight') ? -33 : -8)
        .attr('width', 16)
        .attr('height', d => (d.data.data && d.data.data.actionType === 'high_level_insight') ? 66 : 16)
        .attr('rx', 4) // Rounded corners
        .attr('fill', d => {
          if (d.data.type === 'root') return '#4a5568'
          if (d.data.data && d.data.data.customColor) return d.data.data.customColor
          if (d.data.type === 'annotation') return typeColors.annotation.bg
          if (d.data.type === 'view_branch') return typeColors.view_branch.bg
          const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
          return typeColors[cat] ? typeColors[cat].bg : typeColors.default.bg
        })
        .attr('stroke', getStrokeColor)
        .attr('stroke-width', getStrokeWidth)
        .style('cursor', 'pointer')

      // Add a small icon/initial to view branches so they are recognizable
      node.filter(d => d.data.type === 'view_branch')
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.3em')
        .attr('font-size', '8px')
        .attr('font-weight', 'bold')
        .attr('fill', '#4a5568')
        .style('pointer-events', 'none')
        .text(d => {
          if (d.data.data.viewKey === 'token_distribution') return 'TD'
          if (d.data.data.viewKey === 'kline_chart') return 'KL'
          if (d.data.data.viewKey === 'behavior_details') return 'BD'
          return 'V'
        })
        
      const tooltipDiv = d3.select(this.$refs.tooltip)

      let clickTimeout = null;

      // Hover interactions
      node
        .on('contextmenu', (event, d) => {
          event.preventDefault()
          event.stopPropagation()
          if (d.data.type === 'root') return
          this.contextMenu = { visible: true, x: event.clientX, y: event.clientY, node: d }
        })
        .on('mouseover', (event, d) => {
          const typeLabel = d.data.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
          let content = `<strong>${d.data.name}</strong><br/>
                         <span style="color:#718096;font-size:10px;">Type: ${typeLabel}</span>`
                         
          if (d.data.data && d.data.data.timestamp) {
             const timeStr = new Date(d.data.data.timestamp).toLocaleTimeString()
             content += `<br/><span style="color:#a0aec0;font-size:10px;">${timeStr}</span>`
          }

          if (d.data.data && d.data.data.actionInfo) {
             const actionType = d.data.data.actionType
             const info = d.data.data.actionInfo
             let summary = ''
             
             // Annotations have their own text payload, actions use the formatter
             if (actionType === 'annotation' || actionType === 'high_level_insight') {
                summary = info.text || 'No description provided'
             } else {
                summary = this.formatActionSummary(actionType, info)
             }
             
             content += `<br/><div style="margin-top:4px;font-size:10px;color:#2d3748;max-width:200px;word-wrap:break-word;">${summary}</div>`
          }
          
          if (d.data.type === 'sequential_group') {
             content += `<br/><div style="margin-top:4px;font-size:10px;color:#2d3748;">Contains ${d.data.events.length} actions</div>`
          }

          tooltipDiv.transition().duration(200).style('opacity', 1)
          tooltipDiv.style('display', 'block')
          tooltipDiv.html(content)
            .style('left', (event.clientX + 15) + 'px')
            .style('top', (event.clientY - 30) + 'px')

          if (d.data.data && d.data.data.actionType === 'high_level_insight') {
             const refIds = d.data.data.actionInfo.refAnnotations || [];
             
             // Recursively get all nested refIds
             const getAllRefIds = (ids) => {
                let all = [...ids];
                ids.forEach(id => {
                   const anno = this.annotations.find(a => a.id === id);
                   if (anno && anno.isInsight && anno.selectedItems) {
                      all = all.concat(getAllRefIds(anno.selectedItems));
                   }
                });
                return all;
             };
             const allRefIds = getAllRefIds(refIds);

             // Highlight all nested references
             g.selectAll('.node-rect')
               .attr('stroke', d_node => {
                  const nodeActionId = d_node.data.data && d_node.data.data.actionInfo ? d_node.data.data.actionInfo.id : null;
                  const nodeId = d_node.data.data ? d_node.data.data.id : null;
                  
                  if ((nodeActionId !== null && allRefIds.includes(nodeActionId)) || 
                      (nodeId !== null && allRefIds.includes(nodeId))) {
                     return '#e53e3e';
                  }
                  if (d_node === d) return '#4a5568';
                  return getStrokeColor(d_node);
               })
               .attr('stroke-width', d_node => {
                  const nodeActionId = d_node.data.data && d_node.data.data.actionInfo ? d_node.data.data.actionInfo.id : null;
                  const nodeId = d_node.data.data ? d_node.data.data.id : null;
                  
                  if ((nodeActionId !== null && allRefIds.includes(nodeActionId)) || 
                      (nodeId !== null && allRefIds.includes(nodeId))) {
                     return 3;
                  }
                  if (d_node === d) return 2;
                  return getStrokeWidth(d_node);
               });
          } else {
             d3.select(event.currentTarget).select('.node-rect').attr('stroke', '#4a5568').attr('stroke-width', 2)
          }
        })
        .on('mousemove', (event) => {
          tooltipDiv.style('left', (event.clientX + 15) + 'px')
            .style('top', (event.clientY - 30) + 'px')
        })
        .on('mouseout', (event, d) => {
          tooltipDiv.transition().duration(200).style('opacity', 0)
            .on('end', () => tooltipDiv.style('display', 'none'))
          
          g.selectAll('.node-rect')
            .attr('stroke', getStrokeColor)
            .attr('stroke-width', getStrokeWidth);
        })
        .on('dblclick', (event, d) => {
          // ezio: prevent dblclick from propagating to zoom
          event.stopPropagation();
        })
        .on('click', (event, d) => {
         // ezio: branch on active tool
         if (this.isMultiSelectMode) {
            if (clickTimeout) {
              clearTimeout(clickTimeout);
              clickTimeout = null;
              // Double click logic
              if (d.data.type === 'annotation' && d.data.data) {
                 if (d.data.data.actionType === 'high_level_insight') {
                   // Allow selecting high_level_insight in multi-select mode
                   const id = d.data.data.actionInfo.id;
                   const idx = this.selectedInsightAnnotations.findIndex(a => a.id === id);
                   if (idx === -1) {
                     this.selectedInsightAnnotations.push(d.data.data.actionInfo);
                   } else {
                     this.selectedInsightAnnotations.splice(idx, 1);
                   }
                   this.drawTree();
                 } else if (d.data.data.actionInfo) {
                   const id = d.data.data.actionInfo.id;
                   const idx = this.selectedInsightAnnotations.findIndex(a => a.id === id);
                   if (idx === -1) {
                     this.selectedInsightAnnotations.push(d.data.data.actionInfo);
                   } else {
                     this.selectedInsightAnnotations.splice(idx, 1);
                   }
                   // re-render tree styles
                   this.drawTree();
                 }
              }
            } else {
              // Single click logic (deferred)
              clickTimeout = setTimeout(() => {
                clickTimeout = null;
                // If this is an insight node, show the insight details instead of normal annotation
                if (d.data.type === 'annotation' && d.data.data) {
                  if (d.data.data.actionType === 'high_level_insight') {
                    this.selectedInsightToView = d.data.data;
                  } else {
                    this.selectedAnnotation = d.data.data.actionInfo || d.data.data;
                  }
                }
              }, 250);
            }
         } else {
            // Normal mode: Single click is immediate
            if (d.data.type === 'annotation' && d.data.data) {
              if (d.data.data.actionType === 'high_level_insight') {
                this.selectedInsightToView = d.data.data;
              } else {
                this.selectedAnnotation = d.data.data.actionInfo || d.data.data;
              }
            }
         }
        })
    }
  }
}
</script>

<style scoped>
.user-action-tree-container {
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

.tree-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-right: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #718096;
}

.legend-box {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1px solid;
}

.tree-content {
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.tree-tooltip {
  position: fixed;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  color: #1a202c;
  pointer-events: none;
  z-index: 9999;
  max-width: 250px;
  word-wrap: break-word;
}

/* ezio: insight button styles */
.insight-btn {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #4a5568;
  cursor: pointer;
  transition: all 0.2s;
}
.insight-btn:hover:not(:disabled) {
  background: #edf2f7;
}
.insight-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.insight-btn.cancel-btn {
  color: #e53e3e;
  border-color: #feb2b2;
  background: #fff5f5;
}
.insight-btn.cancel-btn:hover {
  background: #fed7d7;
}
.insight-btn.confirm-btn {
  color: #3182ce;
  border-color: #bee3f8;
  background: #ebf8ff;
}
.insight-btn.confirm-btn:hover:not(:disabled) {
  background: #bee3f8;
}

.insight-popup {
  max-width: 800px;
}
.insight-annotations-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px;
  background: #f8fafc;
}
.insight-anno-item {
  padding: 8px;
  border-bottom: 1px solid #e2e8f0;
}
.insight-anno-item:last-child {
  border-bottom: none;
}
.anno-time {
  font-size: 11px;
  color: #718096;
  margin-bottom: 4px;
}
.anno-text {
  font-size: 13px;
  color: #2d3748;
}
.insight-input-area {
  margin-top: 16px;
}
.insight-textarea {
  width: 100%;
  height: 100px;
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
.insight-textarea:focus {
  border-color: #4a5568;
}
.popup-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 0 0 8px 8px;
}

/* ezio: annotation popup styles */
.annotation-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  z-index: 2000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.annotation-popup {
  background: #fff;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 8px 8px 0 0;
}

.popup-header h3 {
  margin: 0;
  font-size: 16px;
  color: #2d3748;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  line-height: 1;
  color: #a0aec0;
  cursor: pointer;
  padding: 0;
}

.close-btn:hover {
  color: #4a5568;
}

.popup-body {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.popup-time {
  font-size: 12px;
  color: #718096;
}

.popup-text {
  font-size: 14px;
  color: #2d3748;
  line-height: 1.5;
  background: #f1f5f9;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #fcd34d;
}

.popup-empty-text {
  font-size: 14px;
  color: #a0aec0;
  font-style: italic;
}

.popup-image-container {
  margin-top: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  background: #f8fafc;
}

.popup-image {
  width: 100%;
  height: auto;
  display: block;
}

/* ezio: context menu */
.ctx-overlay {
  position: fixed; inset: 0; z-index: 3000;
}
.ctx-menu {
  position: fixed;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 3001;
  min-width: 140px;
  overflow: hidden;
}
.ctx-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #2d3748;
  cursor: pointer;
}
.ctx-item:hover { background: #f1f5f9; }
.ctx-danger { color: #e53e3e; }
.ctx-danger:hover { background: #fff5f5; }

/* ezio: edit dialog fields */
.edit-field { display: flex; flex-direction: column; gap: 6px; }
.edit-label { font-size: 12px; font-weight: 600; color: #4a5568; }
.edit-select {
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}
.color-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.color-dot {
  width: 24px; height: 24px;
  border-radius: 50%;
  cursor: pointer;
  border: 1px solid #cbd5e1;
  outline-offset: 2px;
}
</style>
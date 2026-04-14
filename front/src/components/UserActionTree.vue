<template>
  <div class="user-action-tree-container" ref="container">
    <div class="header-panel">
      <div class="panel-title">Action Tree</div>
      <div class="count-badge">{{ nodesCount }}</div>
      <div style="flex: 1"></div>
      <div class="tree-legend">
        <div class="legend-item"><div class="legend-box" style="background:#fff5f5; border-color:#fed7d7"></div>System</div>
        <div class="legend-item"><div class="legend-box" style="background:#ebf8ff; border-color:#bee3f8"></div>Interact</div>
        <div class="legend-item"><div class="legend-box" style="background:#f0fff4; border-color:#c6f6d5"></div>Zoom/Scroll</div>
        <div class="legend-item"><div class="legend-box" style="background:#faf5ff; border-color:#e9d8fd"></div>Hover</div>
        <div class="legend-item"><div class="legend-box" style="background:#fef3c7; border-color:#fde68a"></div>Annotation</div>
      </div>
    </div>
    <div class="tree-content" ref="svgContainer">
      <svg ref="svg"></svg>
    </div>
    <!-- Tooltip div moved outside tree-content to avoid overflow clipping -->
    <div ref="tooltip" class="tree-tooltip" style="opacity: 0; display: none;"></div>
  </div>
</template>

<script>
import * as d3 from 'd3'

export default {
  name: 'UserActionTree',
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
      nodesCount: 0
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
    buildTreeData() {
      // Merge actions and annotations, sort by time
      let allEvents = [...this.actions]
      
      this.annotations.forEach(anno => {
        allEvents.push({
          ...anno,
          actionType: 'annotation',
          actionInfo: { text: anno.text, selectedItems: anno.selectedItems },
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
        'update_snapshot', 
        'run_entity_detection', 
        'update_link_detection', 
        'run_manipulation_detection'
      ]

      let lastGlobalNode = root;
      let lastNodeByView = {};

      allEvents.forEach((event, i) => {
        this.nodesCount++
        const isRootConfig = rootLevelActions.includes(event.actionType)
        
        let parent;
        if (isRootConfig) {
          parent = root;
        } else {
          const sv = event.sourceView || 'system';
          parent = lastNodeByView[sv] || lastGlobalNode;
        }
        
        const newNode = {
          id: `node_${i}`,
          name: this.formatActionType(event.actionType),
          type: event.actionType === 'annotation' ? 'annotation' : 'action',
          data: event,
          children: [],
          parent: parent
        }
        parent.children.push(newNode)
        
        if (isRootConfig) {
          lastGlobalNode = newNode;
          // Reset all views to point to this new global state
          Object.keys(lastNodeByView).forEach(k => {
            lastNodeByView[k] = newNode;
          });
          const tv = event.targetView;
          if (tv && tv !== 'all_views' && tv !== 'system') {
            lastNodeByView[tv] = newNode;
          }
        } else {
          const sv = event.sourceView || 'system';
          lastNodeByView[sv] = newNode;
          
          const tv = event.targetView;
          if (tv && tv !== 'system') {
            if (tv === 'all_views') {
              lastGlobalNode = newNode;
              Object.keys(lastNodeByView).forEach(k => {
                lastNodeByView[k] = newNode;
              });
            } else {
              lastNodeByView[tv] = newNode;
            }
          }
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
        if (type === 'sync_time_window') {
          return `Synchronized time window from ${summaryInfo.source === 'kline_chart' ? 'K-line Chart' : 'Behavior Details'}`
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
      // dx is the vertical distance between nodes, dy is the horizontal
      const dx = 24 // Vertical distance
      const baseDy = 60 // Base horizontal distance
      const tree = d3.tree().nodeSize([dx, baseDy])
      tree(root)

      // Post-process the tree to compact consecutive nodes of the same type on the same branch
      // We calculate a custom Y coordinate (horizontal position in the D3 layout)
      root.eachBefore(d => {
        if (d.parent) {
          // Check if this node is the ONLY child of its parent, AND they have the same action type
          const isContinuousSameType = 
            d.parent.children.length === 1 && 
            d.data.data && d.parent.data.data && 
            d.data.data.actionType === d.parent.data.data.actionType &&
            d.data.type !== 'root' && d.parent.data.type !== 'root';
            
          if (isContinuousSameType) {
            // Compress the horizontal gap (e.g., 12px instead of 60px)
            d.customY = d.parent.customY + 14;
          } else {
            // Use normal gap
            d.customY = d.parent.customY + baseDy;
          }
        } else {
          d.customY = 0;
        }
      })

      // Replace the default D3 computed y with our custom compressed y
      root.each(d => {
        d.y = d.customY;
      })

      // Center the tree in the SVG initially based on vertical (x) bounds
      let x0 = Infinity
      let x1 = -x0
      root.each(d => {
        if (d.x > x1) x1 = d.x
        if (d.x < x0) x0 = d.x
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

      // Helper to get action class (same as timeline)
      const getActionClass = (type) => {
        if (!type) return 'default'
        if (type.includes('zoom') || type.includes('scroll')) return 'zoom'
        if (type.startsWith('hover_')) return 'hover'
        if (type.includes('select') || type.includes('click')) return 'interaction'
        if (type.includes('run') || type.includes('update')) return 'system'
        return 'default'
      }

      // Colors mapping based on UserActionTimeline classes
      const typeColors = {
        interaction: { bg: '#ebf8ff', text: '#2b6cb0', border: '#bee3f8' },
        zoom: { bg: '#f0fff4', text: '#2c7a7b', border: '#c6f6d5' },
        hover: { bg: '#faf5ff', text: '#2f855a', border: '#e9d8fd' },
        system: { bg: '#fff5f5', text: '#c53030', border: '#fed7d7' },
        default: { bg: '#edf2f7', text: '#4a5568', border: '#e2e8f0' },
        annotation: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' }, // Amber from AnnotationTimeline
        sequential_group: { bg: '#cbd5e1', text: '#334155', border: '#94a3b8' } // Gray for the group node
      }

      // Nodes
      const node = g.append('g')
        .selectAll('g')
        .data(root.descendants())
        .join('g')
        .attr('transform', d => `translate(${d.y},${d.x})`)

      // Node Rectangles based on type
      node.append('rect')
        .attr('x', -8)
        .attr('y', -8)
        .attr('width', 16)
        .attr('height', 16)
        .attr('rx', 4) // Rounded corners
        .attr('fill', d => {
          if (d.data.type === 'root') return '#4a5568'
          if (d.data.type === 'annotation') return typeColors.annotation.bg
          const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
          return typeColors[cat] ? typeColors[cat].bg : typeColors.default.bg
        })
        .attr('stroke', d => {
          if (d.data.type === 'root') return '#2d3748'
          if (d.data.type === 'annotation') return typeColors.annotation.border
          const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
          return typeColors[cat] ? typeColors[cat].border : typeColors.default.border
        })
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer')
        
      const tooltipDiv = d3.select(this.$refs.tooltip)

      // Hover interactions
      node
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
             if (actionType === 'annotation') {
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
            
          d3.select(event.currentTarget).select('rect').attr('stroke', '#4a5568').attr('stroke-width', 2)
        })
        .on('mousemove', (event) => {
          tooltipDiv.style('left', (event.clientX + 15) + 'px')
            .style('top', (event.clientY - 30) + 'px')
        })
        .on('mouseout', (event, d) => {
          tooltipDiv.transition().duration(200).style('opacity', 0)
            .on('end', () => tooltipDiv.style('display', 'none'))
          d3.select(event.currentTarget).select('rect')
            .attr('stroke', d_data => {
              if (d_data.data.type === 'root') return '#2d3748'
              if (d_data.data.type === 'annotation') return typeColors.annotation.border
              const cat = getActionClass(d_data.data.data ? d_data.data.data.actionType : '')
              return typeColors[cat] ? typeColors[cat].border : typeColors.default.border
            })
            .attr('stroke-width', 1.5)
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
</style>
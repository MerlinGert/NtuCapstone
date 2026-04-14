<template>
  <div class="user-action-tree-container" ref="container">
    <div class="header-panel">
      <div class="panel-title">Action Tree</div>
      <div class="count-badge">{{ nodesCount }}</div>
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
        
        const newNode = {
          id: `node_${i}`,
          name: this.formatActionType(event.actionType),
          type: event.actionType === 'annotation' ? 'annotation' : 'action',
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
          if (seg.view === 'token_distribution') labelText = 'Token Distribution';
          else if (seg.view === 'kline_chart') labelText = 'K-line Chart';
          else if (seg.view === 'behavior_details') labelText = 'Behavior Details';
          
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
        if (type.includes('zoom') || type.includes('scroll')) return 'zoom'
        if (type.startsWith('hover_')) return 'hover'
        if (type.includes('select') || type.includes('click')) return 'interaction'
        if (type.includes('run') || type.includes('update')) return 'system'
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
          if (d.data.type === 'view_branch') return typeColors.view_branch.bg
          const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
          return typeColors[cat] ? typeColors[cat].bg : typeColors.default.bg
        })
        .attr('stroke', d => {
          if (d.data.type === 'root') return '#2d3748'
          if (d.data.type === 'annotation') return typeColors.annotation.border
          if (d.data.type === 'view_branch') return typeColors.view_branch.border
          const cat = getActionClass(d.data.data ? d.data.data.actionType : '')
          return typeColors[cat] ? typeColors[cat].border : typeColors.default.border
        })
        .attr('stroke-width', 1.5)
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
              if (d_data.data.type === 'view_branch') return typeColors.view_branch.border
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
<template>
  <div class="behavior-details-container" ref="container">
    <div v-if="!selectedUser && (!selectedUsersList || selectedUsersList.length === 0)" class="empty-state">
      Please select a user node or a manipulation card to view behavior details.
    </div>
    <div v-else class="details-content">
      <div class="header">
        <div class="header-left">
          <h3 class="user-id" v-if="selectedUsersList && selectedUsersList.length > 0">
            Card Users ({{ selectedUsersList.length }})
          </h3>
          <h3 class="user-id" v-else>User: {{ selectedUser }}</h3>
          <div v-if="entityInfo && (!selectedUsersList || selectedUsersList.length === 0)" class="entity-info">
            <span class="entity-badge">Part of Entity</span>
            <span class="entity-members">Members: {{ entityInfo.users.length }}</span>
          </div>
        </div>
        <div class="controls">
          <button 
            v-if="syncTargetTimeWindow && syncTargetTimeWindow.length === 2" 
            class="action-btn sync-btn" 
            :disabled="useSequentialTime"
            @click="() => {
              if (useSequentialTime) return;
              syncTimeWindow();
              $emit('log-action', 'sync_time_window', { source: 'behavior_details' });
            }"
            title="Sync time window to K-Line view"
            :style="{
              fontSize: '12px', fontWeight: 'normal', padding: '2px 6px', display: 'flex', alignItems: 'center', gap: '4px'
            }"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"></path><path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path><path d="M3 22v-6h6"></path><path d="M21 12a9 9 0 0 1-15 6.7L3 16"></path></svg>
            Sync Time
          </button>
          
          <div v-if="!selectedUsersList || selectedUsersList.length === 0" style="display: flex; align-items: center; gap: 8px; margin-right: 15px;">
            <label class="toggle-switch">
              <input type="checkbox" v-model="showRelatedUsers" @change="() => {
                $emit('log-action', 'toggle_show_related_users', { enabled: showRelatedUsers });
                drawChart();
              }">
              <span class="slider"></span>
            </label>
            <span class="toggle-text">Show Related Users</span>
          </div>

          <div style="display: flex; align-items: center; gap: 8px; margin-right: 15px;">
            <label class="toggle-switch">
              <input type="checkbox" v-model="useSequentialTime" @change="() => {
                $emit('sequential-time-changed', useSequentialTime);
                $emit('log-action', 'toggle_sequential_time', { enabled: useSequentialTime });
                drawChart();
              }">
              <span class="slider"></span>
            </label>
            <span class="toggle-text">Sequential Time</span>
          </div>

          <div v-if="manipulationResults && manipulationResults.length > 0" style="display: flex; align-items: center; gap: 8px;">
            <label class="toggle-switch">
              <input type="checkbox" v-model="showManipulationBoxes" @change="() => {
                $emit('log-action', 'toggle_show_manipulation_boxes', { enabled: showManipulationBoxes });
                drawChart();
              }">
              <span class="slider"></span>
            </label>
            <span class="toggle-text">Show Manipulation Boxes</span>
          </div>
          <!-- ezio: Snapshot button -->
          <button @click="openSnapshot" title="Snapshot & Annotate" class="action-btn snapshot-btn" style="padding: 4px; display: flex; align-items: center; justify-content: center; margin-left: 8px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
          </button>
        </div>
      </div>
      
      <div class="data-view">
        <div v-if="!behaviorData" class="loading">Loading behavior data...</div>
        <div v-else-if="Object.keys(behaviorData).length === 0" class="empty-data">
          No behavior data available for this user and its relations.
        </div>
        <div v-else class="behavior-list" ref="chartContainer" style="position: relative;">
          <!-- The D3 chart will be drawn here -->
          <div ref="tooltip" class="custom-tooltip" style="opacity: 0; display: none;"></div>
        </div>
      </div>
    </div>
    <!-- ezio: Behavior Snapshot Modal -->
    <div v-if="showSnapshot" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; justify-content: center; align-items: center;">
      <!-- ezio: bubble snapshot-input event to parent -->
      <BehaviorSnapshot :snapshot-data="snapshotPayload" @close="showSnapshot = false" @snapshot-input="$emit('snapshot-input', $event)" />
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3';
// ezio: import BehaviorSnapshot
import BehaviorSnapshot from './BehaviorSnapshot.vue';

export default {
  name: 'BehaviorDetails',
  // ezio: register BehaviorSnapshot component
  components: { BehaviorSnapshot },
  props: {
    selectedUser: {
      type: String,
      default: null,
    },
    selectedUsersList: {
      type: Array,
      default: () => [],
    },
    behaviorData: {
      type: Object,
      default: () => null,
    },
    entityInfo: {
      type: Object,
      default: () => null,
    },
    snapshotTime: {
      type: String,
      default: null,
    },
    manipulationResults: {
      type: Array,
      default: () => [],
    },
    syncTargetTimeWindow: {
      type: Array,
      default: () => null,
    },
  },
  data() {
    return {
      showManipulationBoxes: true,
      showRelatedUsers: false,
      useSequentialTime: false, // New property for Sequential Time
      // ezio: snapshot state
      showSnapshot: false,
      snapshotPayload: null
    };
  },
  watch: {
    behaviorData: {
      handler(newVal) {
        if (newVal && Object.keys(newVal).length > 0) {
          this.$nextTick(() => {
            this.drawChart()
          })
        }
      },
      deep: true,
    },
    entityInfo: {
      handler() {
        this.$nextTick(() => {
          this.drawChart()
        })
      },
      deep: true,
    },
    manipulationResults: {
      handler() {
        this.$nextTick(() => {
          this.drawChart()
        })
      },
      deep: true,
    },
  },
  mounted() {
    window.addEventListener('resize', this.handleResize)
    if (this.behaviorData && Object.keys(this.behaviorData).length > 0) {
      this.drawChart()
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },
  methods: {
    handleResize() {
      if (this.behaviorData && Object.keys(this.behaviorData).length > 0) {
        this.drawChart()
      }
    },
    // ezio: open snapshot modal
    openSnapshot() {
      this.snapshotPayload = this.captureSnapshot();
      this.showSnapshot = true;
    },
    // ezio: capture current visualization state for snapshot — directly reuses drawChart() computed data
    captureSnapshot() {
      if (!this._lastChartState) return null;

      const state = this._lastChartState;
      // ezio: [2/3 DetailSnapshot initial state] include saved zoom transform in payload so snapshot opens at same view
      const zt = this._currentZoomTransform;
      const initialZoom = zt ? { k: zt.k, x: zt.x, y: zt.y } : null;

      // ezio: capture original chart dimensions for aspect-ratio preservation in snapshot
      const chartContainer = this.$refs.chartContainer;
      const originalWidth = chartContainer ? chartContainer.clientWidth : 800;
      const originalHeight = chartContainer ? chartContainer.clientHeight : 400;

      return {
        time: this.snapshotTime,
        selectedUser: this.selectedUser,
        sortedUsers: state.sortedUsers,
        filteredData: state.filteredData,
        sequenceData: state.sequenceData,
        timeDomain: state.timeDomain,
        entityInfo: this.entityInfo,
        entityUsers: state.entityUsers,
        manipulationResults: this.manipulationResults,
        showManipulationBoxes: this.showManipulationBoxes,
        isFewUsers: state.isFewUsers,
        eventBoxPadding: state.eventBoxPadding,
        initialZoom,
        // ezio: pass aspect ratio and original dimensions so snapshot can match proportions
        chartAspectRatio: originalWidth / originalHeight,
        originalWidth,
        originalHeight,
        useSequentialTime: this.useSequentialTime,
        timeToIndex: this._chartState && this._chartState.xScale && this._chartState.xScale.timeToIndex ? Array.from(this._chartState.xScale.timeToIndex.entries()) : null,
        sortedTimestamps: this._chartState && this._chartState.xScale && this._chartState.xScale.sortedTimestamps ? this._chartState.xScale.sortedTimestamps : null,
        margin: this._chartState ? this._chartState.margin : { top: 30, right: 20, bottom: 25, left: 40 },
        xScaleDomain: this._chartState && this._chartState.xScale ? this._chartState.xScale.domain() : null
      };
    },
    drawChart() {
      const container = this.$refs.chartContainer
      if (!container) return

      // Clear previous chart (only remove svg, keep the tooltip div)
      d3.select(container).selectAll('svg').remove()

      let usersToDraw = Object.keys(this.behaviorData || {})

      if (this.selectedUsersList && this.selectedUsersList.length > 0) {
        // Card mode: use users from card (which should be exactly what's in behaviorData)
        usersToDraw = [...this.selectedUsersList].filter(u => this.behaviorData[u])
      } else if (!this.showRelatedUsers && this.selectedUser) {
        // User mode, single user only
        usersToDraw = [this.selectedUser].filter(u => this.behaviorData[u])
      }

      // Sort users: selectedUser in the middle, entity users adjacent, then other users
      const entityUsers = this.entityInfo
        ? this.entityInfo.users.filter(
            (u) => u !== this.selectedUser && usersToDraw.includes(u),
          )
        : []
      const otherUsers = usersToDraw.filter(
        (u) => u !== this.selectedUser && !entityUsers.includes(u),
      )

      // Balance users to keep selectedUser in the center
      let topHalf = []
      let bottomHalf = []

      // Distribute entity users closely around the selected user
      entityUsers.forEach((u) => {
        if (topHalf.length <= bottomHalf.length) {
          topHalf.push(u) // Add to end of topHalf (will be closest to center after reversal)
        } else {
          bottomHalf.push(u) // Add to start of bottomHalf (closest to center)
        }
      })

      // Distribute other users further outwards
      otherUsers.forEach((u) => {
        if (topHalf.length <= bottomHalf.length) {
          topHalf.push(u)
        } else {
          bottomHalf.push(u)
        }
      })

      // Reverse topHalf so the first elements added (entity users) are closest to the middle
      topHalf.reverse()

      let sortedUsers = []
      if (this.selectedUsersList && this.selectedUsersList.length > 0) {
        // In card mode, there is no single "selectedUser" in the middle, just list them all
        sortedUsers = usersToDraw
      } else {
        sortedUsers = this.selectedUser && usersToDraw.includes(this.selectedUser) 
          ? [...topHalf, this.selectedUser, ...bottomHalf]
          : [...topHalf, ...bottomHalf]
      }

      // Filter behavior data based on snapshot time
      const parseDateSafe = (dateStr) => {
        if (!dateStr) return new Date(NaN)
        let d = new Date(dateStr)
        if (Number.isNaN(d.getTime()) && typeof dateStr === 'string') {
          // Try removing ' UTC' and replacing space with 'T' for Safari/iOS
          let cleaned = dateStr.replace(' UTC', 'Z').replace(' ', 'T')
          d = new Date(cleaned)
        }
        return d
      }

      const snapshotDate = this.snapshotTime
        ? parseDateSafe(this.snapshotTime)
        : new Date()
      let earliestDate = snapshotDate
      let hasData = false

      const filteredData = {}
      const sequenceData = {} // Store continuous balance and earning_usd sequences
      const MAX_EVENTS_PER_USER = 1500 // Limit rendering to prevent browser freeze

      sortedUsers.forEach((user) => {
        const events = this.behaviorData[user] || []
        let validEvents = events.filter((event) => {
          if (!event.timestamp) return false
          const eventDate = parseDateSafe(event.timestamp)
          if (Number.isNaN(eventDate.getTime())) return false
          return eventDate <= snapshotDate
        })

        let currentBalance = 0
        let avgBuyPrice = 0
        const seq = []
        const earningEvents = [] // Store discrete earning events for selling

        // We must calculate the balance sequence using ALL valid events first to ensure accuracy
        validEvents.forEach((event) => {
          const eventDate = parseDateSafe(event.timestamp)
          if (eventDate < earliestDate) {
            earliestDate = eventDate
          }
          hasData = true

          let earningChange = 0
          event._prevBalance = currentBalance

          // Update balance based on event type
          if (event.type === 'transfer_in') {
            currentBalance += parseFloat(event.amount) || 0
          } else if (event.type === 'transfer_out') {
            currentBalance -= parseFloat(event.amount) || 0
          }

          event._currentBalance = currentBalance
          event._eventDate = eventDate // Cache the parsed date

          if (event.isTrade && event.trade_info) {
            const isBuy = event.trade_info.action === 'buy'
            const amt = parseFloat(event.amount) || 0
            const price = parseFloat(event.trade_info.price_usd) || 0

            if (isBuy) {
              // Update Weighted Average Buy Price (WABP)
              if (currentBalance < 0) {
                avgBuyPrice = price
              } else {
                const totalCost = currentBalance * avgBuyPrice + amt * price
                if (currentBalance + amt > 0) {
                  avgBuyPrice = totalCost / (currentBalance + amt)
                }
              }
            } else {
              // Calculate Earning on Sell: (Sell Price - WABP) * Sell Amount
              earningChange = (price - avgBuyPrice) * amt
              if (earningChange !== 0) {
                earningEvents.push({
                  date: eventDate,
                  earning: earningChange,
                })
              }
            }
          }

          seq.push({
            date: eventDate,
            balance: currentBalance,
          })
        })

        // Add a final point at snapshotDate to extend the area chart to the right edge
        if (seq.length > 0) {
          seq.push({
            date: snapshotDate,
            balance: currentBalance,
          })
        }

        // Now apply downsampling for SVG rendering (circles, lines) if too many events
        if (validEvents.length > MAX_EVENTS_PER_USER) {
          console.warn(
            `Downsampling events for user ${user} from ${validEvents.length} to ${MAX_EVENTS_PER_USER}`,
          )
          const step = Math.max(
            1,
            Math.floor(validEvents.length / MAX_EVENTS_PER_USER),
          )
          validEvents = validEvents.filter((_, index) => index % step === 0)
        }

        filteredData[user] = validEvents

        // We can also downsample the area chart points slightly if they are massive
        let finalSeq = seq
        if (seq.length > MAX_EVENTS_PER_USER * 2) {
          const seqStep = Math.max(
            1,
            Math.floor(seq.length / (MAX_EVENTS_PER_USER * 2)),
          )
          finalSeq = seq.filter(
            (_, index) => index % seqStep === 0 || index === seq.length - 1,
          )
        }

        // Aggregate earning events that happen at the exact same time
        const earningMap = new Map();
        earningEvents.forEach(e => {
          const timeKey = e.date.getTime();
          if (earningMap.has(timeKey)) {
             earningMap.get(timeKey).earning += e.earning;
          } else {
             earningMap.set(timeKey, { date: e.date, earning: e.earning });
          }
        });
        const aggregatedEarningEvents = Array.from(earningMap.values());

        sequenceData[user] = { seq: finalSeq, earningEvents: aggregatedEarningEvents }
      })

      // ezio: save chart state so captureSnapshot() can reuse exactly what drawChart() computed
      this._lastChartState = {
        sortedUsers,
        filteredData,
        sequenceData,
        timeDomain: [earliestDate.getTime(), snapshotDate.getTime()],
        entityUsers,
        isFewUsers: sortedUsers.length <= 5,
        eventBoxPadding: sortedUsers.length <= 5 ? 10 : 6,
      }

      // Set up dimensions
      const width = container.clientWidth || 800
      const height = container.clientHeight || 400
      const margin = { top: 30, right: 20, bottom: 25, left: 40 } // Adjusted bottom margin
      const innerWidth = width - margin.left - margin.right
      const innerHeight = height - margin.top - margin.bottom

      // Create SVG
      const rootSvg = d3
        .select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)

      // Define clip path
      const defs = rootSvg.append('defs')
      defs
        .append('clipPath')
        .attr('id', 'chart-clip')
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight)

      // We append a background rect to capture zoom events across the whole SVG
      rootSvg
        .append('rect')
        .attr('width', width)
        .attr('height', height)
        .style('fill', 'none')
        .style('pointer-events', 'all')

      const svg = rootSvg
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`)

      const chartBody = svg.append('g').attr('clip-path', 'url(#chart-clip)')

      // Y Scale for users (evenly distributed)
      const yScale = d3
        .scalePoint()
        .domain(sortedUsers)
        .range([0, innerHeight])
        .padding(0.5)

      // X Scale setup
      let xScale;
      let xAxis;
      
      // We need to collect all unique timestamps for sequential time mode
      const uniqueTimestamps = new Set();
      
      if (this.useSequentialTime && hasData) {
        // Collect all timestamps from filtered data
        sortedUsers.forEach(user => {
          if (filteredData[user]) {
            filteredData[user].forEach(event => {
              const ts = parseDateSafe(event.timestamp).getTime();
              if (!isNaN(ts)) uniqueTimestamps.add(ts);
            });
          }
          if (sequenceData[user]) {
            sequenceData[user].seq.forEach(d => {
               uniqueTimestamps.add(d.date.getTime());
            });
            sequenceData[user].earningEvents.forEach(d => {
               uniqueTimestamps.add(d.date.getTime());
            });
          }
        });
        
        // Add start and end dates to ensure full domain coverage
        uniqueTimestamps.add(earliestDate.getTime());
        uniqueTimestamps.add(snapshotDate.getTime());
        
        const sortedTimestamps = Array.from(uniqueTimestamps).sort((a, b) => a - b);
        
        xScale = d3.scaleLinear()
          .domain([0, sortedTimestamps.length > 0 ? sortedTimestamps.length - 1 : 1])
          .range([0, innerWidth]);
          
        xAxis = d3.axisBottom(xScale).ticks(10).tickFormat(i => {
          const index = Math.round(i);
          if (index >= 0 && index < sortedTimestamps.length) {
            return d3.timeFormat('%m-%d %H:%M')(new Date(sortedTimestamps[index]));
          }
          return '';
        });
        
        // Store mapping for O(1) lookups during rendering
        xScale.timeToIndex = new Map(sortedTimestamps.map((ts, i) => [ts, i]));
        xScale.sortedTimestamps = sortedTimestamps;
        
      } else {
        // Absolute Time (Default)
        xScale = d3
          .scaleTime()
          .domain([earliestDate, snapshotDate])
          .range([0, innerWidth])
          
        xAxis = d3.axisBottom(xScale)
      }

      // X Axis (Bottom)
      const xAxisGroup = svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0, ${innerHeight})`)
        .call(xAxis)
        
      // Professional styling for the X axis
      xAxisGroup.select('.domain').attr('stroke', '#e2e8f0').attr('stroke-width', 1.5)
      xAxisGroup.selectAll('.tick line').attr('stroke', '#cbd5e1')
      xAxisGroup.selectAll('.tick text')
        .attr('fill', '#4a5568')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .attr('font-family', 'Inter, -apple-system, sans-serif')
        .attr('dy', '0.8em')

      // Helper function to get X coordinate regardless of scale type
      const getX = (dateObj) => {
        if (!dateObj || isNaN(dateObj.getTime())) return 0;
        const ts = dateObj.getTime();
        
        if (this.useSequentialTime && xScale.timeToIndex) {
          // Exact match
          if (xScale.timeToIndex.has(ts)) {
            return xScale(xScale.timeToIndex.get(ts));
          }
          // If not exact match (e.g. manipulation box start/end), find the closest index using binary search or simple loop
          // (Since array isn't massive, simple find/bisect is fine)
          const sorted = xScale.sortedTimestamps;
          let closestIdx = 0;
          let minDiff = Infinity;
          for (let i = 0; i < sorted.length; i++) {
             const diff = Math.abs(sorted[i] - ts);
             if (diff < minDiff) {
                minDiff = diff;
                closestIdx = i;
             }
             if (sorted[i] > ts) break; // Optimization since it's sorted
          }
          return xScale(closestIdx);
        } else {
          return xScale(dateObj);
        }
      }

      // Define padding for event elements
      // If there are few users, we can make the dots row larger
      const isFewUsers = sortedUsers.length <= 5
      const eventBoxPadding = isFewUsers ? 10 : 6

      // Create a group for background elements (baselines, area charts, earning bars)
      const backgroundGroup = chartBody
        .append('g')
        .attr('class', 'background-group')

      // Draw horizontal baselines for each user
      // Balance baseline (bottom boundary of balance)
      backgroundGroup
        .selectAll('.balance-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'balance-baseline')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', (d) => yScale(d) - eventBoxPadding)
        .attr('y2', (d) => yScale(d) - eventBoxPadding)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 1)

      // Earning baseline (top boundary of earning)
      backgroundGroup
        .selectAll('.earning-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'earning-baseline')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', (d) => yScale(d) + eventBoxPadding)
        .attr('y2', (d) => yScale(d) + eventBoxPadding)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 1)

      // Create a group for foreground elements (manipulation boxes, points, transfer lines)
      const foregroundGroup = chartBody
        .append('g')
        .attr('class', 'foreground-group')

      // Draw Manipulation Bounding Boxes
      if (
        this.showManipulationBoxes &&
        this.manipulationResults &&
        this.manipulationResults.length > 0
      ) {
        this.manipulationResults.forEach((result) => {
          if (
            !result.participants ||
            !result.manipulation_time ||
            result.manipulation_time.length === 0
          )
            return

          const involvedUsers = sortedUsers.filter((u) =>
            result.participants.includes(u),
          )
          if (involvedUsers.length === 0) return

          // Find time window
          let startStr = result.manipulation_time[0]
          let endStr =
            result.manipulation_time.length > 1
              ? result.manipulation_time[1]
              : startStr

          // Ensure time strings have UTC to match other timestamps
          if (!startStr.endsWith('UTC')) startStr += ' UTC'
          if (!endStr.endsWith('UTC')) endStr += ' UTC'

          let startTs = new Date(startStr)
          let endTs = new Date(endStr)

          if (Number.isNaN(startTs) || Number.isNaN(endTs)) return

          let x1 = getX(startTs)
          let x2 = getX(endTs)

          // Ensure min width if it's a single point or very short
          if (x2 - x1 < 10) {
            const center = (x1 + x2) / 2
            x1 = center - 5
            x2 = center + 5
          }

          // Format tooltip details
          let tooltipHtml = `<strong>Method:</strong> ${result.detection_method}<br>`
          if (result.participants && result.participants.length > 1) {
            tooltipHtml += `<strong>Type:</strong> Entity-based (across ${result.participants.length} users)<br>`
          }
          tooltipHtml += `<strong>Time:</strong> ${startStr} - ${endStr}<br>`

          if (result.features) {
            tooltipHtml += `<ul style="margin: 4px 0; padding-left: 16px;">`
            Object.entries(result.features).forEach(([key, value]) => {
              if (typeof value === 'number') {
                tooltipHtml += `<li><strong>${key}:</strong> ${value.toFixed(2)}</li>`
              } else {
                tooltipHtml += `<li><strong>${key}:</strong> ${value}</li>`
              }
            })
            tooltipHtml += `</ul>`
          }
          if (result.transactions) {
            tooltipHtml += `<strong>Transactions count:</strong> ${result.transactions.length}`
          }

          const self = this

          // Draw separate boxes for each involved user
          involvedUsers.forEach((user) => {
            const height = eventBoxPadding * 2
            const y = yScale(user) - eventBoxPadding

            foregroundGroup
              .append('rect')
              .datum({ startTs, endTs })
              .attr('class', 'manipulation-box')
              .attr('x', x1)
              .attr('y', y)
              .attr('width', x2 - x1)
              .attr('height', height)
              .attr('fill', 'rgba(255, 0, 0, 0.05)')
              .attr('stroke', 'rgba(255, 0, 0, 0.6)')
              .attr('stroke-width', 1) // Made the stroke thinner
              .attr('rx', 4)
              .attr('ry', 4)
              .style('pointer-events', 'all')
              .on('mouseover mouseenter pointerover', function (event) {
                self.$emit('log-action', 'hover_behavior_manipulation_box', { 
                  method: result.detection_method, 
                  time: `${startStr} - ${endStr}`,
                  usersCount: involvedUsers.length
                })
                d3.select(this).attr('fill', 'rgba(255, 0, 0, 0.15)')
                const tooltip = self.$refs.tooltip
                tooltip.innerHTML = tooltipHtml
                tooltip.style.display = 'block'
                tooltip.style.opacity = 1

                // Position relative to chart container
                const [mx, my] = d3.pointer(event, self.$refs.chartContainer)
                tooltip.style.left = `${(mx || 0) + 15}px`
                tooltip.style.top = `${(my || 0) + 15}px`
              })
              .on('mousemove pointermove', (event) => {
                const tooltip = self.$refs.tooltip
                const [mx, my] = d3.pointer(event, self.$refs.chartContainer)

                // Adjust position to prevent tooltip from going off-screen
                const containerWidth = self.$refs.chartContainer.clientWidth
                const tooltipWidth = tooltip.offsetWidth
                let left = (mx || 0) + 15
                if (left + tooltipWidth > containerWidth) {
                  left = (mx || 0) - tooltipWidth - 10
                }

                tooltip.style.left = `${left}px`
                tooltip.style.top = `${(my || 0) + 15}px`
              })
              .on('mouseout mouseleave pointerout', function () {
                self.$emit('log-action', 'cancel_hover', { hoverType: 'hover_behavior_manipulation_box' })
                d3.select(this).attr('fill', 'rgba(255, 0, 0, 0.05)')
                const tooltip = self.$refs.tooltip
                tooltip.style.opacity = 0
                tooltip.style.display = 'none'
              })
          })
        })
      }

      // Draw Entity Bounding Box if applicable
      if (this.entityInfo?.users && this.entityInfo.users.length > 0) {
        const entityUsersInView = sortedUsers.filter((u) =>
          this.entityInfo.users.includes(u),
        )
        if (entityUsersInView.length > 0) {
          const yPositions = entityUsersInView.map((u) => yScale(u))
          const minY = Math.min(...yPositions)
          const maxY = Math.max(...yPositions)
          const boxPadding = 12 // padding around the text
          const boxWidth = 32 // approximate width of the truncated text

          svg
            .append('rect')
            .attr('x', -margin.left + 5) // Shifted right slightly
            .attr('y', minY - boxPadding)
            .attr('width', boxWidth)
            .attr('height', maxY - minY + boxPadding * 2)
            .attr('fill', 'none')
            .attr('stroke', '#ff9800')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '5,5')
            .attr('rx', 4)
            .attr('ry', 4)
        }
      }

      // Draw user labels
      svg
        .selectAll('.user-label')
        .data(sortedUsers)
        .enter()
        .append('text')
        .attr('class', 'user-label')
        .attr('x', -5) // Text anchor is 'end', so this is the right edge of the text
        .attr('y', (d) => yScale(d))
        .attr('dy', '0.32em')
        .attr('text-anchor', 'end')
        .attr('fill', (d) => {
          if (d === this.selectedUser) return '#2d3748'
          if (entityUsers.includes(d)) return '#3182ce'
          return '#718096'
        })
        .attr('font-weight', (d) =>
          d === this.selectedUser ? 'bold' : 'normal',
        )
        .attr('font-size', '11px')
        .style('cursor', 'pointer')
        .text((d) => `${d.substring(0, 3)}..`)
        .on('click', (event, d) => {
          this.$emit('user-selected', d)
        })
        .on('mouseover mouseenter pointerover', (event, d) => {
          this.$emit('log-action', 'hover_behavior_user_label', { hoveredUserId: d })
          d3.select(event.currentTarget).attr('font-weight', 'bold')
          
          const tooltip = d3.select(this.$refs.tooltip)
          tooltip.transition().duration(200).style('opacity', 0.9)

          let type = 'Related User'
          if (d === this.selectedUser) type = 'Selected User'
          else if (entityUsers.includes(d)) type = 'Entity Member'
          
          let htmlContent = `<strong>${type}:</strong><br/>${d}`

          const [x, y] = d3.pointer(event, this.$refs.chartContainer)
          tooltip
            .html(htmlContent)
            .style('display', 'block')
            .style('left', `${(x || 0) + 10}px`)
            .style('top', `${(y || 0) - 28}px`)
        })
        .on('mousemove pointermove', (event) => {
          const tooltip = d3.select(this.$refs.tooltip)
          const [x, y] = d3.pointer(event, this.$refs.chartContainer)
          tooltip.style('left', `${(x || 0) + 10}px`).style('top', `${(y || 0) - 28}px`)
        })
        .on('mouseout mouseleave pointerout', (event, d) => {
          this.$emit('log-action', 'cancel_hover', { hoverType: 'hover_behavior_user_label' })
          d3.select(event.currentTarget).attr('font-weight', d === this.selectedUser ? 'bold' : 'normal')
          
          d3.select(this.$refs.tooltip)
            .transition()
            .duration(500)
            .style('opacity', 0)
            .on('end', function() {
              d3.select(this).style('display', 'none')
            })
        })

      // Draw behavior points and area charts
      let balanceScale
      if (hasData) {
        // Find global max/min for scales
        let maxBalance = 0
        let maxAbsEarning = 0

        Object.values(sequenceData).forEach((data) => {
          data.seq.forEach((d) => {
            if (d.balance > maxBalance) maxBalance = d.balance
          })
          data.earningEvents.forEach((d) => {
            if (Math.abs(d.earning) > maxAbsEarning)
              maxAbsEarning = Math.abs(d.earning)
          })
        })

        // We want the area chart to fit within the row height (distance between user lines)
        // If there are few users, we reduce the proportion of balance/earning height to make more room for the dots
        const rowHeight = yScale.step()
        const heightProportion = isFewUsers ? 0.3 : 0.5
        const maxAreaHeight = rowHeight * heightProportion

        balanceScale = d3
          .scaleLinear()
          .domain([0, maxBalance || 1])
          .range([0, -maxAreaHeight]) // Upwards (negative y)

        const earningScale = d3
          .scaleLinear()
          .domain([0, maxAbsEarning || 1])
          .range([0, maxAreaHeight]) // Downwards (positive y)

        const balanceArea = d3
          .area()
          .x((d) => getX(d.date))
          .y0(-eventBoxPadding)
          .y1((d) => balanceScale(d.balance) - eventBoxPadding)
          .curve(d3.curveStepAfter)

        // Prepare transfer line marker
        defs
          .append('marker')
          .attr('id', 'transfer-arrow')
          .attr('viewBox', '0 -5 10 10')
          .attr('refX', 12)
          .attr('refY', 0)
          .attr('markerWidth', 6)
          .attr('markerHeight', 6)
          .attr('orient', 'auto')
          .append('path')
          .attr('d', 'M0,-5L10,0L0,5')
          .attr('fill', '#A0AEC0')

        const transferLinesGroup = foregroundGroup
          .append('g')
          .attr('class', 'transfer-lines')

        sortedUsers.forEach((user) => {
          const events = filteredData[user] || []
          const { seq, earningEvents } = sequenceData[user] || {
            seq: [],
            earningEvents: [],
          }

          const userBackgroundGroup = backgroundGroup
            .append('g')
            .attr('class', 'user-background')
            .attr('transform', `translate(0, ${yScale(user)})`)

          const userForegroundGroup = foregroundGroup
            .append('g')
            .attr('class', 'user-foreground')
            .attr('transform', `translate(0, ${yScale(user)})`)

          // Draw Area Charts and Bars first so they are behind the points
          if (seq.length > 0) {
            // Balance Area (Above line)
            userBackgroundGroup
              .append('path')
              .datum(seq)
              .attr('class', 'balance-area')
              .attr('fill', '#90cdf4')
              .attr('opacity', 0.4)
              .attr('d', balanceArea)
          }

          // Draw Discrete Earning Bars (Below line)
          if (earningEvents.length > 0) {
            const barWidth = 4 // Fixed width for discrete events
            userBackgroundGroup
              .selectAll('.earning-bar')
              .data(earningEvents)
              .enter()
              .append('rect')
              .attr('class', 'earning-bar')
              .attr('x', (d) => getX(d.date) - barWidth / 2)
              .attr('y', eventBoxPadding)
              .attr('width', barWidth)
              .attr('height', (d) => earningScale(Math.abs(d.earning)))
              .attr('fill', (d) => (d.earning >= 0 ? '#68d391' : '#fc8181')) // Green for profit, Red for loss
              .attr('opacity', 0.8)
              .append('title') // Add simple tooltip
              .text((d) => `Earning: $${d.earning.toFixed(2)}`)
          }

          events.forEach((event) => {
            const eventDate = parseDateSafe(event.timestamp)
            const cx = getX(eventDate)

            if (!event.isTrade) {
              const isOut = event.type === 'transfer_out'
              const counterpartyInView = sortedUsers.includes(
                event.counterparty,
              )

              // Only draw lines if it's an internal transfer between users in the current view
              if (isOut && counterpartyInView && user !== event.counterparty) {
                const startY = yScale(user)
                const endY = yScale(event.counterparty)

                transferLinesGroup
                  .append('line')
                  .datum({ cx_date: eventDate })
                  .attr('class', 'transfer-line')
                  .attr('x1', cx)
                  .attr('x2', cx)
                  .attr('y1', startY)
                  .attr('y2', endY)
                  .attr('stroke', '#A0AEC0')
                  .attr('stroke-width', 1.5)
                  .attr('marker-end', 'url(#transfer-arrow)')
                  .attr('opacity', 0.6)
                  .append('title')
                  .text(`Transfer ${event.amount} to ${event.counterparty}`)
              }
            }

            const eventGroup = userForegroundGroup
              .append('g')
              .datum({ date: eventDate })
              .attr('class', 'event-group')
              .attr('transform', `translate(${cx}, 0)`)

            let circleColor = '#A0AEC0' // default grey for transfers
            let tooltipText = ''

            if (event.isTrade) {
              const isBuy =
                event.trade_info && event.trade_info.action === 'buy'
              circleColor = isBuy ? '#4299e1' : '#ed64a6' // blue for buy, pink for sell
              tooltipText = `${isBuy ? 'Buy' : 'Sell'}: ${event.amount} @ $${parseFloat(event.trade_info?.price_usd || 0).toFixed(4)}`

              const y1 = balanceScale(event._prevBalance || 0) - eventBoxPadding
              const y2 =
                balanceScale(event._currentBalance || 0) - eventBoxPadding

              // Draw balance difference bar
              eventGroup
                .append('line')
                .attr('x1', 0)
                .attr('x2', 0)
                .attr('y1', y1)
                .attr('y2', y2)
                .attr('stroke', circleColor)
                .attr('stroke-width', 4)
                .attr('opacity', 0.8)
                .append('title')
                .text(
                  `Balance change: ${Math.abs(event._currentBalance - event._prevBalance)}`,
                )
            } else {
              const isTransferIn = event.type === 'transfer_in'
              tooltipText = `${isTransferIn ? 'Transfer In' : 'Transfer Out'}: ${event.amount}`
            }

            const circleRadius = isFewUsers ? 4 : 2
            eventGroup
              .append('circle')
              .attr('r', circleRadius)
              .attr('cy', 0)
              .attr('fill', circleColor)
              .attr('opacity', 0.6)
              .attr('stroke', d3.color(circleColor).darker(0.8))
              .attr('stroke-width', 0.5)
              .append('title')
              .text(tooltipText)
          })
        })
      }

      // Setup Zoom
      const zoom = d3
        .zoom()
        .scaleExtent([1, 50])
        .translateExtent([
          [0, 0],
          [width, height],
        ])
        .extent([
          [0, 0],
          [width, height],
        ])
        .on('zoom', (event) => {
          const newXScale = event.transform.rescaleX(xScale)
          
          // Re-create the getX helper for the zoomed scale
          const getZoomedX = (dateObj) => {
            if (!dateObj || isNaN(dateObj.getTime())) return 0;
            const ts = dateObj.getTime();
            
            if (this.useSequentialTime && xScale.timeToIndex) {
              if (xScale.timeToIndex.has(ts)) {
                return newXScale(xScale.timeToIndex.get(ts));
              }
              const sorted = xScale.sortedTimestamps;
              let closestIdx = 0;
              let minDiff = Infinity;
              for (let i = 0; i < sorted.length; i++) {
                 const diff = Math.abs(sorted[i] - ts);
                 if (diff < minDiff) {
                    minDiff = diff;
                    closestIdx = i;
                 }
                 if (sorted[i] > ts) break;
              }
              return newXScale(closestIdx);
            } else {
              return newXScale(dateObj);
            }
          }
          
          const domain = newXScale.domain()
          // Only emit to parent if the zoom was initiated by a user event to prevent infinite sync loops
          if (event.sourceEvent && !this.useSequentialTime) {
            this.$emit('time-window-changed', [domain[0], domain[1]])
          }
          // ezio: [1/3 DetailSnapshot initial state] persist zoom transform on every zoom event for snapshot reuse
          this._currentZoomTransform = event.transform

          // Update X Axis
          xAxisGroup.call(xAxis.scale(newXScale))
          
          // Re-apply styles after zoom redraws the axis
          xAxisGroup.select('.domain').attr('stroke', '#e2e8f0').attr('stroke-width', 1.5)
          xAxisGroup.selectAll('.tick line').attr('stroke', '#cbd5e1')
          xAxisGroup.selectAll('.tick text')
            .attr('fill', '#4a5568')
            .attr('font-size', '10px')
            .attr('font-weight', '500')
            .attr('font-family', 'Inter, -apple-system, sans-serif')
            .attr('dy', '0.8em')

          // Update Manipulation Boxes
          chartBody
            .selectAll('.manipulation-box')
            .attr('x', (d) => {
              let x1 = getZoomedX(d.startTs)
              let x2 = getZoomedX(d.endTs)
              if (x2 - x1 < 10) return (x1 + x2) / 2 - 5
              return x1
            })
            .attr('width', (d) => {
              let x1 = getZoomedX(d.startTs)
              let x2 = getZoomedX(d.endTs)
              if (x2 - x1 < 10) return 10
              return x2 - x1
            })

          if (hasData && balanceScale) {
            // Update Balance Area
            const newBalanceArea = d3
              .area()
              .x((d) => getZoomedX(d.date))
              .y0(-eventBoxPadding)
              .y1((d) => balanceScale(d.balance) - eventBoxPadding)
              .curve(d3.curveStepAfter)
            chartBody.selectAll('.balance-area').attr('d', newBalanceArea)

            // Update Earning Bars
            chartBody
              .selectAll('.earning-bar')
              .attr('x', (d) => getZoomedX(d.date) - 4 / 2) // barWidth = 4

            // Update Transfer Lines
            chartBody
              .selectAll('.transfer-line')
              .attr('x1', (d) => getZoomedX(d.cx_date))
              .attr('x2', (d) => getZoomedX(d.cx_date))

            // Update Event Groups
            chartBody
              .selectAll('.event-group')
              .attr('transform', (d) => `translate(${getZoomedX(d.date)}, 0)`)
          }
        })

      rootSvg.call(zoom)
      
      this._chartState = {
        earliestDate,
        snapshotDate,
        xScale,
        zoom,
        rootSvg,
        yScale,
        sortedUsers,
        eventBoxPadding,
        margin,
        innerWidth,
        innerHeight
      }
    },
    syncTimeWindow() {
      if (!this.syncTargetTimeWindow || this.syncTargetTimeWindow.length !== 2) return
      if (!this._chartState) return
      
      const { earliestDate, snapshotDate, xScale, zoom, rootSvg } = this._chartState
      const [targetMinDate, targetMaxDate] = this.syncTargetTimeWindow
      
      const targetMinTs = targetMinDate.getTime()
      const targetMaxTs = targetMaxDate.getTime()
      const origMinTs = earliestDate.getTime()
      const origMaxTs = snapshotDate.getTime()
      
      const origSpan = origMaxTs - origMinTs
      const targetSpan = targetMaxTs - targetMinTs
      
      if (targetSpan <= 0 || origSpan <= 0) return

      let k = origSpan / targetSpan
      if (k > 50) k = 50
      if (k < 1) k = 1

      // When scaled by k, the range maps [origMinTs, origMaxTs] to [0, width * k]
      // We want targetMinTs to map to x=0.
      // In original scale, targetMinTs is at xScale(targetMinDate).
      // Under zoom identity translated by tx and scaled by k:
      // newX = k * origX + tx. We want newX = 0 when origX = xScale(targetMinDate).
      // So tx = -k * xScale(targetMinDate)
      const tx = -k * xScale(new Date(targetMinTs))

      const transform = d3.zoomIdentity.translate(tx, 0).scale(k)
      
      rootSvg.transition().duration(750)
        .call(zoom.transform, transform)
    }
  },
}
</script>

<style scoped>
.action-btn {
    background: #f8fafc;
    color: #4a5568;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
}
.action-btn:hover:not(:disabled) {
    background: #edf2f7;
    border-color: #cbd5e1;
    color: #2d3748;
}
.action-btn:disabled {
    cursor: not-allowed;
    background: #f1f5f9;
    color: #94a3b8;
    opacity: 0.6;
}

.behavior-details-container {
  width: 100%;
  height: 100%;
  padding: 10px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.empty-state, .loading, .empty-data {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #a0aec0;
  font-size: 14px;
  font-style: italic;
}

.details-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-id {
  margin: 0;
  font-size: 14px;
  color: #2d3748;
  word-break: break-all;
}

.entity-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.entity-badge {
  background-color: #ebf4ff;
  color: #3182ce;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.entity-members {
  font-size: 12px;
  color: #718096;
}

.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 32px;
  height: 18px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #e2e8f0;
  transition: .3s;
  border-radius: 18px;
  border: 1px solid #cbd5e1;
}

.slider:before {
  position: absolute;
  content: "";
  height: 12px;
  width: 12px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

input:checked + .slider {
  background-color: #4a5568;
  border-color: #4a5568;
}

input:checked + .slider:before {
  transform: translateX(14px);
}

.toggle-text {
  font-size: 12px;
  color: #4a5568;
  font-weight: 500;
  user-select: none;
}

.data-view {
  flex: 1;
  overflow: hidden;
}

.behavior-list {
  height: 100%;
  overflow: hidden;
}

.debug-data {
  font-size: 11px;
  background: #f7fafc;
  padding: 8px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #4a5568;
}

.custom-tooltip {
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #2d3748;
  pointer-events: none;
  z-index: 1000;
  max-width: 250px;
  transition: opacity 0.2s ease;
}
</style>
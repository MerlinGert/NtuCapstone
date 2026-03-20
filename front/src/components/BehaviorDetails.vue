<template>
  <div class="behavior-details-container" ref="container">
    <div v-if="!selectedUser" class="empty-state">
      Please select a user node to view behavior details.
    </div>
    <div v-else class="details-content">
      <div class="header">
        <h3 class="user-id">User: {{ selectedUser }}</h3>
        <div v-if="entityInfo" class="entity-info">
          <span class="entity-badge">Part of Entity</span>
          <span class="entity-members">Members: {{ entityInfo.users.length }}</span>
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
  </div>
</template>

<script>
import * as d3 from 'd3';

export default {
  name: 'BehaviorDetails',
  props: {
    selectedUser: {
      type: String,
      default: null
    },
    behaviorData: {
      type: Object,
      default: () => null
    },
    entityInfo: {
      type: Object,
      default: () => null
    },
    snapshotTime: {
      type: String,
      default: null
    },
    manipulationResults: {
      type: Array,
      default: () => []
    }
  },
  watch: {
    behaviorData: {
      handler(newVal) {
        if (newVal && Object.keys(newVal).length > 0) {
          this.$nextTick(() => {
            this.drawChart();
          });
        }
      },
      deep: true
    },
    manipulationResults: {
      handler() {
        this.$nextTick(() => {
          this.drawChart();
        });
      },
      deep: true
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize);
    if (this.behaviorData && Object.keys(this.behaviorData).length > 0) {
      this.drawChart();
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    handleResize() {
      if (this.behaviorData && Object.keys(this.behaviorData).length > 0) {
        this.drawChart();
      }
    },
    drawChart() {
      const container = this.$refs.chartContainer;
      if (!container) return;

      // Clear previous chart (only remove svg, keep the tooltip div)
      d3.select(container).selectAll('svg').remove();

      // Sort users: selectedUser in the middle, entity users adjacent, then other users
      const users = Object.keys(this.behaviorData);
      
      const entityUsers = this.entityInfo ? this.entityInfo.users.filter(u => u !== this.selectedUser && users.includes(u)) : [];
      const otherUsers = users.filter(u => u !== this.selectedUser && !entityUsers.includes(u));
      
      // Balance users to keep selectedUser in the center
      let topHalf = [];
      let bottomHalf = [];
      
      // Distribute entity users closely around the selected user
      entityUsers.forEach(u => {
        if (topHalf.length <= bottomHalf.length) {
          topHalf.push(u); // Add to end of topHalf (will be closest to center after reversal)
        } else {
          bottomHalf.push(u); // Add to start of bottomHalf (closest to center)
        }
      });
      
      // Distribute other users further outwards
      otherUsers.forEach(u => {
        if (topHalf.length <= bottomHalf.length) {
          topHalf.push(u);
        } else {
          bottomHalf.push(u);
        }
      });
      
      // Reverse topHalf so the first elements added (entity users) are closest to the middle
      topHalf.reverse();
      
      const sortedUsers = [...topHalf, this.selectedUser, ...bottomHalf];

      // Filter behavior data based on snapshot time
      const snapshotDate = this.snapshotTime ? new Date(this.snapshotTime) : new Date();
      let earliestDate = snapshotDate;
      let hasData = false;

      const filteredData = {};
      const sequenceData = {}; // Store continuous balance and earning_usd sequences

      sortedUsers.forEach(user => {
        const events = this.behaviorData[user] || [];
        const validEvents = events.filter(event => {
          if (!event.timestamp) return false;
          const eventDate = new Date(event.timestamp);
          return eventDate <= snapshotDate;
        });
        
        filteredData[user] = validEvents;
        
        let currentBalance = 0;
        let avgBuyPrice = 0;
        const seq = [];
        const earningEvents = []; // Store discrete earning events for selling
        
        validEvents.forEach(event => {
          const eventDate = new Date(event.timestamp);
          if (eventDate < earliestDate) {
            earliestDate = eventDate;
          }
          hasData = true;
          
          let earningChange = 0;
          event._prevBalance = currentBalance;

          // Update balance based on event type
          if (event.type === 'transfer_in') {
            currentBalance += parseFloat(event.amount) || 0;
          } else if (event.type === 'transfer_out') {
            currentBalance -= parseFloat(event.amount) || 0;
          }
          
          event._currentBalance = currentBalance;
          
          if (event.isTrade && event.trade_info) {
            const isBuy = event.trade_info.action === 'buy';
            const amt = parseFloat(event.amount) || 0;
            const price = parseFloat(event.trade_info.price_usd) || 0;
            
            if (isBuy) {
              // Update Weighted Average Buy Price (WABP)
              if (currentBalance < 0) {
                avgBuyPrice = price;
              } else {
                const totalCost = (currentBalance * avgBuyPrice) + (amt * price);
                if (currentBalance + amt > 0) {
                  avgBuyPrice = totalCost / (currentBalance + amt);
                }
              }
            } else {
              // Calculate Earning on Sell: (Sell Price - WABP) * Sell Amount
              earningChange = (price - avgBuyPrice) * amt;
              if (earningChange !== 0) {
                earningEvents.push({
                  date: eventDate,
                  earning: earningChange
                });
              }
            }
          }
          
          seq.push({
            date: eventDate,
            balance: currentBalance,
          });
        });
        
        // Add a final point at snapshotDate to extend the area chart to the right edge
        if (seq.length > 0) {
            seq.push({
                date: snapshotDate,
                balance: currentBalance,
            });
        }
        
        sequenceData[user] = { seq, earningEvents };
      });

      // Set up dimensions
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 400;
      const margin = { top: 30, right: 20, bottom: 10, left: 40 }; // Adjusted top margin for top axis
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      // Create SVG
      const rootSvg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      // Define clip path
      const defs = rootSvg.append('defs');
      defs.append('clipPath')
        .attr('id', 'chart-clip')
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight);

      // We append a background rect to capture zoom events
      const zoomRect = rootSvg.append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight)
        .attr('transform', `translate(${margin.left},${margin.top})`)
        .style('fill', 'none')
        .style('pointer-events', 'all');

      const svg = rootSvg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
        
      const chartBody = svg.append('g')
        .attr('clip-path', 'url(#chart-clip)');

      // Y Scale for users (evenly distributed)
      const yScale = d3.scalePoint()
        .domain(sortedUsers)
        .range([0, innerHeight])
        .padding(0.5);

      // X Scale for time
      const xScale = d3.scaleTime()
        .domain([earliestDate, snapshotDate])
        .range([0, innerWidth]);

      // X Axis
      const xAxis = d3.axisTop(xScale);
      const xAxisGroup = svg.append('g')
        .attr('class', 'x-axis')
        .call(xAxis);

      // Define padding for event elements (half the height of a red box)
      const eventBoxPadding = 6;

      // Create a group for background elements (baselines, area charts, earning bars)
      const backgroundGroup = chartBody.append('g').attr('class', 'background-group');

      // Draw horizontal baselines for each user
      // Balance baseline (bottom boundary of balance)
      backgroundGroup.selectAll('.balance-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'balance-baseline')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', d => yScale(d) - eventBoxPadding)
        .attr('y2', d => yScale(d) - eventBoxPadding)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 1);

      // Earning baseline (top boundary of earning)
      backgroundGroup.selectAll('.earning-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'earning-baseline')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', d => yScale(d) + eventBoxPadding)
        .attr('y2', d => yScale(d) + eventBoxPadding)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 1);

      // Create a group for foreground elements (manipulation boxes, points, transfer lines)
      const foregroundGroup = chartBody.append('g').attr('class', 'foreground-group');

      // Draw Manipulation Bounding Boxes
      if (this.manipulationResults && this.manipulationResults.length > 0) {
        this.manipulationResults.forEach(result => {
          if (!result.participants || !result.manipulation_time || result.manipulation_time.length === 0) return;
          
          const involvedUsers = sortedUsers.filter(u => result.participants.includes(u));
          if (involvedUsers.length === 0) return;
          
          // Find time window
          let startStr = result.manipulation_time[0];
          let endStr = result.manipulation_time.length > 1 ? result.manipulation_time[1] : startStr;
          
          // Ensure time strings have UTC to match other timestamps
          if (!startStr.endsWith('UTC')) startStr += ' UTC';
          if (!endStr.endsWith('UTC')) endStr += ' UTC';
          
          let startTs = new Date(startStr);
          let endTs = new Date(endStr);
          
          if (isNaN(startTs) || isNaN(endTs)) return;
          
          let x1 = xScale(startTs);
          let x2 = xScale(endTs);
          
          // Ensure min width if it's a single point or very short
          if (x2 - x1 < 10) {
             const center = (x1 + x2) / 2;
             x1 = center - 5;
             x2 = center + 5;
          }
          
          // Format tooltip details
          let tooltipHtml = `<strong>Method:</strong> ${result.detection_method}<br>`;
          if (result.participants && result.participants.length > 1) {
            tooltipHtml += `<strong>Type:</strong> Entity-based (across ${result.participants.length} users)<br>`;
          }
          tooltipHtml += `<strong>Time:</strong> ${startStr} - ${endStr}<br>`;
          
          if (result.features) {
            tooltipHtml += `<ul style="margin: 4px 0; padding-left: 16px;">`;
            Object.entries(result.features).forEach(([key, value]) => {
              if (typeof value === 'number') {
                tooltipHtml += `<li><strong>${key}:</strong> ${value.toFixed(2)}</li>`;
              } else {
                tooltipHtml += `<li><strong>${key}:</strong> ${value}</li>`;
              }
            });
            tooltipHtml += `</ul>`;
          }
          if (result.transactions) {
            tooltipHtml += `<strong>Transactions count:</strong> ${result.transactions.length}`;
          }

          const self = this;

          // Draw separate boxes for each involved user
          involvedUsers.forEach(user => {
            const height = eventBoxPadding * 2;
            const y = yScale(user) - eventBoxPadding;

            foregroundGroup.append('rect')
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
              .on('mouseover', function(event) {
                  d3.select(this).attr('fill', 'rgba(255, 0, 0, 0.15)');
                  const tooltip = self.$refs.tooltip;
                  tooltip.innerHTML = tooltipHtml;
                  tooltip.style.display = "block";
                  tooltip.style.opacity = 1;
                  
                  // Position relative to chart container
                  const [mx, my] = d3.pointer(event, self.$refs.chartContainer);
                  tooltip.style.left = (mx + 15) + "px";
                  tooltip.style.top = (my + 15) + "px";
              })
              .on('mousemove', function(event) {
                  const tooltip = self.$refs.tooltip;
                  const [mx, my] = d3.pointer(event, self.$refs.chartContainer);
                  
                  // Adjust position to prevent tooltip from going off-screen
                  const containerWidth = self.$refs.chartContainer.clientWidth;
                  const tooltipWidth = tooltip.offsetWidth;
                  let left = mx + 15;
                  if (left + tooltipWidth > containerWidth) {
                      left = mx - tooltipWidth - 10;
                  }
                  
                  tooltip.style.left = left + "px";
                  tooltip.style.top = (my + 15) + "px";
              })
              .on('mouseout', function() {
                  d3.select(this).attr('fill', 'rgba(255, 0, 0, 0.05)');
                  const tooltip = self.$refs.tooltip;
                  tooltip.style.opacity = 0;
                  tooltip.style.display = "none";
              });
          });
        });
      }

      // Draw Entity Bounding Box if applicable
        if (this.entityInfo && this.entityInfo.users && this.entityInfo.users.length > 0) {
          const entityUsersInView = sortedUsers.filter(u => this.entityInfo.users.includes(u));
          if (entityUsersInView.length > 0) {
            const yPositions = entityUsersInView.map(u => yScale(u));
            const minY = Math.min(...yPositions);
            const maxY = Math.max(...yPositions);
            const boxPadding = 12; // padding around the text
            const boxWidth = 32; // approximate width of the truncated text
            
            svg.append('rect')
              .attr('x', -margin.left + 5) // Shifted right slightly
              .attr('y', minY - boxPadding)
              .attr('width', boxWidth)
              .attr('height', maxY - minY + (boxPadding * 2))
              .attr('fill', 'none')
              .attr('stroke', '#ff9800')
              .attr('stroke-width', 2)
              .attr('stroke-dasharray', '5,5')
              .attr('rx', 4)
              .attr('ry', 4);
          }
        }

        // Draw user labels
        svg.selectAll('.user-label')
          .data(sortedUsers)
          .enter()
          .append('text')
          .attr('class', 'user-label')
          .attr('x', -5) // Text anchor is 'end', so this is the right edge of the text
        .attr('y', d => yScale(d))
        .attr('dy', '0.32em')
        .attr('text-anchor', 'end')
        .attr('fill', d => {
          if (d === this.selectedUser) return '#2d3748';
          if (entityUsers.includes(d)) return '#3182ce';
          return '#718096';
        })
        .attr('font-weight', d => d === this.selectedUser ? 'bold' : 'normal')
        .attr('font-size', '11px')
        .text(d => d.substring(0, 3) + '..');
        
      // Add tooltip for full addresses
      svg.selectAll('.user-label')
        .append('title')
        .text(d => {
          let type = 'Related User';
          if (d === this.selectedUser) type = 'Selected User';
          else if (entityUsers.includes(d)) type = 'Entity Member';
          return `${type}: ${d}`;
        });

      // Draw behavior points and area charts
      let balanceScale;
      if (hasData) {
        // Find global max/min for scales
        let maxBalance = 0;
        let maxAbsEarning = 0;
        
        Object.values(sequenceData).forEach(data => {
          data.seq.forEach(d => {
            if (d.balance > maxBalance) maxBalance = d.balance;
          });
          data.earningEvents.forEach(d => {
            if (Math.abs(d.earning) > maxAbsEarning) maxAbsEarning = Math.abs(d.earning);
          });
        });

        // We want the area chart to fit within the row height (distance between user lines)
        // Set maximum area height to 1/2 of the row spacing
        const rowHeight = yScale.step();
        const maxAreaHeight = rowHeight * 0.5;

        balanceScale = d3.scaleLinear()
          .domain([0, maxBalance || 1])
          .range([0, -maxAreaHeight]); // Upwards (negative y)

        const earningScale = d3.scaleLinear()
          .domain([0, maxAbsEarning || 1])
          .range([0, maxAreaHeight]); // Downwards (positive y)

        const balanceArea = d3.area()
          .x(d => xScale(d.date))
          .y0(-eventBoxPadding)
          .y1(d => balanceScale(d.balance) - eventBoxPadding)
          .curve(d3.curveStepAfter);

        // Prepare transfer line marker
        defs.append('marker')
          .attr('id', 'transfer-arrow')
          .attr('viewBox', '0 -5 10 10')
          .attr('refX', 12)
          .attr('refY', 0)
          .attr('markerWidth', 6)
          .attr('markerHeight', 6)
          .attr('orient', 'auto')
          .append('path')
          .attr('d', 'M0,-5L10,0L0,5')
          .attr('fill', '#A0AEC0');

        const transferLinesGroup = foregroundGroup.append('g').attr('class', 'transfer-lines');

        sortedUsers.forEach(user => {
          const events = filteredData[user] || [];
          const { seq, earningEvents } = sequenceData[user] || { seq: [], earningEvents: [] };
          
          const userBackgroundGroup = backgroundGroup.append('g')
            .attr('class', 'user-background')
            .attr('transform', `translate(0, ${yScale(user)})`);

          const userForegroundGroup = foregroundGroup.append('g')
            .attr('class', 'user-foreground')
            .attr('transform', `translate(0, ${yScale(user)})`);
            
          // Draw Area Charts and Bars first so they are behind the points
          if (seq.length > 0) {
            // Balance Area (Above line)
            userBackgroundGroup.append('path')
              .datum(seq)
              .attr('class', 'balance-area')
              .attr('fill', '#90cdf4')
              .attr('opacity', 0.4)
              .attr('d', balanceArea);
          }

          // Draw Discrete Earning Bars (Below line)
          if (earningEvents.length > 0) {
            const barWidth = 4; // Fixed width for discrete events
            userBackgroundGroup.selectAll('.earning-bar')
              .data(earningEvents)
              .enter()
              .append('rect')
              .attr('class', 'earning-bar')
              .attr('x', d => xScale(d.date) - barWidth / 2)
              .attr('y', eventBoxPadding)
              .attr('width', barWidth)
              .attr('height', d => earningScale(Math.abs(d.earning)))
              .attr('fill', d => d.earning >= 0 ? '#68d391' : '#fc8181') // Green for profit, Red for loss
              .attr('opacity', 0.8)
              .append('title') // Add simple tooltip
              .text(d => `Earning: $${d.earning.toFixed(2)}`);
          }
            
          events.forEach(event => {
            const eventDate = new Date(event.timestamp);
            const cx = xScale(eventDate);
            
            if (!event.isTrade) {
              const isOut = event.type === 'transfer_out';
              const counterpartyInView = sortedUsers.includes(event.counterparty);
              
              // Only draw lines if it's an internal transfer between users in the current view
              if (isOut && counterpartyInView && user !== event.counterparty) {
                const startY = yScale(user);
                const endY = yScale(event.counterparty);
                
                transferLinesGroup.append('line')
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
                  .text(`Transfer ${event.amount} to ${event.counterparty}`);
              }
            }

            const eventGroup = userForegroundGroup.append('g')
              .datum({ date: eventDate })
              .attr('class', 'event-group')
              .attr('transform', `translate(${cx}, 0)`);
              
            let circleColor = '#A0AEC0'; // default grey for transfers
            let tooltipText = '';
            
            if (event.isTrade) {
              const isBuy = event.trade_info && event.trade_info.action === 'buy';
              circleColor = isBuy ? '#4299e1' : '#ed64a6'; // blue for buy, pink for sell
              tooltipText = `${isBuy ? 'Buy' : 'Sell'}: ${event.amount} @ $${parseFloat(event.trade_info?.price_usd || 0).toFixed(4)}`;
              
              const y1 = balanceScale(event._prevBalance || 0) - eventBoxPadding;
              const y2 = balanceScale(event._currentBalance || 0) - eventBoxPadding;
              
              // Draw balance difference bar
              eventGroup.append('line')
                .attr('x1', 0)
                .attr('x2', 0)
                .attr('y1', y1)
                .attr('y2', y2)
                .attr('stroke', circleColor)
                .attr('stroke-width', 4)
                .attr('opacity', 0.8)
                .append('title')
                .text(`Balance change: ${Math.abs(event._currentBalance - event._prevBalance)}`);
                
            } else {
              const isTransferIn = event.type === 'transfer_in';
              tooltipText = `${isTransferIn ? 'Transfer In' : 'Transfer Out'}: ${event.amount}`;
            }

            eventGroup.append('circle')
              .attr('r', 2)
              .attr('cy', 0)
              .attr('fill', circleColor)
              .append('title')
              .text(tooltipText);
          });
        });
      }

      // Setup Zoom
      const zoom = d3.zoom()
        .scaleExtent([1, 50])
        .translateExtent([[0, 0], [innerWidth, innerHeight]])
        .extent([[0, 0], [innerWidth, innerHeight]])
        .on('zoom', (event) => {
          const newXScale = event.transform.rescaleX(xScale);
          
          // Update X Axis
          xAxisGroup.call(xAxis.scale(newXScale));

          // Update Manipulation Boxes
          chartBody.selectAll('.manipulation-box')
            .attr('x', d => {
              let x1 = newXScale(d.startTs);
              let x2 = newXScale(d.endTs);
              if (x2 - x1 < 10) return (x1 + x2) / 2 - 5;
              return x1;
            })
            .attr('width', d => {
              let x1 = newXScale(d.startTs);
              let x2 = newXScale(d.endTs);
              if (x2 - x1 < 10) return 10;
              return x2 - x1;
            });

          if (hasData && balanceScale) {
            // Update Balance Area
            const newBalanceArea = d3.area()
              .x(d => newXScale(d.date))
              .y0(-eventBoxPadding)
              .y1(d => balanceScale(d.balance) - eventBoxPadding)
              .curve(d3.curveStepAfter);
            chartBody.selectAll('.balance-area').attr('d', newBalanceArea);

            // Update Earning Bars
            chartBody.selectAll('.earning-bar')
              .attr('x', d => newXScale(d.date) - 4 / 2); // barWidth = 4

            // Update Transfer Lines
            chartBody.selectAll('.transfer-line')
              .attr('x1', d => newXScale(d.cx_date))
              .attr('x2', d => newXScale(d.cx_date));

            // Update Event Groups
            chartBody.selectAll('.event-group')
              .attr('transform', d => `translate(${newXScale(d.date)}, 0)`);
          }
        });

      zoomRect.call(zoom);
    }
  }
}
</script>

<style scoped>
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
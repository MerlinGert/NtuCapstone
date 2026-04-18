<template>
  <div class="behavior-snapshot-container">
    <div class="header">
      <h2>Behavior Snapshot — {{ snapshotData.time || 'N/A' }}</h2>
      <span v-if="selectedCount > 0" class="selection-badge">{{ selectedCount }} selected</span>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>

    <!-- Visualization area -->
    <div class="vis-area" ref="svgContainer">
      <svg ref="snapshotSvg"></svg>
      <!-- ezio: preserved hover tooltip from snapshot -->
      <div v-if="snapshotData.hoveredElement" ref="hoverTooltip"
          class="snapshot-tooltip" :style="tooltipStyle"
          v-html="snapshotData.hoveredElement.tooltipHtml"></div>
      <canvas ref="sketchCanvas" class="lasso-overlay"
          :class="'cursor-' + activeTool"></canvas>
      <!-- ezio: toolbar component -->
      <SnapshotToolbar class="floating-toolbar"
          :tool="activeTool" :color="penColor"
          @update:tool="activeTool = $event"
          @update:color="penColor = $event"
          @clear="clearSketches" />
    </div>

    <!-- Selected items details panel -->
    <div class="details-panel">
      <div class="details-header" @click="detailsOpen = !detailsOpen">
        <span>{{ detailsOpen ? '▼' : '▶' }} Selected Items Details</span>
        <span class="details-count" v-if="selectedItems.length > 0">({{ selectedItems.length }})</span>
      </div>
      <div v-if="detailsOpen" class="details-body">
        <div v-if="selectedItems.length === 0" class="details-empty">
          Switch to Select tool and click on user tracks or event circles.
        </div>
        <table v-else class="details-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>User</th>
              <th>Time</th>
              <th>Amount</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in selectedItems" :key="idx">
              <td>
                <span :class="'type-tag type-' + item.type">{{ item.label }}</span>
              </td>
              <td class="addr">{{ truncAddr(item.user) }}</td>
              <td>{{ item.timestamp || '—' }}</td>
              <td>{{ item.amount != null ? Number(item.amount).toLocaleString() : '—' }}</td>
              <td>{{ item.details || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Text input area -->
    <div class="input-area">
      <input
        type="text"
        v-model="inputText"
        placeholder="Enter annotation text..."
        @keyup.enter="handleInput"
        class="text-input"
      />
      <button @click="handleInput" class="send-btn">Annotate</button>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3';
// ezio: toolbar component
import SnapshotToolbar from './SnapshotToolbar.vue';

export default {
  name: 'BehaviorSnapshot',
  components: { SnapshotToolbar },
  props: {
    snapshotData: { type: Object, required: true }
  },
  // ezio: added 'operation' emit for operation recording
  emits: ['close', 'snapshot-input', 'operation'],
  data() {
    return {
      selectedCount: 0,
      selectedItems: [],
      detailsOpen: true,
      inputText: '',
      // ezio: toolbar state
      activeTool: 'select',
      penColor: 'rgba(255,60,60,0.7)',
      sketchStrokes: [],
      // ezio: operation recording
      operationLog: [],
      // ezio: hover tooltip position for snapshot
      tooltipLeft: 0,
      tooltipTop: 0,
      tooltipReady: false,
    };
  },
  // ezio: computed tooltip position for hovered element
  computed: {
    tooltipStyle() {
      if (!this.tooltipReady) return { display: 'none' };
      return {
        left: this.tooltipLeft + 'px',
        top: this.tooltipTop + 'px',
      };
    }
  },
  watch: {
    activeTool() {
      this.redrawCanvas();
    }
  },
  mounted() {
    // ezio: initialize instance-level state
    this._selectableItems = [];
    this._itemsByKey = new Map();
    this._selectedSet = new Set();
    this._currentTransform = d3.zoomIdentity;
    this._opSeqId = 0;

    this.$nextTick(() => {
      this.renderSnapshot();
      this.setupInteraction();
      // ezio: [3/3 DetailSnapshot initial state] apply zoom transform from BehaviorDetails so snapshot matches detail view
      // ezio: rescale translate-x by width ratio so zoom maps correctly to the resized snapshot
      if (this.snapshotData.initialZoom && this._zoom && this._zoomRect) {
        const iz = this.snapshotData.initialZoom;
        const origW = this.snapshotData.originalWidth;
        const snapW = this._innerWidth;
        const scaleRatio = origW && snapW ? (snapW / origW) : 1;
        const t = d3.zoomIdentity.translate(iz.x * scaleRatio, iz.y).scale(iz.k);
        this._zoomRect.call(this._zoom.transform, t);
      }
    });
  },
  methods: {
    truncAddr(addr) {
      if (!addr) return '—';
      if (addr.length <= 10) return addr;
      return addr.substring(0, 6) + '...' + addr.substring(addr.length - 4);
    },

    // ezio: operation recording method
    recordOperation(type, payload) {
      const entry = {
        id: this._opSeqId++,
        timestamp: Date.now(),
        type,
        payload: JSON.parse(JSON.stringify(payload))
      };
      this.operationLog.push(entry);
      this.$emit('operation', entry);
      return entry;
    },

    // ezio: allow empty text; capture full screenshot (SVG + sketch canvas composited)
    handleInput() {
      const svgEl = this.$refs.snapshotSvg;
      const sketchCanvas = this.$refs.sketchCanvas;
      const container = this.$refs.svgContainer;
      const w = container ? container.offsetWidth : 800;
      const h = container ? container.offsetHeight : 400;
      const inputText = this.inputText;
      const selectedItems = this.selectedItems.map(i => ({ type: i.type, user: i.user, key: i.key }));
      const operationLog = [...this.operationLog];

      // ezio: helper to emit and reset
      const emitResult = (dataUrl) => {
        this.$emit('snapshot-input', {
          text: inputText,
          selectedItems,
          sketchDataUrl: dataUrl,
          operationLog
        });
        this.inputText = '';
        // ezio: close snapshot window after annotate
        this.$emit('close');
      };

      // ezio: composite SVG + sketch canvas into one image
      if (svgEl) {
        const svgData = new XMLSerializer().serializeToString(svgEl);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);
        const img = new Image();
        img.onload = () => {
          const c = document.createElement('canvas');
          c.width = w;
          c.height = h;
          const ctx = c.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, w, h);
          ctx.drawImage(img, 0, 0, w, h);
          URL.revokeObjectURL(url);
          if (sketchCanvas) ctx.drawImage(sketchCanvas, 0, 0);
          emitResult(c.toDataURL());
        };
        img.onerror = () => {
          URL.revokeObjectURL(url);
          emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null);
        };
        img.src = url;
      } else {
        emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null);
      }
    },

    clearSketches() {
      this.sketchStrokes = [];
      this.redrawCanvas();
      // ezio: record clear-sketches operation
      this.recordOperation('clear-sketches', {});
    },

    // ezio: redrawCanvas now applies zoom transform to sketch coordinates
    redrawCanvas() {
      const canvas = this.$refs.sketchCanvas;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const t = this._currentTransform;
      const margin = this._margin || { left: 40 };
      // Redraw all persistent strokes and rects with zoom-adjusted X coordinates
      this.sketchStrokes.forEach(stroke => {
        ctx.strokeStyle = stroke.color;
        ctx.lineWidth = stroke.width;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.setLineDash([]);
        // ezio: dispatch on type — rect vs freehand stroke
        if (stroke.type === 'rect') {
          const screenX = t.applyX(stroke.x - margin.left) + margin.left;
          const screenX2 = t.applyX((stroke.x + stroke.w) - margin.left) + margin.left;
          const screenW = screenX2 - screenX;
          ctx.beginPath();
          ctx.rect(screenX, stroke.y, screenW, stroke.h);
          ctx.stroke();
        } else {
          if (stroke.points.length < 2) return;
          ctx.beginPath();
          // ezio: convert data-space X back to screen-space using current zoom transform
          const sx = stroke.points[0][0];
          const sy = stroke.points[0][1];
          const screenX0 = t.applyX(sx - margin.left) + margin.left;
          ctx.moveTo(screenX0, sy);
          for (let i = 1; i < stroke.points.length; i++) {
            const px = stroke.points[i][0];
            const py = stroke.points[i][1];
            const screenX = t.applyX(px - margin.left) + margin.left;
            ctx.lineTo(screenX, py);
          }
          ctx.stroke();
        }
      });
    },

    // ezio: hit detection - promoted from setupInteraction closure
    _findClickedItem(x, y) {
      // Priority 1: event circles (closest within 15px)
      let bestEvent = null;
      let bestEventDist = Infinity;
      this._selectableItems.forEach(item => {
        if (item.type === 'event') {
          const dist = Math.hypot(x - item.screenX, y - item.screenY);
          if (dist < bestEventDist) {
            bestEventDist = dist;
            bestEvent = item;
          }
        }
      });
      if (bestEvent && bestEventDist < 15) return bestEvent;

      // Priority 2: user tracks (click within track rectangle)
      for (const item of this._selectableItems) {
        if (item.type === 'user-track') {
          if (x >= item.screenX && x <= item.screenX + item.screenWidth &&
              y >= item.screenY && y <= item.screenY + item.screenHeight) {
            return item;
          }
        }
      }
      return null;
    },

    // ezio: highlight update - promoted from setupInteraction closure
    _updateHighlight() {
      const vm = this;
      const selectedSet = this._selectedSet;
      const svg = d3.select(vm.$refs.snapshotSvg);

      // Reset all elements to default style
      svg.selectAll('.event-circle').each(function() {
        const el = d3.select(this);
        const origColor = el.attr('fill');
        const user = el.attr('data-user');
        const evtIdx = el.attr('data-event-idx');
        const item = vm._itemsByKey.get(`event:${user}:${evtIdx}`);
        el.attr('opacity', 0.6)
          .attr('stroke', d3.color(origColor).darker(0.8))
          .attr('stroke-width', 0.5);
        if (item) el.attr('r', item.radius);
      });
      svg.selectAll('.user-label')
        .attr('font-weight', d => d === vm.snapshotData.selectedUser ? 'bold' : 'normal')
        .style('fill', null);

      // Highlight selected elements
      if (selectedSet.size > 0) {
        // Highlight selected user tracks
        selectedSet.forEach(key => {
          if (key.startsWith('track:')) {
            const user = key.substring(6);
            svg.selectAll('.user-label').filter(d => d === user)
              .attr('font-weight', 'bold')
              .style('fill', '#e53e3e');
          }
        });

        // Highlight selected event circles
        selectedSet.forEach(key => {
          if (key.startsWith('event:')) {
            const parts = key.split(':');
            const user = parts[1];
            const evtIdx = parts[2];
            const item = vm._itemsByKey.get(key);
            const highlightR = item ? item.radius + 2 : 4;
            svg.selectAll('.event-circle').filter(function() {
              return d3.select(this).attr('data-user') === user &&
                     d3.select(this).attr('data-event-idx') === evtIdx;
            })
              .attr('opacity', 1.0)
              .attr('stroke', '#fdd835')
              .attr('stroke-width', 3)
              .attr('r', highlightR);
          }
        });
      }

      // Sync Vue state
      vm.selectedItems = Array.from(selectedSet).map(k => vm._itemsByKey.get(k)).filter(Boolean);
      vm.selectedCount = vm.selectedItems.length;
    },

    // ezio: zoom handler
    handleZoom(event) {
      const newXScale = event.transform.rescaleX(this._xScale);
      this._currentTransform = event.transform;

      const chartBody = d3.select(this.$refs.snapshotSvg).select('.chart-body');
      const svg = d3.select(this.$refs.snapshotSvg).select('g');

      // Update x-axis
      svg.select('.x-axis').call(d3.axisTop(newXScale));

      const data = this.snapshotData;
      const xScale = this._xScale;

      const getZoomedX = (dateObj) => {
        if (!dateObj || isNaN(dateObj.getTime())) return 0;
        const ts = dateObj.getTime();
        
        if (data.useSequentialTime && xScale.timeToIndex) {
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

      // Update balance areas
      const ep = this._eventBoxPadding;
      const bs = this._balanceScale;
      if (bs) {
        const newBalanceArea = d3.area()
          .x(d => getZoomedX(new Date(d.date)))
          .y0(-ep)
          .y1(d => bs(d.balance) - ep)
          .curve(d3.curveStepAfter);
        chartBody.selectAll('.balance-area').attr('d', newBalanceArea);
      }

      // Update earning bars
      chartBody.selectAll('.earning-bar')
        .attr('x', d => getZoomedX(new Date(d.date)) - 2);

      // Update transfer lines
      chartBody.selectAll('.transfer-line')
        .attr('x1', d => getZoomedX(d.cx_date))
        .attr('x2', d => getZoomedX(d.cx_date));

      // Update event groups
      chartBody.selectAll('.event-group')
        .attr('transform', d => `translate(${getZoomedX(d.date)}, 0)`);

      // Update manipulation boxes
      chartBody.selectAll('.manipulation-box')
        .attr('x', d => {
          let x1 = getZoomedX(d.startTs), x2 = getZoomedX(d.endTs);
          if (x2 - x1 < 10) {
             const center = (x1 + x2) / 2;
             x1 = center - 5;
             if (this.snapshotData.isFewUsers) x1 -= 6; // mimic sequential time logic from original chart if needed
             return x1;
          }
          if (this.snapshotData.isFewUsers) return x1 - 6; // sequential time offset
          return x1;
        })
        .attr('width', d => {
          let x1 = getZoomedX(d.startTs), x2 = getZoomedX(d.endTs);
          if (x2 - x1 < 10) {
             const center = (x1 + x2) / 2;
             x1 = center - 5;
             x2 = center + 5;
             if (this.snapshotData.isFewUsers) {
                x1 -= 6;
                x2 += 6;
             }
             return x2 - x1;
          }
          if (this.snapshotData.isFewUsers) return (x2 + 6) - (x1 - 6);
          return Math.max(10, x2 - x1);
        });

      // ezio: update selectable items' screen coordinates for hit detection
      const margin = this._margin;
      this._selectableItems.forEach(item => {
        if (item.type === 'event') {
          item.screenX = margin.left + getZoomedX(item._dataDate);
        }
        // user-track items span full width, screenX stays at margin.left
      });

      // ezio: redraw canvas sketches with updated zoom
      this.redrawCanvas();
    },

    renderSnapshot() {
      const data = this.snapshotData;
      if (!data) return;

      const container = this.$refs.svgContainer;

      // ezio: content-adaptive sizing — use original chart dimensions, scale down only if needed
      if (data.originalWidth && data.originalHeight) {
        const nonVisHeight = 330; // approx header + details + input + gaps + padding
        const maxW = window.innerWidth * 0.9 - 30;  // 90vw minus container padding
        const maxH = window.innerHeight * 0.9 - nonVisHeight; // 90vh minus non-vis chrome

        let visW = data.originalWidth;
        let visH = data.originalHeight;

        // scale down proportionally if original exceeds available space
        const scale = Math.min(1, maxW / visW, maxH / visH);
        visW = Math.round(visW * scale);
        visH = Math.round(visH * scale);

        container.style.width = visW + 'px';
        container.style.height = visH + 'px';
        container.style.flex = 'none';
      }

      const width = container.offsetWidth;
      const height = container.offsetHeight;
      const margin = { top: 30, right: 20, bottom: 10, left: 40 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const sortedUsers = data.sortedUsers;
      const filteredData = data.filteredData;
      const sequenceData = data.sequenceData;
      const entityUsers = data.entityUsers || [];
      const isFewUsers = data.isFewUsers;
      const eventBoxPadding = data.eventBoxPadding;

      // Reconstruct time domain
      const earliestDate = new Date(data.timeDomain[0]);
      const snapshotDate = new Date(data.timeDomain[1]);

      const timeToIndex = data.timeToIndex ? new Map(data.timeToIndex) : null;
      const sortedTimestamps = data.sortedTimestamps || [];

      // Create SVG
      const rootSvg = d3.select(this.$refs.snapshotSvg)
        .attr('width', width)
        .attr('height', height);
      rootSvg.selectAll('*').remove();

      // ezio: add defs with clip path for zoom
      const clipId = 'snapshot-clip-' + this._uid;
      const defs = rootSvg.append('defs');
      defs.append('clipPath')
        .attr('id', clipId)
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight);

      const svg = rootSvg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      // Y Scale
      const yScale = d3.scalePoint()
        .domain(sortedUsers)
        .range([0, innerHeight])
        .padding(0.5);

      // X Scale
      let xScale;
      if (data.useSequentialTime && timeToIndex) {
        xScale = d3.scaleLinear()
          .domain([0, sortedTimestamps.length - 1])
          .range([0, innerWidth]);
        xScale.timeToIndex = timeToIndex;
        xScale.sortedTimestamps = sortedTimestamps;
      } else {
        xScale = d3.scaleTime()
          .domain([earliestDate, snapshotDate])
          .range([0, innerWidth]);
      }

      // X Axis
      svg.append('g')
        .attr('class', 'x-axis')
        .call(d3.axisTop(xScale));

      // ezio: chart body with clip path for zoom
      const chartBody = svg.append('g')
        .attr('class', 'chart-body')
        .attr('clip-path', `url(#${clipId})`);

      // Background group — inside chartBody for clipping
      const backgroundGroup = chartBody.append('g').attr('class', 'background-group');

      // Helper function to get X coordinate regardless of scale type
      const getX = (dateObj) => {
        if (!dateObj || isNaN(dateObj.getTime())) return 0;
        const ts = dateObj.getTime();
        
        if (data.useSequentialTime && xScale.timeToIndex) {
          if (xScale.timeToIndex.has(ts)) {
            return xScale(xScale.timeToIndex.get(ts));
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
          return xScale(closestIdx);
        } else {
          return xScale(dateObj);
        }
      }

      // Draw baselines
      backgroundGroup.selectAll('.balance-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'balance-baseline')
        .attr('x1', 0).attr('x2', innerWidth)
        .attr('y1', d => yScale(d) - eventBoxPadding)
        .attr('y2', d => yScale(d) - eventBoxPadding)
        .attr('stroke', '#e2e8f0').attr('stroke-width', 1);

      backgroundGroup.selectAll('.earning-baseline')
        .data(sortedUsers)
        .enter()
        .append('line')
        .attr('class', 'earning-baseline')
        .attr('x1', 0).attr('x2', innerWidth)
        .attr('y1', d => yScale(d) + eventBoxPadding)
        .attr('y2', d => yScale(d) + eventBoxPadding)
        .attr('stroke', '#e2e8f0').attr('stroke-width', 1);

      // Foreground group — inside chartBody for clipping
      const foregroundGroup = chartBody.append('g').attr('class', 'foreground-group');

      // Draw Manipulation Boxes
      if (data.showManipulationBoxes && data.manipulationResults && data.manipulationResults.length > 0) {
        data.manipulationResults.forEach(result => {
          if (!result.participants || !result.manipulation_time || result.manipulation_time.length === 0) return;
          const involvedUsers = sortedUsers.filter(u => result.participants.includes(u));
          if (involvedUsers.length === 0) return;

          let startStr = result.manipulation_time[0];
          let endStr = result.manipulation_time.length > 1 ? result.manipulation_time[1] : startStr;
          if (!startStr.endsWith('UTC')) startStr += ' UTC';
          if (!endStr.endsWith('UTC')) endStr += ' UTC';

          let startTs = new Date(startStr);
          let endTs = new Date(endStr);
          if (isNaN(startTs) || isNaN(endTs)) return;

          let x1 = getX(startTs);
          let x2 = getX(endTs);
          if (x1 > x2) {
            const temp = x1;
            x1 = x2;
            x2 = temp;
          }
          if (x2 - x1 < 10) {
            const center = (x1 + x2) / 2;
            x1 = center - 5;
            x2 = center + 5;
            if (data.isFewUsers) {
               x1 -= 6;
               x2 += 6;
            }
          } else {
            if (data.isFewUsers) {
               x1 -= 6;
               x2 += 6;
            }
          }

          involvedUsers.forEach(user => {
            const boxHeight = eventBoxPadding * 2;
            const y = yScale(user) - eventBoxPadding;
            // ezio: added datum binding for zoom
            foregroundGroup.append('rect')
              .datum({ startTs, endTs })
              .attr('class', 'manipulation-box')
              .attr('x', x1).attr('y', y)
              .attr('width', x2 - x1).attr('height', boxHeight)
              .attr('fill', 'rgba(255, 0, 0, 0.05)')
              .attr('stroke', 'rgba(255, 0, 0, 0.6)')
              .attr('stroke-width', 1)
              .attr('rx', 4).attr('ry', 4);
          });
        });
      }

      // Draw Entity Bounding Box
      if (data.entityInfo && data.entityInfo.users && data.entityInfo.users.length > 0) {
        const entityUsersInView = sortedUsers.filter(u => data.entityInfo.users.includes(u));
        if (entityUsersInView.length > 0) {
          const yPositions = entityUsersInView.map(u => yScale(u));
          const minY = Math.min(...yPositions);
          const maxY = Math.max(...yPositions);
          const boxPadding = 12;
          const boxWidth = 32;
          svg.append('rect')
            .attr('x', -margin.left + 5)
            .attr('y', minY - boxPadding)
            .attr('width', boxWidth)
            .attr('height', maxY - minY + boxPadding * 2)
            .attr('fill', 'none')
            .attr('stroke', '#ff9800')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '5,5')
            .attr('rx', 4).attr('ry', 4);
        }
      }

      // Draw user labels
      svg.selectAll('.user-label')
        .data(sortedUsers)
        .enter()
        .append('text')
        .attr('class', 'user-label')
        .attr('x', -5)
        .attr('y', d => yScale(d))
        .attr('dy', '0.32em')
        .attr('text-anchor', 'end')
        .attr('fill', d => {
          if (d === data.selectedUser) return '#2d3748';
          if (entityUsers.includes(d)) return '#3182ce';
          return '#718096';
        })
        .attr('font-weight', d => d === data.selectedUser ? 'bold' : 'normal')
        .attr('font-size', '11px')
        .text(d => d.substring(0, 3) + '..');

      // Build selectable items array for click hit detection
      this._selectableItems = [];
      this._itemsByKey = new Map();

      // Add user tracks
      sortedUsers.forEach(user => {
        const userEvents = filteredData[user] || [];
        const isEntity = entityUsers.includes(user);
        const key = `track:${user}`;
        // ezio: screenX starts at 0 so clicking on the user label also selects the track
        const item = {
          type: 'user-track',
          key,
          user,
          screenX: 0,
          screenY: margin.top + yScale(user) - eventBoxPadding - 4,
          screenWidth: margin.left + innerWidth,
          screenHeight: eventBoxPadding * 2 + 8,
          label: 'Track',
          amount: null,
          timestamp: null,
          details: `${userEvents.length} events${isEntity ? ', entity member' : ''}${user === data.selectedUser ? ', selected user' : ''}`
        };
        this._selectableItems.push(item);
        this._itemsByKey.set(key, item);
      });

      // Draw behavior points and area charts
      let hasData = false;
      let maxBalance = 0;
      let maxAbsEarning = 0;

      Object.values(sequenceData).forEach(sd => {
        const seqArr = sd.seq || [];
        seqArr.forEach(d => {
          const bal = typeof d.balance === 'number' ? d.balance : d[1];
          if (bal > maxBalance) maxBalance = bal;
        });
        const earnArr = sd.earningEvents || [];
        earnArr.forEach(d => {
          const earn = typeof d.earning === 'number' ? d.earning : d[1];
          if (Math.abs(earn) > maxAbsEarning) maxAbsEarning = Math.abs(earn);
        });
        if (seqArr.length > 0) hasData = true;
      });

      if (hasData) {
        const rowHeight = yScale.step();
        const heightProportion = isFewUsers ? 0.3 : 0.5;
        const maxAreaHeight = rowHeight * heightProportion;

        const balanceScale = d3.scaleLinear()
          .domain([0, maxBalance || 1])
          .range([0, -maxAreaHeight]);

        const earningScale = d3.scaleLinear()
          .domain([0, maxAbsEarning || 1])
          .range([0, maxAreaHeight]);

        const balanceArea = d3.area()
          .x(d => getX(new Date(d.date)))
          .y0(-eventBoxPadding)
          .y1(d => balanceScale(d.balance) - eventBoxPadding)
          .curve(d3.curveStepAfter);

        // Arrow marker for transfer lines
        defs.append('marker')
          .attr('id', 'snapshot-transfer-arrow')
          .attr('viewBox', '0 -5 10 10')
          .attr('refX', 12).attr('refY', 0)
          .attr('markerWidth', 6).attr('markerHeight', 6)
          .attr('orient', 'auto')
          .append('path')
          .attr('d', 'M0,-5L10,0L0,5')
          .attr('fill', '#A0AEC0');

        const transferLinesGroup = foregroundGroup.append('g').attr('class', 'transfer-lines');

        sortedUsers.forEach(user => {
          const events = filteredData[user] || [];
          const sd = sequenceData[user] || { seq: [], earningEvents: [] };
          const seq = sd.seq || [];
          const earningEvents = sd.earningEvents || [];

          const userBackgroundGroup = backgroundGroup.append('g')
            .attr('class', 'user-background')
            .attr('transform', `translate(0, ${yScale(user)})`);

          const userForegroundGroup = foregroundGroup.append('g')
            .attr('class', 'user-foreground')
            .attr('data-user', user)
            .attr('transform', `translate(0, ${yScale(user)})`);

          // Balance Area
          if (seq.length > 0) {
            userBackgroundGroup.append('path')
              .datum(seq)
              .attr('class', 'balance-area')
              .attr('fill', '#90cdf4')
              .attr('opacity', 0.4)
              .attr('d', balanceArea);
          }

          // Earning Bars
          if (earningEvents.length > 0) {
            const barWidth = 4;
            userBackgroundGroup.selectAll('.earning-bar')
              .data(earningEvents)
              .enter()
              .append('rect')
              .attr('class', 'earning-bar')
              .attr('x', d => getX(new Date(d.date)) - barWidth / 2)
              .attr('y', eventBoxPadding)
              .attr('width', barWidth)
              .attr('height', d => earningScale(Math.abs(d.earning)))
              .attr('fill', d => d.earning >= 0 ? '#68d391' : '#fc8181')
              .attr('opacity', 0.8);
          }

          // Events
          events.forEach((event, eventIdx) => {
            const eventDate = new Date(event.timestamp);
            const cx = getX(eventDate);

            // Transfer lines
            if (!event.isTrade) {
              const isOut = event.type === 'transfer_out';
              const counterpartyInView = sortedUsers.includes(event.counterparty);
              if (isOut && counterpartyInView && user !== event.counterparty) {
                const startY = yScale(user);
                const endY = yScale(event.counterparty);
                // ezio: added datum binding for zoom
                transferLinesGroup.append('line')
                  .datum({ cx_date: eventDate })
                  .attr('class', 'transfer-line')
                  .attr('x1', cx).attr('x2', cx)
                  .attr('y1', startY).attr('y2', endY)
                  .attr('stroke', '#A0AEC0')
                  .attr('stroke-width', 1.5)
                  .attr('marker-end', 'url(#snapshot-transfer-arrow)')
                  .attr('opacity', 0.6);
              }
            }

            // Event group — ezio: added datum binding for zoom
            const eventGroup = userForegroundGroup.append('g')
              .datum({ date: eventDate })
              .attr('class', 'event-group')
              .attr('transform', `translate(${cx}, 0)`);

            let circleColor = '#A0AEC0';
            let eventLabel = '';
            let eventDetails = '';

            if (event.isTrade) {
              const isBuy = event.trade_info && event.trade_info.action === 'buy';
              circleColor = isBuy ? '#4299e1' : '#ed64a6';
              eventLabel = isBuy ? 'Buy' : 'Sell';
              eventDetails = `@ $${parseFloat(event.trade_info?.price_usd || 0).toFixed(4)}`;

              const y1 = balanceScale(event._prevBalance || 0) - eventBoxPadding;
              const y2 = balanceScale(event._currentBalance || 0) - eventBoxPadding;
              eventGroup.append('line')
                .attr('x1', 0).attr('x2', 0)
                .attr('y1', y1).attr('y2', y2)
                .attr('stroke', circleColor)
                .attr('stroke-width', 4)
                .attr('opacity', 0.8);
            } else {
              const isTransferIn = event.type === 'transfer_in';
              eventLabel = isTransferIn ? 'Transfer In' : 'Transfer Out';
              if (event.counterparty) {
                eventDetails = isTransferIn ? `from ${this.truncAddr(event.counterparty)}` : `to ${this.truncAddr(event.counterparty)}`;
              }
            }

            const circleRadius = isFewUsers ? 4 : 2;
            eventGroup.append('circle')
              .attr('class', 'event-circle')
              .attr('data-user', user)
              .attr('data-event-idx', eventIdx)
              .attr('r', circleRadius)
              .attr('cy', 0)
              .attr('fill', circleColor)
              .attr('opacity', 0.6)
              .attr('stroke', d3.color(circleColor).darker(0.8))
              .attr('stroke-width', 0.5);

            // Add to selectable items — ezio: added _dataDate for zoom coordinate recalc
            const key = `event:${user}:${eventIdx}`;
            const item = {
              type: 'event',
              key,
              user,
              eventIdx,
              screenX: margin.left + cx,
              screenY: margin.top + yScale(user),
              _dataDate: eventDate,
              radius: circleRadius,
              label: eventLabel,
              amount: event.amount,
              timestamp: event.timestamp,
              details: eventDetails,
              circleColor
            };
            this._selectableItems.push(item);
            this._itemsByKey.set(key, item);
          });
        });

        // ezio: store balanceScale for zoom handler
        this._balanceScale = balanceScale;
      }

      // Cache layout info for interaction and zoom
      this._margin = margin;
      this._innerWidth = innerWidth;
      this._innerHeight = innerHeight;
      this._yScale = yScale;
      this._xScale = xScale;
      this._sortedUsers = sortedUsers;
      this._eventBoxPadding = eventBoxPadding;

      // ezio: setup d3.zoom behavior
      const zoomRect = rootSvg.append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight)
        .attr('transform', `translate(${margin.left},${margin.top})`)
        .style('fill', 'none')
        .style('pointer-events', 'none');

      const vm = this;
      this._zoom = d3.zoom()
        .scaleExtent([1, 50])
        .translateExtent([[0, 0], [innerWidth, innerHeight]])
        .extent([[0, 0], [innerWidth, innerHeight]])
        .on('zoom', (event) => { vm.handleZoom(event); })
        .on('end', (event) => {
          // ezio: record zoom final state
          vm.recordOperation('zoom', {
            transform: { k: event.transform.k, x: event.transform.x, y: event.transform.y }
          });
        });

      zoomRect.call(this._zoom);
      this._zoomRect = zoomRect;
      this._currentTransform = d3.zoomIdentity;

      // ezio: position hover tooltip — bottom-right corner, clamped to container bounds
      if (data.hoveredElement) {
        this.tooltipReady = true;

        this.$nextTick(() => {
          const tip = this.$refs.hoverTooltip;
          const box = this.$refs.svgContainer;
          if (tip && box) {
            const tw = tip.offsetWidth;
            const th = tip.offsetHeight;
            const bw = box.offsetWidth;
            const bh = box.offsetHeight;
            // bottom-right corner, reserve 50px for toolbar
            this.tooltipLeft = bw - tw - 10;
            this.tooltipTop = bh - th - 50;
          }
        });
      }
    },

    setupInteraction() {
      const canvas = this.$refs.sketchCanvas;
      const container = this.$refs.svgContainer;
      canvas.width = container.offsetWidth;
      canvas.height = container.offsetHeight;
      const ctx = canvas.getContext('2d');
      const vm = this;

      let isDrawing = false;
      let currentPoints = [];
      // ezio: track drag start for select-mode pan
      let dragStartX = 0;
      let dragStartY = 0;
      let isPanning = false;

      // ezio: hit-test helper for both freehand strokes and rects (zoom-aware)
      const ERASER_RADIUS = 10;
      const isNearItem = (item, x, y) => {
        const t = vm._currentTransform;
        const margin = vm._margin || { left: 40 };
        // ezio: rect edge-proximity detection with zoom transform
        if (item.type === 'rect') {
          const screenX = t.applyX(item.x - margin.left) + margin.left;
          const screenX2 = t.applyX((item.x + item.w) - margin.left) + margin.left;
          const screenW = screenX2 - screenX;
          const ry = item.y, rh = item.h;
          const nearLeft   = Math.abs(x - screenX) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS;
          const nearRight  = Math.abs(x - (screenX + screenW)) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS;
          const nearTop    = Math.abs(y - ry) < ERASER_RADIUS && x >= screenX - ERASER_RADIUS && x <= screenX + screenW + ERASER_RADIUS;
          const nearBottom = Math.abs(y - (ry + rh)) < ERASER_RADIUS && x >= screenX - ERASER_RADIUS && x <= screenX + screenW + ERASER_RADIUS;
          return nearLeft || nearRight || nearTop || nearBottom;
        }
        // ezio: convert data-space points to screen-space for comparison
        return item.points.some(([px, py]) => {
          const screenX = t.applyX(px - margin.left) + margin.left;
          return Math.hypot(screenX - x, py - y) < ERASER_RADIUS;
        });
      };
      // ezio: rect tool drag origin
      let rectStart = null;

      // ezio: forward wheel events from canvas to d3.zoom for X-axis zoom
      canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (!vm._zoom || !vm._zoomRect) return;
        const rect = canvas.getBoundingClientRect();
        const direction = e.deltaY > 0 ? 0.9 : 1.1;
        const point = [e.clientX - rect.left - vm._margin.left, e.clientY - rect.top - vm._margin.top];
        vm._zoomRect.call(vm._zoom.scaleBy, direction, point);
      }, { passive: false });

      canvas.addEventListener('mousedown', (e) => {
        isDrawing = true;
        isPanning = false;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        dragStartX = x;
        dragStartY = y;
        currentPoints = [[x, y]];

        // ezio: rect tool records drag origin
        if (vm.activeTool === 'rect') {
          rectStart = { x, y };
        } else if (vm.activeTool === 'eraser') {
          // ezio: eraser immediately erases on mousedown
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y));
        }
        vm.redrawCanvas();
      });

      canvas.addEventListener('mousemove', (e) => {
        if (!isDrawing) return;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        currentPoints.push([x, y]);

        // ezio: branch on active tool
        if (vm.activeTool === 'pen') {
          // Draw current stroke in real time
          vm.redrawCanvas();
          if (currentPoints.length >= 2) {
            ctx.beginPath();
            // ezio: draw live stroke at screen coordinates (not yet converted to data-space)
            ctx.moveTo(currentPoints[0][0], currentPoints[0][1]);
            for (let i = 1; i < currentPoints.length; i++) {
              ctx.lineTo(currentPoints[i][0], currentPoints[i][1]);
            }
            ctx.strokeStyle = vm.penColor;
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.setLineDash([]);
            ctx.stroke();
          }
        } else if (vm.activeTool === 'rect' && rectStart) {
          // ezio: draw preview rectangle while dragging
          vm.redrawCanvas();
          const rx = Math.min(rectStart.x, x);
          const ry = Math.min(rectStart.y, y);
          const rw = Math.abs(x - rectStart.x);
          const rh = Math.abs(y - rectStart.y);
          ctx.beginPath();
          ctx.rect(rx, ry, rw, rh);
          ctx.strokeStyle = vm.penColor;
          ctx.lineWidth = 2;
          ctx.setLineDash([]);
          ctx.stroke();
        } else if (vm.activeTool === 'eraser') {
          // ezio: erase strokes touched by the eraser path
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y));
          vm.redrawCanvas();
        } else {
          // ezio: select mode — drag to pan if moved > 5px
          const dx = x - dragStartX;
          const dy = y - dragStartY;
          if (!isPanning && Math.hypot(dx, dy) > 5) {
            isPanning = true;
          }
          if (isPanning && vm._zoom && vm._zoomRect) {
            // Apply incremental pan (delta from last point)
            const prev = currentPoints[currentPoints.length - 2];
            const deltaX = x - prev[0];
            vm._zoomRect.call(vm._zoom.translateBy, deltaX, 0);
          }
        }
      });

      canvas.addEventListener('mouseup', (e) => {
        if (!isDrawing) return;
        isDrawing = false;

        const hasMoved = currentPoints.length > 3;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // ezio: branch on active tool
        if (vm.activeTool === 'pen') {
          // Save the stroke
          if (hasMoved && currentPoints.length >= 2) {
            // ezio: convert screen coordinates to data-space for zoom-aware storage
            const t = vm._currentTransform;
            const margin = vm._margin;
            const dataPoints = currentPoints.map(([px, py]) => {
              const dataX = t.invertX(px - margin.left) + margin.left;
              return [dataX, py];
            });
            vm.sketchStrokes.push({
              points: dataPoints,
              color: vm.penColor,
              width: 2
            });
            // ezio: record sketch operation
            vm.recordOperation('sketch', {
              strokeIndex: vm.sketchStrokes.length - 1,
              points: dataPoints,
              color: vm.penColor,
              width: 2
            });
          }
          vm.redrawCanvas();
        } else if (vm.activeTool === 'rect' && rectStart) {
          // ezio: finalize rectangle — convert screen X to data-space
          const rx = Math.min(rectStart.x, x);
          const ry = Math.min(rectStart.y, y);
          const rw = Math.abs(x - rectStart.x);
          const rh = Math.abs(y - rectStart.y);
          if (rw > 2 || rh > 2) {
            const t = vm._currentTransform;
            const margin = vm._margin;
            const dataX = t.invertX(rx - margin.left) + margin.left;
            const dataX2 = t.invertX((rx + rw) - margin.left) + margin.left;
            const dataW = dataX2 - dataX;
            const rectObj = { type: 'rect', x: dataX, y: ry, w: dataW, h: rh, color: vm.penColor, width: 2 };
            vm.sketchStrokes.push(rectObj);
            // ezio: record sketch-rect operation
            vm.recordOperation('sketch-rect', {
              strokeIndex: vm.sketchStrokes.length - 1,
              ...rectObj
            });
          }
          rectStart = null;
          vm.redrawCanvas();
        } else if (vm.activeTool === 'eraser') {
          // ezio: eraser mouseup — just redraw
          vm.redrawCanvas();
        } else {
          // Select tool
          if (isPanning) {
            // ezio: was a pan drag, don't select
            isPanning = false;
          } else {
            // Click to toggle selection
            const item = vm._findClickedItem(x, y);
            if (item) {
              const wasSelected = vm._selectedSet.has(item.key);
              if (wasSelected) {
                vm._selectedSet.delete(item.key);
              } else {
                vm._selectedSet.add(item.key);
              }
              vm._updateHighlight();
              // ezio: record select/deselect operation
              vm.recordOperation(wasSelected ? 'deselect' : 'select', {
                itemKey: item.key,
                itemType: item.type,
                selectedSetAfter: Array.from(vm._selectedSet)
              });
            }
          }
        }

        currentPoints = [];
      });
    },

    // ezio: replay a recorded operation log
    async replayOperations(log, { animated = false, speedMs = 500 } = {}) {
      // Reset state
      this.clearSketches();
      this._selectedSet.clear();
      if (this._zoom && this._zoomRect) {
        this._zoomRect.call(this._zoom.transform, d3.zoomIdentity);
      }
      this._updateHighlight();

      for (const entry of log) {
        if (animated) {
          await new Promise(r => setTimeout(r, speedMs));
        }
        switch (entry.type) {
          case 'select':
            this._selectedSet.add(entry.payload.itemKey);
            this._updateHighlight();
            break;
          case 'deselect':
            this._selectedSet.delete(entry.payload.itemKey);
            this._updateHighlight();
            break;
          case 'zoom': {
            const t = entry.payload.transform;
            if (this._zoom && this._zoomRect) {
              this._zoomRect.call(
                this._zoom.transform,
                d3.zoomIdentity.translate(t.x, t.y).scale(t.k)
              );
            }
            break;
          }
          case 'sketch':
            this.sketchStrokes.push({
              points: entry.payload.points,
              color: entry.payload.color,
              width: entry.payload.width
            });
            this.redrawCanvas();
            break;
          // ezio: replay rect sketch operations
          case 'sketch-rect':
            this.sketchStrokes.push({
              type: 'rect',
              x: entry.payload.x,
              y: entry.payload.y,
              w: entry.payload.w,
              h: entry.payload.h,
              color: entry.payload.color,
              width: entry.payload.width
            });
            this.redrawCanvas();
            break;
          case 'clear-sketches':
            this.sketchStrokes = [];
            this.redrawCanvas();
            break;
        }
      }
    }
  }
};
</script>

<style scoped>
/* ezio: content-adaptive container — sized by vis-area, capped by viewport */
.behavior-snapshot-container {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.header h2 {
  margin: 0;
  font-size: 16px;
}

.selection-badge {
  background: #fdd835;
  color: #333;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: bold;
}

/* ezio: margin-left:auto pushes × to the right, matching other snapshots */
.close-btn {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: #666;
  margin-left: auto;
}

.close-btn:hover {
  color: #000;
}

/* ezio: preserved hover tooltip — boundary-aware, matches BehaviorDetails .custom-tooltip style */
.snapshot-tooltip {
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #2d3748;
  pointer-events: none;
  z-index: 3;
  max-width: 280px;
  max-height: 300px;
  overflow-y: auto;
  white-space: normal;
  word-break: break-word;
}

.vis-area {
  flex: 1;
  min-height: 200px;
  position: relative;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.vis-area svg {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

/* ezio: floating toolbar positioning */
.floating-toolbar {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 2;
}

/* ezio: cursor per tool */
.lasso-overlay.cursor-select { cursor: pointer; }
.lasso-overlay.cursor-pen    { cursor: crosshair; }
.lasso-overlay.cursor-rect    { cursor: crosshair; }
.lasso-overlay.cursor-eraser { cursor: pointer; }

.lasso-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.details-panel {
  max-height: 200px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.details-header {
  padding: 8px 12px;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 13px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  user-select: none;
}

.details-count {
  color: #666;
  font-weight: normal;
}

.details-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.details-empty {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.details-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.details-table th {
  background: #fafafa;
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
}

.details-table td {
  padding: 5px 10px;
  border-bottom: 1px solid #f0f0f0;
}

.details-table tr:hover {
  background: #f8f8f8;
}

.addr {
  font-family: monospace;
  font-size: 11px;
}

.type-tag {
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.type-tag.type-user-track {
  background: #ebf4ff;
  color: #3182ce;
}

.type-tag.type-event {
  background: #f0fff4;
  color: #38a169;
}

.input-area {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.text-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
  outline: none;
}

.text-input:focus {
  border-color: #4caf50;
}

.send-btn {
  padding: 8px 16px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: bold;
}

.send-btn:hover {
  background: #43a047;
}
</style>

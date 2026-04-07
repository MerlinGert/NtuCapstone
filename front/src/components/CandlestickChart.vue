<template>
  <div class="candlestick-container">
    <div class="header-panel">
      <div class="panel-title">{{ currentCoin }} K-Line</div>
      <div class="granularity-panel">
        <button v-for="g in granularities" :key="g.key"
          :class="['gran-btn', currentGranularity===g.key ? 'gran-btn--active' : '']"
          @click="currentGranularity=g.key"
        >{{ g.label }}</button>
      </div>
    </div>
    
    <div class="candlestick-wrap" ref="wrap">
      <!-- Overlay SVG for connection bands -->
      <svg ref="bandsOverlay" class="bands-overlay"></svg>

      <!-- Upper manipulation cards (Round Trip) -->
      <div class="manipulation-cards-container scroll-x top-cards scroll-top" @scroll="drawBands" ref="topCardsContainer">
        <div class="manipulation-card top-card" v-for="(card, i) in topCards" :key="'top-'+i" :title="card.tooltip">
          <div class="card-time">{{ card.timeLabel }}</div>
          <div class="card-stats">{{ card.timeSpan }} | ${{ card.totalAmount }}</div>
          <svg :ref="'svg-top-'+i" class="card-svg" width="100%" height="100%"></svg>
        </div>
        <div v-if="topCards.length === 0" class="empty-cards">No Round Trip manipulations</div>
      </div>

      <!-- Centered K-line chart (Flex 1 to fill remaining space) -->
      <div class="chart-body-wrapper">
        <div class="chart-body" ref="chartBody">
          <svg ref="svg" class="candle-svg"></svg>
          <div v-if="loading" class="loading-mask">Loading...</div>
          <div v-if="!loading && ohlc.length === 0" class="loading-mask">No data</div>
        </div>
      </div>

      <!-- Lower manipulation cards (Same Direction) -->
      <div class="manipulation-cards-container scroll-x bottom-cards" @scroll="drawBands" ref="bottomCardsContainer">
        <div class="manipulation-card" v-for="(card, i) in bottomCards" :key="'bottom-'+i" :title="card.tooltip">
          <div class="card-time">{{ card.timeLabel }}</div>
          <div class="card-stats">{{ card.timeSpan }} | ${{ card.totalAmount }}</div>
          <svg :ref="'svg-bottom-'+i" class="card-svg" width="100%" height="100%"></svg>
        </div>
        <div v-if="bottomCards.length === 0" class="empty-cards">No Same Direction manipulations</div>
      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'

const COLORS = {
  bull: '#26a69a', // Green (欧美习惯：阳线涨为绿)
  bear: '#ef5350', // Red   (欧美习惯：阴线跌为红)
  grid: '#eef2f7',
  axis: '#718096',
  volume: '#78909c' // Darker Gray for bar chart
}

const GRANULARITIES = [
  { key: '1H', label: '1H' },
  { key: '1D', label: '1D' },
  { key: '3D', label: '3D' },
  { key: '1W', label: '1W' },
]

export default {
  name: 'CandlestickChart',
  props: {
    manipulationResults: {
      type: Array,
      default: () => []
    },
    currentCoin: {
      type: String,
      default: 'ACT'
    }
  },
  data() {
    return {
      granularities: GRANULARITIES,
      currentGranularity: '1H',
      actOhlc: null,
      ohlc: [],
      loading: true,
      resizeObs: null,
      panelWidth: 400,
      zoomTransform: null
    }
  },
  computed: {
    chartHeight() {
      return Math.max(150, this.panelWidth / 3);
    },
    aggregatedCards() {
      if (!this.manipulationResults || this.ohlc.length === 0) return { roundTrip: [], sameDirection: [] };
      
      const fmtMap = {
        '1H': d => d3.timeFormat('%m/%d %H:%M')(d),
        '1D': d => d3.timeFormat('%m/%d')(d),
        '3D': d => d3.timeFormat('%m/%d')(d),
        '1W': d => d3.timeFormat('%m/%d')(d),
      };
      const fmt = fmtMap[this.currentGranularity];

      const computeStats = (rawManipulations) => {
        let minTs = Infinity;
        let maxTs = -Infinity;
        let totalAmount = 0;
        rawManipulations.forEach(m => {
          if (m.transactions) {
            m.transactions.forEach(tx => {
              const tsStr = tx.timestamp || tx.time;
              if (tsStr) {
                const ts = this.parseUtcDate(tsStr).getTime();
                if (ts < minTs) minTs = ts;
                if (ts > maxTs) maxTs = ts;
              }
              totalAmount += parseFloat(tx.amount || tx.quantity) || 0;
            });
          }
        });
        
        let timeRangeStr = '';
        if (minTs !== Infinity && maxTs !== -Infinity) {
          const timePad = Math.max((maxTs - minTs) * 0.05, 60000);
          const startTs = minTs - timePad;
          const endTs = maxTs + timePad;
          
          const timeFmt = d3.timeFormat('%m/%d %H:%M:%S');
          timeRangeStr = `${timeFmt(new Date(startTs))} - ${timeFmt(new Date(endTs))}`;
        } else {
          timeRangeStr = 'N/A';
        }
        
        let amountStr = '';
        if (totalAmount >= 1000000) {
          amountStr = (totalAmount / 1000000).toFixed(2) + 'M';
        } else if (totalAmount >= 1000) {
          amountStr = (totalAmount / 1000).toFixed(2) + 'K';
        } else {
          amountStr = totalAmount.toFixed(2);
        }
        
        return { timeSpan: timeRangeStr, totalAmount: amountStr };
      };

      const bins = {};

      this.manipulationResults.forEach(res => {
        if (!res.manipulation_time || res.manipulation_time.length === 0) return;
        // Use the end time (last element in manipulation_time) for grouping
        const endStr = res.manipulation_time[res.manipulation_time.length - 1];
        const endTs = this.parseUtcDate(endStr).getTime();
        
        // Find the matching time bin in OHLC
        let binIdx = 0;
        for (let i = 0; i < this.ohlc.length; i++) {
          if (this.ohlc[i].date.getTime() <= endTs) {
            binIdx = i;
          } else {
            break;
          }
        }
        
        if (!bins[binIdx]) {
          bins[binIdx] = { roundTrip: [], sameDirection: [], date: this.ohlc[binIdx].date };
        }
        
        const isRoundTrip = res.detection_method && res.detection_method.toLowerCase().includes('round_trip');
        if (isRoundTrip) {
          bins[binIdx].roundTrip.push(res);
        } else {
          bins[binIdx].sameDirection.push(res);
        }
      });
      console.log("bins",bins)
      
      const roundTripCards = [];
      const sameDirectionCards = [];

      Object.keys(bins).forEach(idx => {
        const bin = bins[idx];
        const timeLabel = fmt(bin.date);
        
        if (bin.roundTrip.length > 0) {
          const uniqueUsers = new Set();
          bin.roundTrip.forEach(r => (r.participants || []).forEach(u => uniqueUsers.add(u)));
          const stats = computeStats(bin.roundTrip);
          roundTripCards.push({
            timeLabel: timeLabel,
            timeSpan: stats.timeSpan,
            totalAmount: stats.totalAmount,
            method: 'Round Trip',
            count: bin.roundTrip.length,
            users: uniqueUsers.size + ' Users',
            tooltip: `${bin.roundTrip.length} manipulations\nUsers: ${Array.from(uniqueUsers).join(', ')}\nTime Range: ${stats.timeSpan}\nAmount: ${stats.totalAmount}`,
            ts: bin.date.getTime(),
            rawManipulations: bin.roundTrip,
            uniqueUsers: Array.from(uniqueUsers),
            binDate: bin.date
          });
        }
        
        if (bin.sameDirection.length > 0) {
          const uniqueUsers = new Set();
          bin.sameDirection.forEach(r => (r.participants || []).forEach(u => uniqueUsers.add(u)));
          const stats = computeStats(bin.sameDirection);
          sameDirectionCards.push({
            timeLabel: timeLabel,
            timeSpan: stats.timeSpan,
            totalAmount: stats.totalAmount,
            method: 'Same Direction',
            count: bin.sameDirection.length,
            users: uniqueUsers.size + ' Users',
            tooltip: `${bin.sameDirection.length} manipulations\nUsers: ${Array.from(uniqueUsers).join(', ')}\nTime Range: ${stats.timeSpan}\nAmount: ${stats.totalAmount}`,
            ts: bin.date.getTime(),
            rawManipulations: bin.sameDirection,
            uniqueUsers: Array.from(uniqueUsers),
            binDate: bin.date
          });
        }
      });
      
      // Sort by time
      roundTripCards.sort((a, b) => a.ts - b.ts);
      sameDirectionCards.sort((a, b) => a.ts - b.ts);
      
      return { roundTrip: roundTripCards, sameDirection: sameDirectionCards };
    },
    topCards() {
      return this.aggregatedCards.roundTrip;
    },
    bottomCards() {
      return this.aggregatedCards.sameDirection;
    }
  },
  watch: {
    currentGranularity() {
      this.refresh()
    },
    manipulationResults: {
      deep: true,
      handler() {
        // Need to recalculate binData roundTripCount/sameDirectionCount 
        // when manipulation results change, so we call refresh() instead of just draw()
        this.refresh()
      }
    },
    currentCoin() {
      this.loadData();
    }
  },
  mounted() {
    this.loadData()
    this.resizeObs = new ResizeObserver(() => this.draw())
    this.resizeObs.observe(this.$refs.chartBody)
  },
  beforeUnmount() {
    if (this.resizeObs) this.resizeObs.disconnect()
  },
  methods: {
    // Safari/iOS rejects "YYYY-MM-DD HH:MM:SS" and "... UTC" date strings.
    // Normalize to ISO 8601 ("YYYY-MM-DDTHH:MM:SSZ") so all browsers parse it.
    parseUtcDate(s) {
      if (!s) return new Date(NaN)
      const iso = String(s).replace(' UTC', '').replace(' ', 'T') + 'Z'
      return new Date(iso)
    },

    async loadData() {
      this.loading = true
      try {
        const dataDir = this.currentCoin === 'PNUT' ? 'data2' : 'data'
        const fileName = this.currentCoin === 'PNUT' ? 'OHLC.json' : 'ACT_OHLC.json'
        const res = await fetch(`/${dataDir}/${fileName}`)
        this.actOhlc = await res.json()
      } catch (e) {
        console.error('CandlestickChart: failed to load data', e)
        this.actOhlc = {}
      }
      this.loading = false
      this.refresh()
    },

    refresh() {
      if (!this.actOhlc) { this.ohlc = []; return }
      const raw = this.actOhlc[this.currentGranularity] || []
      
      // Calculate manipulation counts per bin directly in ohlc data
      const binData = raw.map(d => ({
        date:  this.parseUtcDate(d.t),
        open:  d.o,
        high:  d.h,
        low:   d.l,
        close: d.c,
        vol:   d.v,
        roundTripCount: 0,
        sameDirectionCount: 0
      }))

      if (this.manipulationResults && this.manipulationResults.length > 0) {
        this.manipulationResults.forEach(res => {
          if (!res.manipulation_time || res.manipulation_time.length === 0) return;
          const endStr = res.manipulation_time[res.manipulation_time.length - 1];
          const endTs = this.parseUtcDate(endStr).getTime();
          
          let binIdx = 0;
          for (let i = 0; i < binData.length; i++) {
            if (binData[i].date.getTime() <= endTs) {
              binIdx = i;
            } else {
              break;
            }
          }
          
          const isRoundTrip = res.detection_method && res.detection_method.toLowerCase().includes('round_trip');
          if (isRoundTrip) {
            binData[binIdx].roundTripCount++;
          } else {
            binData[binIdx].sameDirectionCount++;
          }
        });
      }
      
      this.ohlc = binData;
      this.$nextTick(() => this.draw())
    },

    draw() {
      const el    = this.$refs.chartBody
      const svgEl = this.$refs.svg
      if (!el || !svgEl || this.ohlc.length === 0) return

      const W = el.clientWidth  || 400
      this.panelWidth = this.$refs.wrap ? this.$refs.wrap.clientWidth : W;
      const H = el.clientHeight || 200
      const m = { top: 40, right: 80, bottom: 40, left: 8 }
      const iW = W - m.left - m.right
      const iH = H - m.top  - m.bottom

      const svg = d3.select(svgEl).attr('width', W).attr('height', H)
      svg.selectAll('*').remove()
      
      // Semantic zoom setup
      const zoom = d3.zoom()
        .scaleExtent([1, Math.max(1, this.ohlc.length / 10)]) // Allow zooming until ~10 candles are visible
        .on('zoom', (event) => {
          if (!event.sourceEvent) return; // Prevent infinite loop when setting zoom programmatically
          this.zoomTransform = event.transform
          this.draw()
          // syncCardScroll and drawBands are called via $nextTick inside draw()
        })

      // Attach zoom to svg but only if we haven't already set a transform
      // to avoid resetting the transform on redraw
      svg.call(zoom)
      if (this.zoomTransform) {
        // Restore zoom transform silently
        Object.assign(svg.node(), { __zoom: this.zoomTransform })
      }
      
      // Defs for styling
      const defs = svg.append('defs')
      
      // Add clipPath to prevent candles and bars from overflowing horizontally during zoom
      defs.append('clipPath')
        .attr('id', 'zoom-clip')
        .append('rect')
        .attr('width', iW)
        .attr('height', H) // Full height to include top and bottom bars
        .attr('y', -m.top) // Start from top to cover top bars
      
      const g = svg.append('g')
        .attr('transform', `translate(${m.left},${m.top})`)
        
      const chartBody = g.append('g')
        .attr('clip-path', 'url(#zoom-clip)')

      // Create a zoom group (we use semantic zoom, so no transform is applied directly to this group)
      const zoomGroup = chartBody.append('g')
        .attr('class', 'zoom-group')

      const data = this.ohlc

      // Semantic zoom: map indices to determine visible data window
      const baseIndexScale = d3.scaleLinear().domain([0, data.length - 1]).range([0, iW])
      let startIndex = 0
      let endIndex = data.length - 1

      if (this.zoomTransform) {
        const zoomedScale = this.zoomTransform.rescaleX(baseIndexScale)
        const domain = zoomedScale.domain()
        startIndex = Math.max(0, Math.floor(domain[0]))
        endIndex = Math.min(data.length - 1, Math.ceil(domain[1]))
        
        // Ensure at least a minimal window
        if (endIndex - startIndex < 5) {
          const mid = (startIndex + endIndex) / 2
          startIndex = Math.max(0, Math.floor(mid - 2.5))
          endIndex = Math.min(data.length - 1, Math.ceil(mid + 2.5))
        }
      }

      const visibleData = data.slice(startIndex, endIndex + 1)

      // X scale based ONLY on visible data window
      const xScale = d3.scaleBand()
        .domain(visibleData.map(d => d.date))
        .range([0, iW])
        .padding(0.25)

      this.chartState = { xScale, m, H, W, iW, baseIndexScale, visibleData, dataLength: data.length };

      // Y scale for K-line (dynamically scaled to visible window for better UX)
      const [minL, maxH] = [d3.min(visibleData, d => d.low), d3.max(visibleData, d => d.high)]
      const pad = (maxH - minL) * 0.06 || 1e-9
      const yScale = d3.scaleLinear()
        .domain([minL - pad, maxH + pad])
        .range([iH, 0])

      // Bar chart scales (Top and Bottom margins)
      const maxRoundTrip = d3.max(visibleData, d => d.roundTripCount) || 1;
      const maxSameDirection = d3.max(visibleData, d => d.sameDirectionCount) || 1;
      
      const barHeight = 25; // max height for bars
      
      const yTopBarScale = d3.scaleLinear()
        .domain([0, maxRoundTrip])
        .range([0, barHeight]); // grows upwards visually by setting y = -height
        
      const yBottomBarScale = d3.scaleLinear()
        .domain([0, maxSameDirection])
        .range([0, barHeight]); // grows downwards

      // Grid
      g.append('g').selectAll('line')
        .data(yScale.ticks(5))
        .enter().append('line')
          .attr('x1', 0).attr('x2', iW)
          .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
          .attr('stroke', COLORS.grid).attr('stroke-width', 1)

      // Boundary lines for bar charts and bands
      g.append('line')
        .attr('x1', 0).attr('x2', iW)
        .attr('y1', 0).attr('y2', 0)
        .attr('stroke', '#cbd5e1').attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,2')

      g.append('line')
        .attr('x1', 0).attr('x2', iW)
        .attr('y1', iH).attr('y2', iH)
        .attr('stroke', '#cbd5e1').attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,2')

      // Y axis (right)
      g.append('g')
        .attr('transform', `translate(${iW},0)`)
        .call(d3.axisRight(yScale).ticks(5))
        .call(ax => ax.select('.domain').remove())
        .call(ax => ax.selectAll('.tick line')
          .attr('x2', -iW).attr('stroke', '#e2e8f0').attr('stroke-dasharray', '2,2'))
        .selectAll('text')
        .style('fill', COLORS.axis)
        .style('font-size', '9px')

      // X axis
      const fmtMap = {
        '1H': d => d3.timeFormat('%m/%d %H:%M')(d),
        '1D': d => d3.timeFormat('%m/%d')(d),
        '3D': d => d3.timeFormat('%m/%d')(d),
        '1W': d => d3.timeFormat('%m/%d')(d),
      }
      const fmt  = fmtMap[this.currentGranularity]
      // 动态计算合适的间距，确保X轴文字不会重叠
      const maxTicks = Math.max(2, Math.floor(iW / 90))
      
      const step = Math.max(1, Math.ceil(visibleData.length / maxTicks))
      const tickDates = visibleData.filter((_, i) => i % step === 0).map(d => d.date)

      // Create x-axis group
      const xAxisGroup = g.append('g').attr('transform', `translate(0,${iH})`)
      
      xAxisGroup.call(d3.axisBottom(xScale).tickValues(tickDates).tickFormat(fmt).tickSizeInner(0).tickSizeOuter(0))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text')
        .style('fill', COLORS.axis)
        .style('font-size', '8px')
        .attr('dy', '-5px')
        .style('text-anchor', 'middle')

      // Candles
      const bw = xScale.bandwidth()

      // Permanent manipulation highlight masks on K-line
      const masks = zoomGroup.append('g').attr('class', 'manipulation-masks')
      masks.selectAll('rect')
        .data(visibleData.filter(d => d.roundTripCount > 0 || d.sameDirectionCount > 0))
        .enter().append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', 0)
        .attr('width', bw)
        .attr('height', iH)
        .attr('fill', 'rgba(100, 150, 255, 0.08)')
        .style('pointer-events', 'none')

      const candles = zoomGroup.append('g').selectAll('g.candle')
        .data(visibleData).enter().append('g').attr('class', 'candle')

      candles.append('line')
        .attr('x1', d => xScale(d.date) + bw / 2)
        .attr('x2', d => xScale(d.date) + bw / 2)
        .attr('y1', d => yScale(d.high))
        .attr('y2', d => yScale(d.low))
        .attr('stroke', d => d.close >= d.open ? COLORS.bull : COLORS.bear)
        .attr('stroke-width', 1)

      candles.append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', d => yScale(Math.max(d.open, d.close)))
        .attr('width', bw)
        .attr('height', d => Math.max(1, Math.abs(yScale(d.open) - yScale(d.close))))
        .attr('fill', d => d.close >= d.open ? COLORS.bull : COLORS.bear)
        .attr('rx', 1)

      // Top Bar Chart (Round Trip)
      const topBars = zoomGroup.append('g').attr('class', 'top-bars')
      topBars.selectAll('rect')
        .data(visibleData.filter(d => d.roundTripCount > 0))
        .enter().append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', d => -yTopBarScale(d.roundTripCount)) // Align with 0 position
        .attr('width', bw)
        .attr('height', d => yTopBarScale(d.roundTripCount))
        .attr('fill', COLORS.volume)
        .attr('rx', 1)

      // Bottom Bar Chart (Same Direction)
      const bottomBars = zoomGroup.append('g').attr('class', 'bottom-bars')
      bottomBars.selectAll('rect')
        .data(visibleData.filter(d => d.sameDirectionCount > 0))
        .enter().append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', iH) // Align with 0 position
        .attr('width', bw)
        .attr('height', d => yBottomBarScale(d.sameDirectionCount))
        .attr('fill', COLORS.volume)
        .attr('rx', 1)

      // Tooltip
        const tooltip = d3.select(this.$refs.wrap)
          .selectAll('.kline-tooltip')
          .data([0])
          .join('div')
          .attr('class', 'kline-tooltip')
          .style('position', 'absolute')
          .style('display', 'none')
          .style('background', 'rgba(255,255,255,0.95)')
          .style('border', '1px solid #e2e8f0')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('font-size', '12px')
          .style('pointer-events', 'none')
          .style('z-index', 10)
          .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')

        // Hover interaction layer
        // We append a background rect to capture zoom and hover events
        const hoverRect = chartBody.append('rect')
          .attr('width', iW)
          .attr('height', H)
          .attr('y', -m.top)
          .style('fill', 'none')
          .style('pointer-events', 'all')
        
        // Update hover interactions to use hoverRect
        hoverRect.on('mousemove', (e) => {
          const [mx, my] = d3.pointer(e, hoverRect.node())
          
          // Find closest candle based on x position
          let closestDist = Infinity
          let closestData = null
          
          visibleData.forEach(d => {
            const cx = xScale(d.date) + bw/2
            const dist = Math.abs(mx - cx)
            if (dist < closestDist) {
              closestDist = dist
              closestData = d
            }
          })

          // Adjusted interaction distance
          const interactionDist = Math.max(bw * 1.5, 10)

          if (closestData && closestDist < interactionDist) {
            const d = closestData
            let screenCx = xScale(d.date) + bw/2

            // Draw crosshair
            g.selectAll('.crosshair').remove()
            g.append('line')
              .attr('class', 'crosshair')
              .attr('x1', screenCx)
              .attr('x2', screenCx)
              .attr('y1', 0)
              .attr('y2', iH)
              .attr('stroke', '#ccc')
              .attr('stroke-dasharray', '3,3')

            const fmt = d3.timeFormat('%Y-%m-%d %H:%M')
            const upDown = d.close >= d.open ? '▲' : '▼'
            const color = d.close >= d.open ? COLORS.bull : COLORS.bear
            
            const [wrapX, wrapY] = d3.pointer(e, this.$refs.wrap)
            
            // Adjust position to prevent right-edge clipping
            const wrapWidth = this.$refs.wrap.clientWidth || W;
            let leftPos = wrapX + 15
            if (wrapX > wrapWidth - 150) {
              leftPos = wrapX - 140
            }

            // Helper to format values avoiding scientific notation
            const formatVal = (val) => {
              if (val === 0) return "0";
              
              // For extremely small values (< 0.000001), format with 8 decimal places 
              if (Math.abs(val) < 0.000001) {
                return Number(val).toFixed(8).replace(/\.?0+$/, '');
              }
              
              // For small values (< 1), format with up to 6 decimal places
              if (Math.abs(val) < 1) {
                return Number(val).toFixed(6).replace(/\.?0+$/, '');
              }
              
              // For larger values, use unit suffixes
              if (Math.abs(val) >= 1e9) {
                return (val / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
              }
              if (Math.abs(val) >= 1e6) {
                return (val / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
              }
              if (Math.abs(val) >= 1e3) {
                return (val / 1e3).toFixed(2).replace(/\.?0+$/, '') + 'K';
              }
              
              // For normal values, max 2 decimal places
              return Number(val).toFixed(2).replace(/\.?0+$/, '');
            };

            tooltip.style('display', 'block')
              .style('left', leftPos + 'px')
              .style('top', (wrapY + 15) + 'px')
              .html(`
                <div style="color:${color};font-weight:bold;">${upDown} ${fmt(d.date)}</div>
                <div>O: $${formatVal(d.open)}</div>
                <div>H: $${formatVal(d.high)}</div>
                <div>L: $${formatVal(d.low)}</div>
                <div>C: <b>$${formatVal(d.close)}</b></div>
                <div style="color:#a0aec0;">Txns: ${d.vol}</div>
                ${d.roundTripCount > 0 ? `<div style="color:#e53e3e; margin-top:4px;">Round Trip: ${d.roundTripCount}</div>` : ''}
                ${d.sameDirectionCount > 0 ? `<div style="color:#e53e3e;">Same Dir: ${d.sameDirectionCount}</div>` : ''}
              `)
          } else {
            g.selectAll('.crosshair').remove()
            tooltip.style('display', 'none')
          }
        }).on('mouseleave', () => {
          g.selectAll('.crosshair').remove()
          tooltip.style('display', 'none')
        })
          
        this.$nextTick(() => {
          this.syncCardScroll();
          this.drawBands();
          this.drawCardBehaviors();
        });
    },
    syncCardScroll() {
      if (!this.chartState || !this.chartState.visibleData || !this.chartState.visibleData.length) return;
      
      const visibleStartTs = this.chartState.visibleData[0].date.getTime();

      const scrollToCard = (containerRef, cardsData) => {
        const container = this.$refs[containerRef];
        if (!container) return;

        // Find the first card that falls within or after the visible time window
        const targetIndex = cardsData.findIndex(c => c.ts >= visibleStartTs);
        
        if (targetIndex !== -1) {
          const cardEls = container.querySelectorAll('.manipulation-card');
          if (cardEls[targetIndex]) {
            const targetEl = cardEls[targetIndex];
            // 12px accounts for the padding-left of the container
            container.scrollLeft = targetEl.offsetLeft - 12;
          }
        }
      };

      scrollToCard('topCardsContainer', this.topCards);
      scrollToCard('bottomCardsContainer', this.bottomCards);
    },
    drawCardBehaviors() {
      const drawCard = (cardData, isTop, index) => {
        const refName = `svg-${isTop ? 'top' : 'bottom'}-${index}`;
        const svgEls = this.$refs[refName];
        if (!svgEls || !svgEls[0]) return;
        const svgNode = svgEls[0];
        
        const W = svgNode.clientWidth || 200;
        const H = svgNode.clientHeight || 70; // fixed height based on flex layout
        d3.select(svgNode).attr('height', H);
        
        const svg = d3.select(svgNode);
        svg.selectAll('*').remove();
        
        // Find time range for this card based on all transactions and collect all users
        let minTs = Infinity;
        let maxTs = -Infinity;
        const localUniqueUsers = new Set(cardData.uniqueUsers);
        
        cardData.rawManipulations.forEach(m => {
          if (m.transactions) {
            m.transactions.forEach(tx => {
              const tsStr = tx.timestamp || tx.time;
              if (tsStr) {
                const ts = this.parseUtcDate(tsStr).getTime();
                if (ts < minTs) minTs = ts;
                if (ts > maxTs) maxTs = ts;
              }
              const user = tx.trader || tx.user;
              if (user) {
                localUniqueUsers.add(user);
              }
            });
          }
        });
        
        const allUsersList = Array.from(localUniqueUsers);
        if (allUsersList.length === 0) return;
        
        // Add a little padding to the time scale
        const timePad = Math.max((maxTs - minTs) * 0.05, 60000);
        
        const mLeft = 40;
        const mRight = 10;
        
        const xScale = d3.scaleTime()
          .domain([new Date(minTs - timePad), new Date(maxTs + timePad)])
          .range([mLeft, W - mRight]);
          
        const yScale = d3.scalePoint()
          .domain(allUsersList)
          .range([10, H - 10])
          .padding(0.5);
          
        // Draw user lines
        svg.selectAll('.user-line')
          .data(allUsersList)
          .enter().append('line')
          .attr('class', 'user-line')
          .attr('x1', mLeft)
          .attr('x2', W - mRight)
          .attr('y1', d => yScale(d))
          .attr('y2', d => yScale(d))
          .attr('stroke', '#e2e8f0')
          .attr('stroke-width', 1);
          
        // Draw user labels
        svg.selectAll('.user-label')
          .data(allUsersList)
          .enter().append('text')
          .attr('class', 'user-label')
          .attr('x', mLeft - 5)
          .attr('y', d => yScale(d))
          .attr('dy', '0.32em')
          .attr('text-anchor', 'end')
          .attr('fill', '#718096')
          .style('font-size', '9px')
          .text(d => d.substring(0, 3) + '..')
          .append('title').text(d => d);
          
        // Draw events
        let allEvents = [];
        let maxAmount = 0;
        
        cardData.rawManipulations.forEach(m => {
          if (m.transactions) {
            m.transactions.forEach(tx => {
              const tsStr = tx.timestamp || tx.time;
              if (!tsStr) return;
              const evTs = this.parseUtcDate(tsStr).getTime();
              const user = tx.trader || tx.user;
              if (user && allUsersList.includes(user) && evTs >= minTs - timePad && evTs <= maxTs + timePad) {
                const amount = parseFloat(tx.amount || tx.quantity) || 0;
                if (amount > maxAmount) maxAmount = amount;
                allEvents.push({
                  user: user,
                  ts: evTs,
                  amount: amount,
                  action: tx.action_type || tx.action,
                  rawTime: tsStr
                });
              }
            });
          }
        });
        
        // Calculate max radius based on row height to avoid overflow
        const yPadding = 10;
        const availableH = H - yPadding * 2;
        const userCount = allUsersList.length;
        const rowHeight = userCount > 1 ? availableH / (userCount - 1) : availableH;
        
        // Max radius should be small enough to fit within row spacing, but at least 1.5, max 6
        const maxRadius = Math.min(6, Math.max(1.5, (rowHeight / 2) - 0.5));
        const minRadius = Math.min(2, maxRadius * 0.3);
        
        const rScale = d3.scaleSqrt()
          .domain([0, maxAmount || 1])
          .range([minRadius, maxRadius]);
          
        svg.selectAll('.event-point')
          .data(allEvents)
          .enter().append('circle')
          .attr('class', 'event-point')
          .attr('cx', d => xScale(d.ts))
          .attr('cy', d => yScale(d.user))
          .attr('r', d => rScale(d.amount))
          .attr('fill', d => d.action === 'buy' ? '#4299e1' : '#ed64a6') // blue for buy, pink for sell
          .attr('opacity', 0.5)
          .attr('stroke', d => d.action === 'buy' ? '#2b6cb0' : '#d53f8c')
          .attr('stroke-width', 1)
          .append('title')
          .text(d => `${d.action === 'buy' ? 'Buy' : 'Sell'}: ${d.amount}\nTime: ${d.rawTime}`);
          
      };

      this.topCards.forEach((card, i) => drawCard(card, true, i));
      this.bottomCards.forEach((card, i) => drawCard(card, false, i));
    },
    drawBands() {
        if (!this.chartState || !this.ohlc.length || !this.$refs.bandsOverlay) return;
        const { xScale, m, H, baseIndexScale, visibleData } = this.chartState;
        
        const overlay = d3.select(this.$refs.bandsOverlay);
        
        const wrapRect = this.$refs.wrap.getBoundingClientRect();
        overlay.attr('width', wrapRect.width).attr('height', wrapRect.height);
        overlay.selectAll('*').remove();
        
        const chartRect = this.$refs.chartBody.getBoundingClientRect();
        const chartLeft = chartRect.left - wrapRect.left;
        const chartTop = chartRect.top - wrapRect.top;
        
        const drawPolygons = (containerRef, cardsData, isTop) => {
              const container = this.$refs[containerRef];
              if (!container) return;
              const cardEls = container.querySelectorAll('.manipulation-card');
              
              cardEls.forEach((cardEl, i) => {
                const cardData = cardsData[i];
                if (!cardData) return;
                
                const cardRect = cardEl.getBoundingClientRect();
                if (cardRect.right < wrapRect.left || cardRect.left > wrapRect.right) return;
                
                const cardL = cardRect.left - wrapRect.left;
                const cardR = cardRect.right - wrapRect.left;
                
                const targetIdx = this.ohlc.findIndex(d => d.date.getTime() === cardData.ts);
                if (targetIdx === -1) return;
                
                let targetX, targetW;
                
                // If it's in the visible domain, use exact xScale
                const xPos = xScale(cardData.ts);
                if (xPos !== undefined) {
                  targetX = chartLeft + m.left + xPos;
                  targetW = xScale.bandwidth();
                } else {
                  // Otherwise, calculate an approximate off-screen position to point towards
                  let zoomedScale = baseIndexScale;
                  if (this.zoomTransform) {
                    zoomedScale = this.zoomTransform.rescaleX(baseIndexScale);
                  }
                  const slotX = zoomedScale(targetIdx);
                  const nextSlotX = zoomedScale(targetIdx + 1);
                  const slotWidth = nextSlotX - slotX;
                  
                  targetX = chartLeft + m.left + slotX + slotWidth * 0.125;
                  targetW = slotWidth * 0.75;
                }
          
          if (isTop) {
          const cardBottom = cardRect.bottom - wrapRect.top;
          const chartAreaTop = chartTop + m.top; // Align with 0 position
          // Draw a smooth curved band
          overlay.append('path')
            .attr('d', `M ${cardL},${cardBottom} L ${cardR},${cardBottom} C ${cardR},${cardBottom + 20} ${targetX + targetW},${chartAreaTop - 20} ${targetX + targetW},${chartAreaTop} L ${targetX},${chartAreaTop} C ${targetX},${chartAreaTop - 20} ${cardL},${cardBottom + 20} ${cardL},${cardBottom} Z`)
            .attr('fill', 'rgba(100, 150, 255, 0.15)')
            .attr('stroke', 'rgba(100, 150, 255, 0.3)')
            .attr('stroke-width', 1);
        } else {
          const cardTopPos = cardRect.top - wrapRect.top;
          const chartAreaBottom = chartTop + H - m.bottom; // Align with 0 position
          overlay.append('path')
            .attr('d', `M ${cardL},${cardTopPos} L ${cardR},${cardTopPos} C ${cardR},${cardTopPos - 20} ${targetX + targetW},${chartAreaBottom + 20} ${targetX + targetW},${chartAreaBottom} L ${targetX},${chartAreaBottom} C ${targetX},${chartAreaBottom + 20} ${cardL},${cardTopPos - 20} ${cardL},${cardTopPos} Z`)
            .attr('fill', 'rgba(100, 150, 255, 0.15)')
            .attr('stroke', 'rgba(100, 150, 255, 0.3)')
            .attr('stroke-width', 1);
        }
          });
        };
      
      drawPolygons('topCardsContainer', this.topCards, true);
      drawPolygons('bottomCardsContainer', this.bottomCards, false);
    },
  },
}
</script>

<style scoped>
.candlestick-container {
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
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a5568;
}

/* 粒度按钮面板 */
.granularity-panel {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.gran-btn {
  padding: 4px 10px;
  border: 1px solid #e8edf3;
  border-radius: 4px;
  background: #fff;
  color: #90a0b7;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  text-align: center;
  white-space: nowrap;
  transition: all 0.18s ease;
  letter-spacing: 0.5px;
  box-shadow: none;
}
.gran-btn:hover {
  background: #f4f7fd;
  color: #7090b8;
  border-color: #d0ddef;
}
.gran-btn--active {
  background: #edf3ff !important;
  color: #7090c8 !important;
  border-color: #d2e0f8 !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}

.candlestick-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
  width: 100%; height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.bands-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.manipulation-cards-container {
  position: relative;
  width: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 8px 12px;
  box-sizing: border-box;
  height: 160px;
}
.manipulation-cards-container.top-cards {
  height: 160px;
}
.scroll-x {
  overflow-x: auto;
  white-space: nowrap;
}

/* Custom class to move scrollbar to top */
.scroll-top {
  transform: rotateX(180deg);
}
.scroll-top > * {
  transform: rotateX(180deg);
}

/* Hide scrollbar for cleaner look, optional */
.scroll-x::-webkit-scrollbar {
  height: 6px;
}
.scroll-x::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.manipulation-card {
  display: inline-flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px;
  margin-right: 12px;
  min-width: 250px;
  height: 120px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  cursor: default;
  overflow: hidden; /* Ensure SVG doesn't overflow */
}
.manipulation-card.top-card {
  height: 120px;
}
.manipulation-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.card-time {
  font-size: 11px;
  color: #718096;
  margin-bottom: 2px;
  flex-shrink: 0;
}
.card-stats {
  font-size: 10px;
  color: #a0aec0;
  margin-bottom: 4px;
  flex-shrink: 0;
}
.card-svg {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.empty-cards {
  font-size: 12px;
  color: #a0aec0;
  font-style: italic;
  padding: 8px;
}

.chart-body-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  min-height: 0;
}

.chart-body {
  position: relative;
  width: 100%;
  height: 100%;
}
.candle-svg { display: block; width: 100%; height: 100%; }

.loading-mask {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #a0aec0; font-size: 13px;
}
</style>

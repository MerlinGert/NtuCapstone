<template>
  <div class="candlestick-snapshot-container">
    <div class="header">
      <h2>K-Line Snapshot — {{ snapshotData.currentCoin }} {{ snapshotData.currentGranularity }}</h2>
      <span v-if="selectedCount > 0" class="selection-badge">{{ selectedCount }} candles selected</span>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>

    <!-- ezio: Visualization area with top/bottom manipulation cards + bands + floating toolbar -->
    <div class="vis-area" ref="svgContainer">
      <!-- ezio: bands overlay SVG (connection curves between cards and K-line) -->
      <svg ref="bandsOverlay" class="bands-overlay"></svg>

      <!-- ezio: Upper manipulation cards (Round Trip) -->
      <div class="manipulation-cards-container scroll-x top-cards scroll-top" ref="topCardsContainer" @scroll="drawBands">
        <div class="manipulation-card top-card" v-for="(card, i) in snapshotData.topCards" :key="'top-'+i" :title="card.tooltip">
          <div class="card-time">{{ card.timeLabel }}</div>
          <div class="card-stats">{{ card.timeSpan }} | ${{ card.totalAmount }}</div>
          <svg :ref="'svg-top-'+i" class="card-svg" width="100%" height="100%"></svg>
        </div>
        <div v-if="!snapshotData.topCards || snapshotData.topCards.length === 0" class="empty-cards">No Round Trip manipulations</div>
      </div>

      <!-- ezio: K-line chart area -->
      <div class="chart-area" ref="chartArea">
        <svg ref="snapshotSvg"></svg>
      </div>

      <!-- ezio: Lower manipulation cards (Same Direction) -->
      <div class="manipulation-cards-container scroll-x bottom-cards" ref="bottomCardsContainer" @scroll="drawBands">
        <div class="manipulation-card" v-for="(card, i) in snapshotData.bottomCards" :key="'bottom-'+i" :title="card.tooltip">
          <div class="card-time">{{ card.timeLabel }}</div>
          <div class="card-stats">{{ card.timeSpan }} | ${{ card.totalAmount }}</div>
          <svg :ref="'svg-bottom-'+i" class="card-svg" width="100%" height="100%"></svg>
        </div>
        <div v-if="!snapshotData.bottomCards || snapshotData.bottomCards.length === 0" class="empty-cards">No Same Direction manipulations</div>
      </div>

      <!-- ezio: canvas covers entire vis-area so user can sketch over cards too -->
      <canvas ref="sketchCanvas" class="lasso-overlay"
          :class="'cursor-' + activeTool"></canvas>
      <!-- ezio: toolbar component -->
      <SnapshotToolbar class="floating-toolbar"
          :tool="activeTool" :color="penColor"
          @update:tool="activeTool = $event"
          @update:color="penColor = $event"
          @clear="clearSketches" />
    </div>

    <!-- ezio: Selected candles details panel -->
    <div class="details-panel">
      <div class="details-header" @click="detailsOpen = !detailsOpen">
        <span>{{ detailsOpen ? '▼' : '▶' }} Selected Candles Details</span>
        <span class="details-count" v-if="selectedCandles.length > 0">({{ selectedCandles.length }})</span>
      </div>
      <div v-if="detailsOpen" class="details-body">
        <div v-if="selectedCandles.length === 0" class="details-empty">
          Switch to Select tool and click on candles to select/deselect them.
        </div>
        <table v-else class="details-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Open</th>
              <th>High</th>
              <th>Low</th>
              <th>Close</th>
              <th>Manipulation</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, idx) in selectedCandles" :key="idx">
              <td>{{ formatDate(c.date) }}</td>
              <td>{{ formatVal(c.open) }}</td>
              <td>{{ formatVal(c.high) }}</td>
              <td>{{ formatVal(c.low) }}</td>
              <td :style="{ color: c.close >= c.open ? '#26a69a' : '#ef5350', fontWeight: 'bold' }">{{ formatVal(c.close) }}</td>
              <td>
                <span v-if="c.roundTripCount > 0" class="manipulation-tag rt">RT:{{ c.roundTripCount }}</span>
                <span v-if="c.sameDirectionCount > 0" class="manipulation-tag sd">SD:{{ c.sameDirectionCount }}</span>
                <span v-if="!c.roundTripCount && !c.sameDirectionCount">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ezio: Text input area -->
    <div class="input-area">
      <input
        type="text"
        v-model="inputText"
        placeholder="Enter annotation text..."
        @keyup.enter="handleInput"
        class="text-input"
      />
      <button @click="handleInput" class="send-btn">Send</button>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
// ezio: toolbar component
import SnapshotToolbar from './SnapshotToolbar.vue'

// ezio: reuse same color constants as CandlestickChart
const COLORS = {
  bull: '#26a69a',
  bear: '#ef5350',
  grid: '#eef2f7',
  axis: '#718096',
  volume: '#78909c',
}

// ezio: granularity-based date formatters
const FMT_MAP = {
  '1min': d => d3.timeFormat('%H:%M:%S')(d),
  '5min': d => d3.timeFormat('%H:%M')(d),
  '15min': d => d3.timeFormat('%H:%M')(d),
  '30min': d => d3.timeFormat('%H:%M')(d),
  '1H': d => d3.timeFormat('%m/%d %H:%M')(d),
  '1D': d => d3.timeFormat('%m/%d')(d),
  '3D': d => d3.timeFormat('%m/%d')(d),
  '1W': d => d3.timeFormat('%m/%d')(d),
}

export default {
  name: 'CandlestickSnapshot',
  components: { SnapshotToolbar },
  props: {
    snapshotData: { type: Object, required: true }
  },
  emits: ['close', 'snapshot-input'],
  data() {
    return {
      selectedCount: 0,
      selectedCandles: [],
      detailsOpen: true,
      inputText: '',
      // ezio: toolbar state
      activeTool: 'select',
      penColor: 'rgba(255,60,60,0.7)',
      sketchStrokes: [],
    }
  },
  watch: {
    activeTool() {
      this.redrawCanvas()
    }
  },
  mounted() {
    // ezio: initialize instance-level state
    this._selectableCandles = []
    this._selectedSet = new Set()
    this._currentTransform = d3.zoomIdentity

    this.$nextTick(() => {
      this.renderSnapshot()
      this.setupInteraction()
      // ezio: render manipulation card SVGs + connection bands
      this.drawCardBehaviors()
      this.$nextTick(() => this.drawBands())
      // ezio: apply initial zoom if available
      if (this.snapshotData.zoomTransform && this._zoom && this._zoomRect) {
        const iz = this.snapshotData.zoomTransform
        const t = d3.zoomIdentity.translate(iz.x, 0).scale(iz.k)
        this._zoomRect.call(this._zoom.transform, t)
      }
    })
  },
  methods: {
    // ezio: format date per current granularity
    formatDate(date) {
      const fmt = FMT_MAP[this.snapshotData.currentGranularity] || FMT_MAP['1H']
      if (date instanceof Date) return fmt(date)
      return fmt(new Date(date))
    },

    // ezio: format values avoiding scientific notation for small crypto values
    formatVal(val) {
      if (val === 0) return '0'
      if (Math.abs(val) < 0.000001) {
        return Number(val).toFixed(8).replace(/\.?0+$/, '')
      }
      if (Math.abs(val) < 1) {
        return Number(val).toFixed(6).replace(/\.?0+$/, '')
      }
      if (Math.abs(val) >= 1e9) {
        return `${(val / 1e9).toFixed(2).replace(/\.?0+$/, '')}B`
      }
      if (Math.abs(val) >= 1e6) {
        return `${(val / 1e6).toFixed(2).replace(/\.?0+$/, '')}M`
      }
      if (Math.abs(val) >= 1e3) {
        return `${(val / 1e3).toFixed(2).replace(/\.?0+$/, '')}K`
      }
      return Number(val).toFixed(2).replace(/\.?0+$/, '')
    },

    // ezio: allow empty text; capture full screenshot (SVG + sketch canvas composited)
    handleInput() {
      const svgEl = this.$refs.snapshotSvg
      const sketchCanvas = this.$refs.sketchCanvas
      const container = this.$refs.svgContainer
      const w = container ? container.offsetWidth : 800
      const h = container ? container.offsetHeight : 400
      const inputText = this.inputText
      const selectedItems = this.selectedCandles.map(c => ({
        date: c.date instanceof Date ? c.date.toISOString() : c.date,
        open: c.open, high: c.high, low: c.low, close: c.close,
        roundTripCount: c.roundTripCount,
        sameDirectionCount: c.sameDirectionCount
      }))

      // ezio: helper to emit and reset
      const emitResult = (dataUrl) => {
        this.$emit('snapshot-input', {
          text: inputText,
          selectedItems,
          sketchDataUrl: dataUrl
        })
        this.inputText = ''
      }

      // ezio: composite SVG + sketch canvas into one image
      if (svgEl) {
        const svgData = new XMLSerializer().serializeToString(svgEl)
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
        const url = URL.createObjectURL(svgBlob)
        const img = new Image()
        img.onload = () => {
          const c = document.createElement('canvas')
          c.width = w
          c.height = h
          const ctx = c.getContext('2d')
          ctx.fillStyle = '#ffffff'
          ctx.fillRect(0, 0, w, h)
          ctx.drawImage(img, 0, 0, w, h)
          URL.revokeObjectURL(url)
          if (sketchCanvas) ctx.drawImage(sketchCanvas, 0, 0)
          emitResult(c.toDataURL())
        }
        img.onerror = () => {
          URL.revokeObjectURL(url)
          emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null)
        }
        img.src = url
      } else {
        emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null)
      }
    },

    // ezio: clear all sketch strokes
    clearSketches() {
      this.sketchStrokes = []
      this.redrawCanvas()
    },

    // ezio: redraw persistent sketch strokes on canvas (zoom-aware X coordinates)
    redrawCanvas() {
      const canvas = this.$refs.sketchCanvas
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const t = this._currentTransform
      const margin = this._margin || { left: 40 }
      this.sketchStrokes.forEach(stroke => {
        if (stroke.points.length < 2) return
        ctx.beginPath()
        // ezio: convert data-space X back to screen-space using current zoom transform
        const sx = stroke.points[0][0]
        const sy = stroke.points[0][1]
        const screenX0 = t.applyX(sx - margin.left) + margin.left
        ctx.moveTo(screenX0, sy)
        for (let i = 1; i < stroke.points.length; i++) {
          const px = stroke.points[i][0]
          const py = stroke.points[i][1]
          const screenX = t.applyX(px - margin.left) + margin.left
          ctx.lineTo(screenX, py)
        }
        ctx.strokeStyle = stroke.color
        ctx.lineWidth = stroke.width
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        ctx.setLineDash([])
        ctx.stroke()
      })
    },

    // ezio: find candle at click position
    _findClickedCandle(x, y) {
      for (const item of this._selectableCandles) {
        if (x >= item.screenX && x <= item.screenX + item.screenWidth &&
            y >= item.screenTop && y <= item.screenBottom) {
          return item
        }
      }
      return null
    },

    // ezio: update SVG highlight for selected candles
    _updateHighlight() {
      const selectedSet = this._selectedSet
      const svg = d3.select(this.$refs.snapshotSvg)

      svg.selectAll('.candle').each(function () {
        const g = d3.select(this)
        const idx = +g.attr('data-idx')
        if (selectedSet.has(idx)) {
          g.select('rect')
            .attr('stroke', '#fdd835')
            .attr('stroke-width', 3)
          g.select('line')
            .attr('stroke', '#fdd835')
            .attr('stroke-width', 3)
        } else {
          const isUp = g.attr('data-up') === 'true'
          const color = isUp ? COLORS.bull : COLORS.bear
          g.select('rect')
            .attr('stroke', null)
            .attr('stroke-width', null)
          g.select('line')
            .attr('stroke', color)
            .attr('stroke-width', 1)
        }
      })

      // ezio: sync Vue state
      this.selectedCandles = Array.from(selectedSet).map(idx => this._selectableCandles.find(c => c.idx === idx)?.data).filter(Boolean)
      this.selectedCount = this.selectedCandles.length
    },

    // ezio: zoom handler — re-render chart from full ohlc dataset with new visible window
    handleZoom(event) {
      this._currentTransform = event.transform
      this._renderWithTransform(event.transform)
      this.redrawCanvas()
      this.$nextTick(() => this.drawBands())
    },

    // ezio: render chart with a given zoom transform (semantic zoom)
    _renderWithTransform(transform) {
      const data = this.snapshotData
      if (!data) return

      const container = this.$refs.chartArea
      const W = container.offsetWidth
      const H = container.offsetHeight
      const m = { top: 40, right: 20, bottom: 40, left: 40 }
      const iW = W - m.left - m.right
      const iH = H - m.top - m.bottom
      this._margin = m

      const ohlc = data.ohlc

      // ezio: semantic zoom — determine visible data window from transform
      const baseIndexScale = d3.scaleLinear()
        .domain([0, ohlc.length - 1])
        .range([0, iW])

      let startIndex = 0
      let endIndex = ohlc.length - 1

      if (transform && transform.k !== 1) {
        const zoomedScale = transform.rescaleX(baseIndexScale)
        const domain = zoomedScale.domain()
        startIndex = Math.max(0, Math.floor(domain[0]))
        endIndex = Math.min(ohlc.length - 1, Math.ceil(domain[1]))
        if (endIndex - startIndex < 5) {
          const mid = (startIndex + endIndex) / 2
          startIndex = Math.max(0, Math.floor(mid - 2.5))
          endIndex = Math.min(ohlc.length - 1, Math.ceil(mid + 2.5))
        }
      }

      const visibleData = ohlc.slice(startIndex, endIndex + 1)

      // ezio: X scale based only on visible data
      const xScale = d3.scaleBand()
        .domain(visibleData.map(d => d.date))
        .range([0, iW])
        .padding(0.25)

      // ezio: Y scale for candles
      const [minL, maxH] = [
        d3.min(visibleData, d => d.low),
        d3.max(visibleData, d => d.high),
      ]
      const pad = (maxH - minL) * 0.06 || 1e-9
      const yScale = d3.scaleLinear()
        .domain([minL - pad, maxH + pad])
        .range([iH, 0])

      // ezio: bar chart scales
      const maxRoundTrip = d3.max(visibleData, d => d.roundTripCount) || 1
      const maxSameDirection = d3.max(visibleData, d => d.sameDirectionCount) || 1
      const barHeight = 25

      const yTopBarScale = d3.scaleLinear()
        .domain([0, maxRoundTrip])
        .range([0, barHeight])

      const yBottomBarScale = d3.scaleLinear()
        .domain([0, maxSameDirection])
        .range([0, barHeight])

      // ezio: render SVG
      const svg = d3.select(this.$refs.snapshotSvg)
        .attr('width', W)
        .attr('height', H)
      svg.selectAll('*').remove()

      const defs = svg.append('defs')
      defs.append('clipPath')
        .attr('id', 'snapshot-zoom-clip')
        .append('rect')
        .attr('width', iW)
        .attr('height', H)
        .attr('y', -m.top)

      const g = svg.append('g')
        .attr('transform', `translate(${m.left},${m.top})`)

      const chartBody = g.append('g').attr('clip-path', 'url(#snapshot-zoom-clip)')
      const zoomGroup = chartBody.append('g').attr('class', 'zoom-group')

      // ezio: grid lines
      g.append('g')
        .selectAll('line')
        .data(yScale.ticks(5))
        .enter()
        .append('line')
        .attr('x1', 0).attr('x2', iW)
        .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
        .attr('stroke', COLORS.grid).attr('stroke-width', 1)

      // ezio: boundary lines
      g.append('line')
        .attr('x1', 0).attr('x2', iW)
        .attr('y1', 0).attr('y2', 0)
        .attr('stroke', '#cbd5e1').attr('stroke-width', 1).attr('stroke-dasharray', '4,2')
      g.append('line')
        .attr('x1', 0).attr('x2', iW)
        .attr('y1', iH).attr('y2', iH)
        .attr('stroke', '#cbd5e1').attr('stroke-width', 1).attr('stroke-dasharray', '4,2')

      // ezio: Y axis
      g.append('g')
        .call(d3.axisLeft(yScale).ticks(5))
        .call(ax => ax.select('.domain').remove())
        .call(ax => ax.selectAll('.tick line')
          .attr('x2', iW)
          .attr('stroke', '#e2e8f0')
          .attr('stroke-dasharray', '2,2'))
        .selectAll('text')
        .style('fill', COLORS.axis)
        .style('font-size', '9px')

      // ezio: X axis
      const fmt = FMT_MAP[data.currentGranularity] || FMT_MAP['1H']
      const maxTicks = Math.max(2, Math.floor(iW / 90))
      const step = Math.max(1, Math.ceil(visibleData.length / maxTicks))
      const tickDates = visibleData.filter((_, i) => i % step === 0).map(d => d.date)

      g.append('g')
        .attr('transform', `translate(0,${iH})`)
        .call(d3.axisBottom(xScale)
          .tickValues(tickDates)
          .tickFormat(fmt)
          .tickSizeInner(0)
          .tickSizeOuter(0))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text')
        .style('fill', COLORS.axis)
        .style('font-size', '8px')
        .attr('dy', '-5px')
        .style('text-anchor', 'middle')

      // ezio: manipulation highlight masks
      const bw = xScale.bandwidth()
      zoomGroup.append('g').attr('class', 'manipulation-masks')
        .selectAll('rect')
        .data(visibleData.filter(d => d.roundTripCount > 0 || d.sameDirectionCount > 0))
        .enter()
        .append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', 0)
        .attr('width', bw)
        .attr('height', iH)
        .attr('fill', 'rgba(100, 150, 255, 0.08)')
        .style('pointer-events', 'none')

      // ezio: candlestick wicks and bodies
      const candles = zoomGroup.append('g')
        .selectAll('g.candle')
        .data(visibleData)
        .enter()
        .append('g')
        .attr('class', 'candle')
        .attr('data-idx', (d, i) => startIndex + i)
        .attr('data-up', d => d.close >= d.open ? 'true' : 'false')

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

      // ezio: top bar chart (Round Trip)
      zoomGroup.append('g').attr('class', 'top-bars')
        .selectAll('rect')
        .data(visibleData.filter(d => d.roundTripCount > 0))
        .enter()
        .append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', d => -yTopBarScale(d.roundTripCount))
        .attr('width', bw)
        .attr('height', d => yTopBarScale(d.roundTripCount))
        .attr('fill', COLORS.volume)
        .attr('rx', 1)

      // ezio: bottom bar chart (Same Direction)
      zoomGroup.append('g').attr('class', 'bottom-bars')
        .selectAll('rect')
        .data(visibleData.filter(d => d.sameDirectionCount > 0))
        .enter()
        .append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', iH)
        .attr('width', bw)
        .attr('height', d => yBottomBarScale(d.sameDirectionCount))
        .attr('fill', COLORS.volume)
        .attr('rx', 1)

      // ezio: build selectable candles for hit detection
      this._selectableCandles = visibleData.map((d, i) => ({
        idx: startIndex + i,
        screenX: m.left + xScale(d.date),
        screenWidth: bw,
        screenTop: m.top,
        screenBottom: m.top + iH,
        data: d
      }))

      // ezio: save chart state for drawBands
      this._chartState = { xScale, m, H, W, iW, iH, baseIndexScale, visibleData, ohlc }

      // ezio: setup zoom rect (invisible, captures wheel events via d3.zoom)
      if (!this._zoom) {
        const vm = this
        this._zoom = d3.zoom()
          .scaleExtent([1, Math.max(1, ohlc.length / 10)])
          .on('zoom', (event) => {
            if (!event.sourceEvent && !event.isProgrammatic) return
            vm.handleZoom(event)
          })

        const zoomRect = svg.append('rect')
          .attr('width', iW)
          .attr('height', iH)
          .attr('transform', `translate(${m.left},${m.top})`)
          .style('fill', 'none')
          .style('pointer-events', 'none')

        zoomRect.call(this._zoom)
        this._zoomRect = zoomRect
      }

      // ezio: re-apply highlight after re-render
      if (this._selectedSet.size > 0) {
        this._updateHighlight()
      }
    },

    // ezio: parse UTC date strings for cross-browser compatibility
    parseUtcDate(s) {
      if (!s) return new Date(NaN)
      const iso = `${String(s).replace(' UTC', '').replace(' ', 'T')}Z`
      return new Date(iso)
    },

    // ezio: render manipulation card SVGs (adapted from CandlestickChart.drawCardBehaviors)
    drawCardBehaviors() {
      const drawCard = (cardData, isTop, index) => {
        const refName = `svg-${isTop ? 'top' : 'bottom'}-${index}`
        const svgEls = this.$refs[refName]
        if (!svgEls?.[0]) return
        const svgNode = svgEls[0]

        const W = svgNode.clientWidth || 200
        const H = svgNode.clientHeight || 70
        d3.select(svgNode).attr('height', H)

        const svg = d3.select(svgNode)
        svg.selectAll('*').remove()

        let minTs = Infinity
        let maxTs = -Infinity
        const localUniqueUsers = new Set(cardData.uniqueUsers)

        cardData.rawManipulations.forEach(m => {
          if (m.transactions) {
            m.transactions.forEach(tx => {
              const tsStr = tx.timestamp || tx.time
              if (tsStr) {
                const ts = this.parseUtcDate(tsStr).getTime()
                if (ts < minTs) minTs = ts
                if (ts > maxTs) maxTs = ts
              }
              const user = tx.trader || tx.user
              if (user) localUniqueUsers.add(user)
            })
          }
        })

        const allUsersList = Array.from(localUniqueUsers)
        if (allUsersList.length === 0) return

        const timePad = Math.max((maxTs - minTs) * 0.05, 60000)
        const mLeft = 40
        const mRight = 10

        const xScale = d3.scaleTime()
          .domain([new Date(minTs - timePad), new Date(maxTs + timePad)])
          .range([mLeft, W - mRight])

        const yScale = d3.scalePoint()
          .domain(allUsersList)
          .range([10, H - 10])
          .padding(0.5)

        // Draw user lines
        svg.selectAll('.user-line')
          .data(allUsersList)
          .enter()
          .append('line')
          .attr('class', 'user-line')
          .attr('x1', mLeft).attr('x2', W - mRight)
          .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
          .attr('stroke', '#e2e8f0').attr('stroke-width', 1)

        // Draw user labels
        svg.selectAll('.user-label')
          .data(allUsersList)
          .enter()
          .append('text')
          .attr('class', 'user-label')
          .attr('x', mLeft - 5)
          .attr('y', d => yScale(d))
          .attr('dy', '0.32em')
          .attr('text-anchor', 'end')
          .attr('fill', '#718096')
          .style('font-size', '9px')
          .text(d => `${d.substring(0, 3)}..`)
          .append('title')
          .text(d => d)

        // Collect events
        let allEvents = []
        let maxAmount = 0

        cardData.rawManipulations.forEach(m => {
          if (m.transactions) {
            m.transactions.forEach(tx => {
              const tsStr = tx.timestamp || tx.time
              if (!tsStr) return
              const evTs = this.parseUtcDate(tsStr).getTime()
              const user = tx.trader || tx.user
              if (user && allUsersList.includes(user) &&
                  evTs >= minTs - timePad && evTs <= maxTs + timePad) {
                const amount = parseFloat(tx.amount || tx.quantity) || 0
                if (amount > maxAmount) maxAmount = amount
                allEvents.push({
                  user, ts: evTs, amount,
                  action: tx.action_type || tx.action,
                  rawTime: tsStr,
                })
              }
            })
          }
        })

        const yPadding = 10
        const availableH = H - yPadding * 2
        const userCount = allUsersList.length
        const rowHeight = userCount > 1 ? availableH / (userCount - 1) : availableH
        const maxRadius = Math.min(6, Math.max(1.5, rowHeight / 2 - 0.5))
        const minRadius = Math.min(2, maxRadius * 0.3)

        const rScale = d3.scaleSqrt()
          .domain([0, maxAmount || 1])
          .range([minRadius, maxRadius])

        svg.selectAll('.event-point')
          .data(allEvents)
          .enter()
          .append('circle')
          .attr('class', 'event-point')
          .attr('cx', d => xScale(d.ts))
          .attr('cy', d => yScale(d.user))
          .attr('r', d => rScale(d.amount))
          .attr('fill', d => d.action === 'buy' ? '#4299e1' : '#ed64a6')
          .attr('opacity', 0.5)
          .attr('stroke', d => d.action === 'buy' ? '#2b6cb0' : '#d53f8c')
          .attr('stroke-width', 1)
          .append('title')
          .text(d => `${d.action === 'buy' ? 'Buy' : 'Sell'}: ${d.amount}\nTime: ${d.rawTime}`)
      }

      const data = this.snapshotData
      if (data.topCards) {
        data.topCards.forEach((card, i) => drawCard(card, true, i))
      }
      if (data.bottomCards) {
        data.bottomCards.forEach((card, i) => drawCard(card, false, i))
      }
    },

    // ezio: draw connection bands between manipulation cards and K-line positions
    drawBands() {
      if (!this._chartState || !this.$refs.bandsOverlay) return
      const { xScale, m, H, baseIndexScale, ohlc } = this._chartState

      const overlay = d3.select(this.$refs.bandsOverlay)
      const wrapEl = this.$refs.svgContainer
      const wrapRect = wrapEl.getBoundingClientRect()
      overlay.attr('width', wrapRect.width).attr('height', wrapRect.height)
      overlay.selectAll('*').remove()

      const chartEl = this.$refs.chartArea
      const chartRect = chartEl.getBoundingClientRect()
      const chartLeft = chartRect.left - wrapRect.left
      const chartTop = chartRect.top - wrapRect.top

      const drawPolygons = (containerRef, cardsData, isTop) => {
        const container = this.$refs[containerRef]
        if (!container || !cardsData) return
        const cardEls = container.querySelectorAll('.manipulation-card')

        cardEls.forEach((cardEl, i) => {
          const cardData = cardsData[i]
          if (!cardData) return

          const cardRect = cardEl.getBoundingClientRect()
          if (cardRect.right < wrapRect.left || cardRect.left > wrapRect.right) return

          const cardL = cardRect.left - wrapRect.left
          const cardR = cardRect.right - wrapRect.left

          const targetIdx = ohlc.findIndex(d => d.date.getTime() === cardData.ts)
          if (targetIdx === -1) return

          let targetX, targetW
          const xPos = xScale(cardData.ts)
          if (xPos !== undefined) {
            targetX = chartLeft + m.left + xPos
            targetW = xScale.bandwidth()
          } else {
            let zoomedScale = baseIndexScale
            if (this._currentTransform && this._currentTransform.k !== 1) {
              zoomedScale = this._currentTransform.rescaleX(baseIndexScale)
            }
            const slotX = zoomedScale(targetIdx)
            const nextSlotX = zoomedScale(targetIdx + 1)
            const slotWidth = nextSlotX - slotX
            targetX = chartLeft + m.left + slotX + slotWidth * 0.125
            targetW = slotWidth * 0.75
          }

          if (isTop) {
            const cardBottom = cardRect.bottom - wrapRect.top
            const chartAreaTop = chartTop + m.top
            overlay.append('path')
              .attr('d', `M ${cardL},${cardBottom} L ${cardR},${cardBottom} C ${cardR},${cardBottom + 20} ${targetX + targetW},${chartAreaTop - 20} ${targetX + targetW},${chartAreaTop} L ${targetX},${chartAreaTop} C ${targetX},${chartAreaTop - 20} ${cardL},${cardBottom + 20} ${cardL},${cardBottom} Z`)
              .attr('fill', 'rgba(100, 150, 255, 0.15)')
              .attr('stroke', 'rgba(100, 150, 255, 0.3)')
              .attr('stroke-width', 1)
          } else {
            const cardTopPos = cardRect.top - wrapRect.top
            const chartAreaBottom = chartTop + H - m.bottom
            overlay.append('path')
              .attr('d', `M ${cardL},${cardTopPos} L ${cardR},${cardTopPos} C ${cardR},${cardTopPos - 20} ${targetX + targetW},${chartAreaBottom + 20} ${targetX + targetW},${chartAreaBottom} L ${targetX},${chartAreaBottom} C ${targetX},${chartAreaBottom + 20} ${cardL},${cardTopPos - 20} ${cardL},${cardTopPos} Z`)
              .attr('fill', 'rgba(100, 150, 255, 0.15)')
              .attr('stroke', 'rgba(100, 150, 255, 0.3)')
              .attr('stroke-width', 1)
          }
        })
      }

      drawPolygons('topCardsContainer', this.snapshotData.topCards, true)
      drawPolygons('bottomCardsContainer', this.snapshotData.bottomCards, false)
    },

    // ezio: initial render
    renderSnapshot() {
      const data = this.snapshotData
      if (!data) return

      const container = this.$refs.chartArea
      const W = container.offsetWidth
      const H = container.offsetHeight
      const m = { top: 40, right: 20, bottom: 40, left: 40 }
      this._margin = m

      // ezio: render with identity transform first (shows visibleData window)
      this._renderWithTransform(d3.zoomIdentity)
    },

    // ezio: canvas overlay interaction setup (adapted from BehaviorSnapshot pattern)
    setupInteraction() {
      const canvas = this.$refs.sketchCanvas
      // ezio: size canvas to entire vis-area so sketching covers cards too
      const container = this.$refs.svgContainer
      canvas.width = container.offsetWidth
      canvas.height = container.offsetHeight
      const ctx = canvas.getContext('2d')
      const vm = this

      let isDrawing = false
      let currentPoints = []
      let dragStartX = 0
      let dragStartY = 0
      let isPanning = false

      // ezio: eraser hit-test helper — data-space aware
      const ERASER_RADIUS = 10
      const isNearStroke = (stroke, x, y) => {
        const t = vm._currentTransform
        const margin = vm._margin || { left: 40 }
        return stroke.points.some(([px, py]) => {
          const screenX = t.applyX(px - margin.left) + margin.left
          return Math.hypot(screenX - x, py - y) < ERASER_RADIUS
        })
      }

      // ezio: forward wheel events from canvas to d3.zoom for X-axis zoom
      canvas.addEventListener('wheel', (e) => {
        e.preventDefault()
        if (!vm._zoom || !vm._zoomRect) return
        const rect = canvas.getBoundingClientRect()
        const direction = e.deltaY > 0 ? 0.9 : 1.1
        const point = [e.clientX - rect.left - vm._margin.left, e.clientY - rect.top - vm._margin.top]
        vm._zoomRect.call(vm._zoom.scaleBy, direction, point)
      }, { passive: false })

      canvas.addEventListener('mousedown', (e) => {
        isDrawing = true
        isPanning = false
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        dragStartX = x
        dragStartY = y
        currentPoints = [[x, y]]

        if (vm.activeTool === 'eraser') {
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearStroke(s, x, y))
        }
        vm.redrawCanvas()
      })

      canvas.addEventListener('mousemove', (e) => {
        if (!isDrawing) return
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        currentPoints.push([x, y])

        if (vm.activeTool === 'pen') {
          vm.redrawCanvas()
          if (currentPoints.length >= 2) {
            ctx.beginPath()
            ctx.moveTo(currentPoints[0][0], currentPoints[0][1])
            for (let i = 1; i < currentPoints.length; i++) {
              ctx.lineTo(currentPoints[i][0], currentPoints[i][1])
            }
            ctx.strokeStyle = vm.penColor
            ctx.lineWidth = 2
            ctx.lineCap = 'round'
            ctx.lineJoin = 'round'
            ctx.setLineDash([])
            ctx.stroke()
          }
        } else if (vm.activeTool === 'eraser') {
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearStroke(s, x, y))
          vm.redrawCanvas()
        } else {
          // ezio: select mode — drag to pan if moved > 5px
          const dx = x - dragStartX
          const dy = y - dragStartY
          if (!isPanning && Math.hypot(dx, dy) > 5) {
            isPanning = true
          }
          if (isPanning && vm._zoom && vm._zoomRect) {
            const prev = currentPoints[currentPoints.length - 2]
            const deltaX = x - prev[0]
            vm._zoomRect.call(vm._zoom.translateBy, deltaX, 0)
          }
        }
      })

      canvas.addEventListener('mouseup', (e) => {
        if (!isDrawing) return
        isDrawing = false

        const hasMoved = currentPoints.length > 3
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top

        if (vm.activeTool === 'pen') {
          if (hasMoved && currentPoints.length >= 2) {
            // ezio: convert screen coordinates to data-space for zoom-aware storage
            const t = vm._currentTransform
            const margin = vm._margin
            const dataPoints = currentPoints.map(([px, py]) => {
              const dataX = t.invertX(px - margin.left) + margin.left
              return [dataX, py]
            })
            vm.sketchStrokes.push({
              points: dataPoints,
              color: vm.penColor,
              width: 2
            })
          }
          vm.redrawCanvas()
        } else if (vm.activeTool === 'eraser') {
          vm.redrawCanvas()
        } else {
          // ezio: select tool
          if (isPanning) {
            isPanning = false
          } else {
            // Click to toggle candle selection
            const candle = vm._findClickedCandle(x, y)
            if (candle) {
              if (vm._selectedSet.has(candle.idx)) {
                vm._selectedSet.delete(candle.idx)
              } else {
                vm._selectedSet.add(candle.idx)
              }
              vm._updateHighlight()
            }
          }
        }
        currentPoints = []
      })
    }
  }
}
</script>

<style scoped>
/* ezio: container — wider than TokenSnapshot for K-line chart */
.candlestick-snapshot-container {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  width: 90%;
  max-width: 900px;
  height: 90vh;
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

/* ezio: floating toolbar positioning */
.floating-toolbar {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 2;
}

/* ezio: cursor per tool */
.lasso-overlay.cursor-select { cursor: crosshair; }
.lasso-overlay.cursor-pen    { cursor: crosshair; }
.lasso-overlay.cursor-eraser { cursor: pointer; }

/* ezio: bands overlay SVG */
.bands-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

/* ezio: vis-area is a flex column containing top cards, chart, bottom cards */
.vis-area {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ezio: chart area holds SVG + canvas overlay */
.chart-area {
  flex: 1;
  min-height: 0;
  position: relative;
}

.chart-area svg {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.lasso-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* ezio: manipulation cards containers */
.manipulation-cards-container {
  position: relative;
  width: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 4px 8px;
  box-sizing: border-box;
  height: 120px;
}
.scroll-x {
  overflow-x: auto;
  white-space: nowrap;
}
.scroll-top {
  transform: rotateX(180deg);
}
.scroll-top > * {
  transform: rotateX(180deg);
}
.scroll-x::-webkit-scrollbar {
  height: 4px;
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
  padding: 6px;
  margin-right: 8px;
  min-width: 200px;
  height: 90px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
}
.manipulation-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.card-time {
  font-size: 10px;
  color: #718096;
  margin-bottom: 1px;
  flex-shrink: 0;
}
.card-stats {
  font-size: 9px;
  color: #a0aec0;
  margin-bottom: 2px;
  flex-shrink: 0;
}
.card-svg {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.empty-cards {
  font-size: 11px;
  color: #a0aec0;
  font-style: italic;
  padding: 6px;
}

.details-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
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

/* ezio: manipulation tags */
.manipulation-tag {
  display: inline-block;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: bold;
  margin-right: 3px;
}
.manipulation-tag.rt {
  background: #fee2e2;
  color: #dc2626;
}
.manipulation-tag.sd {
  background: #fef3c7;
  color: #d97706;
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

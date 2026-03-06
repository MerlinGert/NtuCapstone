<template>
  <div class="candlestick-wrap" ref="wrap">
    <div class="chart-body" ref="chartBody">
      <svg ref="svg" class="candle-svg"></svg>
      <div v-if="loading" class="loading-mask">Loading...</div>
      <div v-if="!loading && ohlc.length === 0" class="loading-mask">No data</div>
      <span class="price-tag" v-if="lastClose !== null">
        {{ lastClose.toExponential(4) }} USD
      </span>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'

const COLORS = {
  bull: '#26a69a',
  bear: '#ef5350',
  grid: '#eef2f7',
  axis: '#718096',
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
    granularity: { type: String, default: '1D' },
  },
  data() {
    return {
      actOhlc: null,
      ohlc: [],
      loading: true,
      lastClose: null,
      resizeObs: null,
    }
  },
  watch: {
    granularity() {
      this.refresh()
    },
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
    async loadData() {
      this.loading = true
      try {
        const res = await fetch('/ACT_OHLC.json')
        this.actOhlc = await res.json()
      } catch (e) {
        console.error('CandlestickChart: failed to load ACT_OHLC.json', e)
        this.actOhlc = {}
      }
      this.loading = false
      this.refresh()
    },

    refresh() {
      if (!this.actOhlc) { this.ohlc = []; return }
      const raw = this.actOhlc[this.granularity] || []
      this.ohlc = raw.map(d => ({
        date:  new Date(d.t + ' UTC'),
        open:  d.o,
        high:  d.h,
        low:   d.l,
        close: d.c,
        vol:   d.v,
      }))
      this.lastClose = this.ohlc.length ? this.ohlc[this.ohlc.length - 1].close : null
      this.$nextTick(() => this.draw())
    },

    draw() {
      const el    = this.$refs.chartBody
      const svgEl = this.$refs.svg
      if (!el || !svgEl || this.ohlc.length === 0) return

      const W = el.clientWidth  || 400
      const H = el.clientHeight || 200
      const m = { top: 8, right: 80, bottom: 26, left: 8 }
      const iW = W - m.left - m.right
      const iH = H - m.top  - m.bottom

      const svg = d3.select(svgEl).attr('width', W).attr('height', H)
      svg.selectAll('*').remove()
      const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`)
      const data = this.ohlc

      // X scale
      const xScale = d3.scaleBand()
        .domain(data.map(d => d.date))
        .range([0, iW])
        .padding(0.25)

      // Y scale
      const [minL, maxH] = [d3.min(data, d => d.low), d3.max(data, d => d.high)]
      const pad = (maxH - minL) * 0.06 || 1e-9
      const yScale = d3.scaleLinear()
        .domain([minL - pad, maxH + pad])
        .range([iH, 0])

      // Grid
      g.append('g').selectAll('line')
        .data(yScale.ticks(5))
        .enter().append('line')
          .attr('x1', 0).attr('x2', iW)
          .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
          .attr('stroke', COLORS.grid).attr('stroke-width', 1)

      // Y axis (right)
      g.append('g').attr('transform', `translate(${iW},0)`)
        .call(d3.axisRight(yScale).ticks(5).tickFormat(d => d.toExponential(2)))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text').style('fill', COLORS.axis).style('font-size', '9px')

      // X axis
      const fmtMap = {
        '1H': d => d3.timeFormat('%m/%d %H:%M')(d),
        '1D': d => d3.timeFormat('%m/%d')(d),
        '3D': d => d3.timeFormat('%m/%d')(d),
        '1W': d => d3.timeFormat('%m/%d')(d),
      }
      const fmt  = fmtMap[this.granularity]
      const step = Math.max(1, Math.ceil(data.length / Math.max(3, Math.floor(iW / 70))))
      const tickDates = data.filter((_, i) => i % step === 0).map(d => d.date)

      g.append('g').attr('transform', `translate(0,${iH})`)
        .call(d3.axisBottom(xScale).tickValues(tickDates).tickFormat(fmt))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text').style('fill', COLORS.axis).style('font-size', '9px').attr('dy', '1em')

      // Candles
      const bw = xScale.bandwidth()
      const candles = g.append('g').selectAll('g.candle')
        .data(data).enter().append('g').attr('class', 'candle')

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

      // Tooltip
      const tooltip = d3.select(this.$refs.wrap)
        .selectAll('.candle-tooltip').data([null]).join('div')
        .attr('class', 'candle-tooltip')
        .style('position', 'fixed').style('pointer-events', 'none')
        .style('opacity', 0).style('background', 'rgba(30,39,55,0.88)')
        .style('color', '#e2e8f0').style('border-radius', '6px')
        .style('padding', '6px 10px').style('font-size', '11px')
        .style('line-height', '1.6').style('z-index', 9999).style('white-space', 'nowrap')

      const bandStep = xScale.step()
      g.append('rect')
        .attr('width', iW).attr('height', iH).attr('fill', 'transparent')
        .on('mousemove', function(event) {
          const [mx] = d3.pointer(event)
          const idx = Math.max(0, Math.min(Math.floor(mx / bandStep), data.length - 1))
          const d = data[idx]
          if (!d) return
          const color = d.close >= d.open ? COLORS.bull : COLORS.bear
          const upDown = d.close >= d.open ? '\u25b2' : '\u25bc'
          tooltip.style('opacity', 1)
            .style('left', (event.clientX + 14) + 'px')
            .style('top',  (event.clientY - 14) + 'px')
            .html(`
              <div style="color:${color};font-weight:bold;">${upDown} ${fmt(d.date)}</div>
              <div>O: ${d.open.toExponential(4)}</div>
              <div>H: ${d.high.toExponential(4)}</div>
              <div>L: ${d.low.toExponential(4)}</div>
              <div>C: <b>${d.close.toExponential(4)}</b></div>
              <div style="color:#a0aec0;">Txns: ${d.vol}</div>
            `)
        })
        .on('mouseleave', () => tooltip.style('opacity', 0))
    },
  },
}
</script>

<style scoped>
.candlestick-wrap {
  width: 100%;
  height: 100%;
  background: #ffffff;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.chart-body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}
.candle-svg { display: block; width: 100%; height: 100%; }
.price-tag {
  position: absolute;
  top: 4px; left: 8px;
  font-size: 11px;
  font-family: 'Courier New', monospace;
  color: #26a69a;
  font-weight: 700;
  pointer-events: none;
  z-index: 2;
}
.loading-mask {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #a0aec0; font-size: 13px;
}
</style>
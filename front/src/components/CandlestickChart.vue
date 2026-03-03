<template>
  <div class="candlestick-wrap" ref="wrap">
    <!-- 宸ュ叿鏍?-->
    <div class="toolbar">
      <!-- Token 鍒囨崲 -->
      <div class="tab-group token-group">
        <button
          v-for="tk in tokens"
          :key="tk.key"
          :class="['tab-btn', { active: currentToken === tk.key }]"
          @click="setToken(tk.key)"
        >{{ tk.label }}</button>
      </div>

      <span class="divider">|</span>

      <!-- 绮掑害鍒囨崲 -->
      <div class="tab-group">
        <button
          v-for="g in granularities"
          :key="g.key"
          :class="['tab-btn', { active: currentGranularity === g.key }]"
          @click="setGranularity(g.key)"
        >{{ g.label }}</button>
      </div>

      <span class="price-tag" v-if="lastClose !== null">
        {{ lastClose.toExponential(4) }} USD
      </span>
    </div>

    <!-- 鍥捐〃涓讳綋 -->
    <div class="chart-body" ref="chartBody">
      <svg ref="svg" class="candle-svg"></svg>
      <div v-if="loading" class="loading-mask">Loading...</div>
      <div v-if="!loading && ohlc.length === 0" class="loading-mask">No data</div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import csvUrl from '../assets/RENA_Transfer_Price.csv?url'

const COLORS = {
  bull:    '#26a69a',
  bear:    '#ef5350',
  grid:    '#eef2f7',
  axis:    '#718096',
}

const GRANULARITIES = [
  { key: '1H', label: '1H', ms: 3_600_000 },
  { key: '1D', label: '1D', ms: 86_400_000 },
  { key: '3D', label: '3D', ms: 3 * 86_400_000 },
  { key: '1W', label: '1W', ms: 7 * 86_400_000 },
]

const TOKENS = [
  { key: 'ACT',  label: 'ACT'  },
  { key: 'RENA', label: 'RENA' },
]

export default {
  name: 'CandlestickChart',
  data() {
    return {
      tokens: TOKENS,
      granularities: GRANULARITIES,
      currentToken: 'ACT',
      currentGranularity: '1D',

      // RENA raw ticks [{time: Date, price: number}]
      renaRaw: [],
      // ACT pre-aggregated { '1H': [...], '1D': [...], '3D': [...], '1W': [...] }
      actOhlc: null,

      ohlc: [],
      loading: true,
      lastClose: null,
      resizeObs: null,
    }
  },
  mounted() {
    this.loadAll()
    this.resizeObs = new ResizeObserver(() => this.draw())
    this.resizeObs.observe(this.$refs.chartBody)
  },
  beforeUnmount() {
    if (this.resizeObs) this.resizeObs.disconnect()
  },
  methods: {
    /** 骞惰鍔犺浇 ACT JSON 鍜?RENA CSV */
    async loadAll() {
      this.loading = true
      await Promise.all([this.loadACT(), this.loadRENA()])
      this.loading = false
      this.refresh()
    },

    /** 鍔犺浇 ACT 棰勮绠?OHLC JSON */
    async loadACT() {
      try {
        const res = await fetch('/ACT_OHLC.json')
        this.actOhlc = await res.json()
      } catch (e) {
        console.error('CandlestickChart: failed to load ACT_OHLC.json', e)
        this.actOhlc = {}
      }
    },

    /** 鍔犺浇 RENA CSV锛堜繚鎸佸師鏈夐€昏緫锛?*/
    async loadRENA() {
      try {
        const data = await d3.csv(csvUrl, row => {
          const raw = row.block_time ? row.block_time.replace(' UTC', '') : null
          const t = raw ? new Date(raw) : null
          const p = row.dex_price ? +row.dex_price : null
          if (!t || !p || isNaN(t) || isNaN(p)) return null
          return { time: t, price: p }
        })
        this.renaRaw = data.filter(Boolean).sort((a, b) => a.time - b.time)
      } catch (e) {
        console.error('CandlestickChart: failed to load RENA CSV', e)
        this.renaRaw = []
      }
    },

    /** 鍒囨崲 Token */
    setToken(key) {
      this.currentToken = key
      this.refresh()
    },

    /** 鍒囨崲绮掑害 */
    setGranularity(key) {
      this.currentGranularity = key
      this.refresh()
    },

    /** 鏍规嵁褰撳墠 token + 绮掑害 鏇存柊 ohlc */
    refresh() {
      if (this.currentToken === 'ACT') {
        this.ohlc = this.getACTOhlc()
      } else {
        this.ohlc = this.aggregateRENA()
      }
      this.lastClose = this.ohlc.length ? this.ohlc[this.ohlc.length - 1].close : null
      this.$nextTick(() => this.draw())
    },

    /** 浠庨璁＄畻 JSON 鍙栧綋鍓嶇矑搴︽暟鎹?*/
    getACTOhlc() {
      if (!this.actOhlc) return []
      const raw = this.actOhlc[this.currentGranularity] || []
      return raw.map(d => ({
        date:  new Date(d.t + ' UTC'),
        open:  d.o,
        high:  d.h,
        low:   d.l,
        close: d.c,
        vol:   d.v,
      }))
    },

    /** 浠?RENA 鍘熷 tick 鑱氬悎 OHLC */
    aggregateRENA() {
      const gran = GRANULARITIES.find(g => g.key === this.currentGranularity)
      const ms = gran.ms
      const buckets = new Map()
      for (const { time, price } of this.renaRaw) {
        const key = Math.floor(time.getTime() / ms) * ms
        if (!buckets.has(key)) {
          buckets.set(key, { open: price, high: price, low: price, close: price, vol: 0 })
        } else {
          const b = buckets.get(key)
          if (price > b.high) b.high = price
          if (price < b.low)  b.low  = price
          b.close = price
        }
        buckets.get(key).vol++
      }
      return Array.from(buckets.entries())
        .sort((a, b) => a[0] - b[0])
        .map(([ts, b]) => ({ date: new Date(ts), ...b }))
    },

    /** D3 缁樺浘锛堜笌鍘熸潵涓€鑷达級 */
    draw() {
      const el    = this.$refs.chartBody
      const svgEl = this.$refs.svg
      if (!el || !svgEl || this.ohlc.length === 0) return

      const W = el.clientWidth  || 400
      const H = el.clientHeight || 200
      const m = { top: 8, right: 58, bottom: 26, left: 8 }
      const iW = W - m.left - m.right
      const iH = H - m.top  - m.bottom

      const svg = d3.select(svgEl).attr('width', W).attr('height', H)
      svg.selectAll('*').remove()

      const g = svg.append('g').attr('transform', `translate(${m.left},${m.top})`)

      const data = this.ohlc

      // 鈹€鈹€ 姣斾緥灏?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const xScale = d3.scaleBand()
        .domain(data.map(d => d.date))
        .range([0, iW])
        .padding(0.25)

      const [minL, maxH] = [d3.min(data, d => d.low), d3.max(data, d => d.high)]
      const pad = (maxH - minL) * 0.06 || 1e-9
      const yScale = d3.scaleLinear()
        .domain([minL - pad, maxH + pad])
        .range([iH, 0])

      // 鈹€鈹€ 缃戞牸 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      g.append('g').selectAll('line')
        .data(yScale.ticks(5))
        .enter().append('line')
          .attr('x1', 0).attr('x2', iW)
          .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
          .attr('stroke', COLORS.grid).attr('stroke-width', 1)

      // 鈹€鈹€ Y 杞达紙鍙充晶锛夆攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      g.append('g').attr('transform', `translate(${iW},0)`)
        .call(d3.axisRight(yScale).ticks(5).tickFormat(d => d.toExponential(2)))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text').style('fill', COLORS.axis).style('font-size', '9px')

      // 鈹€鈹€ X 杞?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const fmtMap = {
        '1H': d => d3.timeFormat('%m/%d %H:%M')(d),
        '1D': d => d3.timeFormat('%m/%d')(d),
        '3D': d => d3.timeFormat('%m/%d')(d),
        '1W': d => d3.timeFormat('%m/%d')(d),
      }
      const fmt  = fmtMap[this.currentGranularity]
      const step = Math.max(1, Math.ceil(data.length / Math.max(3, Math.floor(iW / 70))))
      const tickDates = data.filter((_, i) => i % step === 0).map(d => d.date)

      g.append('g').attr('transform', `translate(0,${iH})`)
        .call(d3.axisBottom(xScale).tickValues(tickDates).tickFormat(fmt))
        .call(ax => ax.select('.domain').remove())
        .selectAll('text').style('fill', COLORS.axis).style('font-size', '9px').attr('dy', '1em')

      // 鈹€鈹€ 铚＄儧 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const bw = xScale.bandwidth()
      const candles = g.append('g').selectAll('g.candle')
        .data(data).enter().append('g').attr('class', 'candle')

      // 褰辩嚎
      candles.append('line')
        .attr('x1', d => xScale(d.date) + bw / 2)
        .attr('x2', d => xScale(d.date) + bw / 2)
        .attr('y1', d => yScale(d.high))
        .attr('y2', d => yScale(d.low))
        .attr('stroke', d => d.close >= d.open ? COLORS.bull : COLORS.bear)
        .attr('stroke-width', 1)

      // 瀹炰綋
      candles.append('rect')
        .attr('x', d => xScale(d.date))
        .attr('y', d => yScale(Math.max(d.open, d.close)))
        .attr('width', bw)
        .attr('height', d => Math.max(1, Math.abs(yScale(d.open) - yScale(d.close))))
        .attr('fill', d => d.close >= d.open ? COLORS.bull : COLORS.bear)
        .attr('rx', 1)

      // 鈹€鈹€ Tooltip 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const self = this
      const tooltip = d3.select(this.$refs.wrap)
        .selectAll('.candle-tooltip').data([null]).join('div')
        .attr('class', 'candle-tooltip')
        .style('position', 'absolute').style('pointer-events', 'none')
        .style('opacity', 0).style('background', 'rgba(30,39,55,0.88)')
        .style('color', '#e2e8f0').style('border-radius', '6px')
        .style('padding', '6px 10px').style('font-size', '11px')
        .style('line-height', '1.6').style('z-index', 9).style('white-space', 'nowrap')

      g.append('rect')
        .attr('width', iW).attr('height', iH).attr('fill', 'transparent')
        .on('mousemove', function(event) {
          const [mx] = d3.pointer(event)
          const idx = Math.round((mx / iW) * (data.length - 1))
          const d = data[Math.max(0, Math.min(idx, data.length - 1))]
          if (!d) return
          const wrapRect = self.$refs.wrap.getBoundingClientRect()
          const color = d.close >= d.open ? COLORS.bull : COLORS.bear
          const upDown = d.close >= d.open ? '\u25b2' : '\u25bc'
          tooltip.style('opacity', 1)
            .style('left', (event.clientX - wrapRect.left + 12) + 'px')
            .style('top',  (event.clientY - wrapRect.top  - 10) + 'px')
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
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f0f0f0;
  border-bottom: 1px solid #ddd;
  flex-shrink: 0;
}

.divider {
  color: #cbd5e0;
  font-size: 14px;
  user-select: none;
}

.tab-group { display: flex; gap: 2px; }

.tab-btn {
  padding: 2px 8px;
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  background: #ffffff;
  color: #4a5568;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.6;
}
.tab-btn:hover { background: #ebf4ff; border-color: #4a90e2; color: #4a90e2; }
.tab-btn.active { background: #4a90e2; border-color: #4a90e2; color: #ffffff; font-weight: 600; }

.price-tag {
  margin-left: auto;
  font-size: 11px;
  font-family: 'Courier New', monospace;
  color: #26a69a;
  font-weight: 700;
}

.chart-body { flex: 1; position: relative; overflow: hidden; }
.candle-svg { display: block; width: 100%; height: 100%; }
.loading-mask {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #a0aec0; font-size: 13px;
}
</style>

// ezio: Unified view snapshot utility for auto-capturing view screenshots on user actions.
// Dispatches by view type:
//   - candlestick_chart: delegates to CandlestickChart.captureImage() (html-to-image; handles scroll)
//   - token_distribution / behavior_details: SVG serialization + canvas composite (fast, SVG-only)
// Always outputs PNG — lossless, preserves SVG text/lines; size controlled via pixelRatio.

import { toPng } from 'html-to-image'

const QUALITY_PRESETS = {
  thumbnail: { pixelRatio: 0.5 },
  full: { pixelRatio: 1 },
}

// ezio: logUserAction view name -> DOM data-snapshot-view name
const VIEW_NAME_MAP = {
  kline_chart: 'candlestick_chart',
  candlestick_chart: 'candlestick_chart',
  token_distribution: 'token_distribution',
  behavior_details: 'behavior_details',
}

const SKIP_VIEWS = new Set(['system', 'all_views', 'control_panel'])

export function isCapturable(viewName) {
  if (!viewName) return false
  if (SKIP_VIEWS.has(viewName)) return false
  return !!VIEW_NAME_MAP[viewName]
}

function findPanel(domViewName) {
  return document.querySelector(`[data-snapshot-view="${domViewName}"]`)
}

// ezio: capture an SVG-centric panel by serializing <svg> into an img and compositing onto canvas
async function captureSvgAsImage(panelEl, quality) {
  // ezio: prefer the explicitly tagged main-chart SVG — panel headers contain small icon SVGs
  // (camera/refresh buttons) that would otherwise be picked as the first match
  const svgEl = panelEl.querySelector('svg[data-snapshot-target]') || panelEl.querySelector('svg')
  if (!svgEl) return null
  const bbox = svgEl.getBoundingClientRect()
  const w = Math.max(1, Math.round(bbox.width))
  const h = Math.max(1, Math.round(bbox.height))
  if (w <= 1 || h <= 1) return null

  const preset = QUALITY_PRESETS[quality] || QUALITY_PRESETS.thumbnail
  const scale = preset.pixelRatio

  const svgData = new XMLSerializer().serializeToString(svgEl)
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)

  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      try {
        const c = document.createElement('canvas')
        c.width = Math.round(w * scale)
        c.height = Math.round(h * scale)
        const ctx = c.getContext('2d')
        ctx.scale(scale, scale)
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, w, h)
        ctx.drawImage(img, 0, 0, w, h)
        resolve({ dataUrl: c.toDataURL('image/png'), width: w, height: h })
      } catch (err) {
        console.warn('[viewSnapshot] canvas composite failed', err)
        resolve(null)
      } finally {
        URL.revokeObjectURL(url)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      console.warn('[viewSnapshot] SVG image load failed')
      resolve(null)
    }
    img.src = url
  })
}

// ezio: fallback path using html-to-image for generic DOM
async function captureDomAsImage(panelEl, quality) {
  const preset = QUALITY_PRESETS[quality] || QUALITY_PRESETS.thumbnail
  try {
    const dataUrl = await toPng(panelEl, { backgroundColor: '#ffffff', pixelRatio: preset.pixelRatio })
    const bbox = panelEl.getBoundingClientRect()
    return { dataUrl, width: Math.round(bbox.width), height: Math.round(bbox.height) }
  } catch (err) {
    console.warn('[viewSnapshot] html-to-image capture failed', err)
    return null
  }
}

// ezio: main entry — dispatches by viewName
export async function captureViewByName(viewName, options = {}) {
  if (!isCapturable(viewName)) return null
  // ezio: actionType drives capture strategy — hover actions on TokenDistribution need DOM capture
  // so the HTML tooltip (sibling of the SVG) ends up in the PNG
  const { quality = 'thumbnail', candlestickRef = null, actionType = null } = options
  const domView = VIEW_NAME_MAP[viewName]
  const panel = findPanel(domView)
  if (!panel) {
    console.warn(`[viewSnapshot] panel not found for ${domView}`)
    return null
  }

  let result = null
  if (domView === 'candlestick_chart') {
    if (candlestickRef && typeof candlestickRef.captureImage === 'function') {
      const dataUrl = await candlestickRef.captureImage(quality)
      if (dataUrl) {
        const bbox = panel.getBoundingClientRect()
        result = { dataUrl, width: Math.round(bbox.width), height: Math.round(bbox.height) }
      }
    } else {
      result = await captureDomAsImage(panel, quality)
    }
  } else if (domView === 'token_distribution' && actionType === 'hover_token_distribution_user') {
    // ezio: hover tooltip lives outside <svg>, so fall back to full-DOM capture
    result = await captureDomAsImage(panel, quality)
  } else {
    result = await captureSvgAsImage(panel, quality)
  }

  if (!result) return null
  return {
    dataUrl: result.dataUrl,
    viewName,
    width: result.width,
    height: result.height,
    capturedAt: new Date().toISOString(),
  }
}

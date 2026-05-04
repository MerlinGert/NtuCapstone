import { createApp, h } from 'vue'
import { toPng } from 'html-to-image'
import * as d3 from 'd3'
import TokenDistribution from '../components/TokenDistribution.vue'
import CandlestickChart from '../components/CandlestickChart.vue'
import BehaviorDetails from '../components/BehaviorDetails.vue'

export const MAJOR_VIEW_NAMES = [
  'token_distribution',
  'candlestick_chart',
  'behavior_details',
]

const VIEW_ALIASES = {
  token_distribution: 'token_distribution',
  candlestick_chart: 'candlestick_chart',
  kline_chart: 'candlestick_chart',
  behavior_details: 'behavior_details',
}

const REQUIRED_RENDER_ARGS = {
  token_distribution: [
    'snapshotData',
    'entityDetectionResults',
    'linkDetectionResults',
    'manipulationDetectionResults',
    'scaleFactor',
    'showLinks',
    'width',
    'height',
  ],
  candlestick_chart: [
    'currentCoin',
    'ohlcData',
    'manipulationResults',
    'syncTargetTimeWindow',
    'isSequentialTime',
    'currentGranularity',
    'zoomTransform',
    'topCardsScrollLeft',
    'bottomCardsScrollLeft',
    'width',
    'height',
  ],
  behavior_details: [
    'selectedUser',
    'selectedUsersList',
    'behaviorData',
    'entityInfo',
    'snapshotTime',
    'manipulationResults',
    'syncTargetTimeWindow',
    'showRelatedUsers',
    'useSequentialTime',
    'showManipulationBoxes',
    'width',
    'height',
  ],
}

const ARG_SOURCES = {
  token_distribution: {
    snapshotData: 'CryptoVis.snapshot_data',
    entityDetectionResults: 'CryptoVis.entity_detection_results',
    linkDetectionResults: 'CryptoVis.link_generation_results',
    manipulationDetectionResults: 'CryptoVis.manipulation_detection_results',
    scaleFactor: 'TokenDistribution.scaleFactor',
    showLinks: 'TokenDistribution.showLinks',
    width: 'render argument',
    height: 'render argument',
  },
  candlestick_chart: {
    currentCoin: 'CryptoVis.currentCoin',
    ohlcData: 'CandlestickChart.actOhlc',
    manipulationResults: 'CryptoVis.manipulation_detection_results',
    syncTargetTimeWindow: 'CryptoVis.behaviorTimeWindow',
    isSequentialTime: 'CryptoVis.behaviorSequentialTime',
    currentGranularity: 'CandlestickChart.currentGranularity',
    zoomTransform: 'CandlestickChart.zoomTransform',
    topCardsScrollLeft: 'CandlestickChart.$refs.topCardsContainer.scrollLeft',
    bottomCardsScrollLeft: 'CandlestickChart.$refs.bottomCardsContainer.scrollLeft',
    width: 'render argument',
    height: 'render argument',
  },
  behavior_details: {
    selectedUser: 'CryptoVis.selectedUser',
    selectedUsersList: 'CryptoVis.selectedCardUsers',
    behaviorData: 'CryptoVis.behaviorDetailData',
    entityInfo: 'CryptoVis.selectedEntityInfo',
    snapshotTime: 'CryptoVis.snapshot_configuration.time',
    manipulationResults: 'CryptoVis.manipulation_detection_results',
    syncTargetTimeWindow: 'CryptoVis.klineTimeWindow',
    showRelatedUsers: 'BehaviorDetails.showRelatedUsers',
    useSequentialTime: 'BehaviorDetails.useSequentialTime',
    showManipulationBoxes: 'BehaviorDetails.showManipulationBoxes',
    width: 'render argument',
    height: 'render argument',
  },
}

function normalizeMajorViewName(viewName) {
  return VIEW_ALIASES[viewName] || null
}

function normalizeDimension(value, name, viewName) {
  const dimension = Number(value)
  if (!Number.isFinite(dimension) || dimension <= 0) {
    throw new Error(`${viewName} requires a positive numeric ${name} render argument`)
  }
  return Math.round(dimension)
}

function assertRequiredArgs(viewName, args) {
  if (!args || typeof args !== 'object') {
    throw new Error(`${viewName} render function requires an argument object`)
  }

  const missing = REQUIRED_RENDER_ARGS[viewName].filter(
    (key) => !Object.prototype.hasOwnProperty.call(args, key),
  )
  if (missing.length > 0) {
    throw new Error(`${viewName} render arguments missing: ${missing.join(', ')}`)
  }
}

function cloneRenderArgs(args) {
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(args)
    } catch (_err) {
      // Vue reactive proxies from getRenderArgs are plain-data JSON values for this API,
      // but structuredClone rejects proxies. Fall back to JSON to strip reactivity.
    }
  }
  return JSON.parse(JSON.stringify(args))
}

function prepareRenderArgs(viewName, args) {
  assertRequiredArgs(viewName, args)
  return cloneRenderArgs(args)
}

function summarizeValue(value) {
  if (value == null) {
    return { type: value === null ? 'null' : 'undefined' }
  }
  if (Array.isArray(value)) {
    return { type: 'array', length: value.length }
  }
  if (value instanceof Set) {
    return { type: 'set', size: value.size }
  }
  if (value instanceof Map) {
    return { type: 'map', size: value.size }
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value)
    return {
      type: 'object',
      keyCount: keys.length,
      sampleKeys: keys.slice(0, 10),
    }
  }
  return {
    type: typeof value,
    value,
  }
}

function dependency(viewName, prop, value, includeRawData) {
  const item = {
    prop,
    source: ARG_SOURCES[viewName][prop] || 'render argument',
    summary: summarizeValue(value),
  }
  if (includeRawData) {
    item.value = value
  }
  return item
}

function renderArgDependencies(viewName, args, includeRawData) {
  return REQUIRED_RENDER_ARGS[viewName].map((key) =>
    dependency(viewName, key, args[key], includeRawData),
  )
}

function summarizeZoomTransform(transform) {
  if (!transform) return null
  return {
    k: transform.k,
    x: transform.x,
    y: transform.y,
  }
}

function restoreZoomTransform(transform) {
  if (!transform) return null
  if (typeof transform.rescaleX === 'function') return transform

  const k = Number.isFinite(Number(transform.k)) ? Number(transform.k) : 1
  const x = Number.isFinite(Number(transform.x)) ? Number(transform.x) : 0
  const y = Number.isFinite(Number(transform.y)) ? Number(transform.y) : 0
  return d3.zoomIdentity.translate(x, y).scale(k)
}

function elementBounds(selector) {
  if (typeof document === 'undefined') return null
  const el = document.querySelector(selector)
  if (!el) return null
  const rect = el.getBoundingClientRect()
  return {
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  }
}

function currentPanelSize(viewName, options = {}) {
  const normalizedViewName = normalizeMajorViewName(viewName)
  const bounds = elementBounds(`[data-snapshot-view="${normalizedViewName}"]`)
  return {
    width: options.width || bounds?.width,
    height: options.height || bounds?.height,
  }
}

async function waitForPaint(vm) {
  if (vm?.$nextTick) {
    await vm.$nextTick()
  }
  if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
    await new Promise((resolve) => window.requestAnimationFrame(resolve))
    await new Promise((resolve) => window.requestAnimationFrame(resolve))
  }
}

async function waitForSettledRender(ms) {
  if (!ms) return
  await new Promise((resolve) => setTimeout(resolve, ms))
}

function createRenderHost(viewName, width, height) {
  const host = document.createElement('div')
  host.dataset.majorViewRenderHost = viewName
  Object.assign(host.style, {
    position: 'fixed',
    left: '0',
    top: '0',
    width: `${width}px`,
    height: `${height}px`,
    background: '#ffffff',
    overflow: 'hidden',
    pointerEvents: 'none',
    zIndex: '2147483647',
  })
  document.body.appendChild(host)
  return host
}

async function mountAndRender(Component, props, args, options = {}) {
  const viewName = options.viewName
  const width = normalizeDimension(args.width, 'width', viewName)
  const height = normalizeDimension(args.height, 'height', viewName)
  const host = createRenderHost(viewName, width, height)
  let componentVm = null

  const app = createApp({
    render() {
      return h(Component, {
        ...props,
        ref: 'view',
        onLogAction: () => {},
        onSnapshotInput: () => {},
        onDetectionComplete: () => {},
        onUserSelected: () => {},
        onCardClick: () => {},
        onTimeWindowChanged: () => {},
        onSequentialTimeChanged: () => {},
      })
    },
  })

  const rootVm = app.mount(host)
  componentVm = rootVm.$refs.view

  try {
    await waitForPaint(componentVm)
    if (options.applyState) {
      await options.applyState(componentVm)
      await waitForPaint(componentVm)
    }
    await waitForSettledRender(options.settleMs ?? 250)
    if (options.afterSettle) {
      await options.afterSettle(componentVm)
      await waitForPaint(componentVm)
    }

    let dataUrl = null
    if (options.captureComponent) {
      dataUrl = await options.captureComponent(componentVm)
    } else {
      dataUrl = await toPng(host, {
        backgroundColor: '#ffffff',
        pixelRatio: options.quality === 'thumbnail' ? 0.5 : 1,
      })
    }

    return {
      dataUrl,
      width,
      height,
    }
  } finally {
    app.unmount()
    host.remove()
  }
}

function buildRenderResult(viewName, args, image, options = {}) {
  const includeRawData = !!options.includeRawData
  return {
    viewName,
    image: image
      ? {
          ...image,
          viewName,
        }
      : null,
    dependencies: {
      viewName,
      requiredArguments: [...REQUIRED_RENDER_ARGS[viewName]],
      dataDependencies: renderArgDependencies(viewName, args, includeRawData),
    },
    renderArgs: includeRawData ? args : undefined,
  }
}

export function getMajorViewRenderArgs(vm, viewName, options = {}) {
  const normalizedViewName = normalizeMajorViewName(viewName)
  if (!normalizedViewName) {
    throw new Error(`Unknown major visualization view: ${viewName}`)
  }
  const size = currentPanelSize(normalizedViewName, options)

  if (normalizedViewName === 'token_distribution') {
    const ref = vm.$refs?.tokenDistribution
    return {
      snapshotData: vm.snapshot_data,
      entityDetectionResults: vm.entity_detection_results,
      linkDetectionResults: vm.link_generation_results,
      manipulationDetectionResults: vm.manipulation_detection_results,
      scaleFactor: ref?.scaleFactor ?? 0.4,
      showLinks: ref?.showLinks ?? true,
      width: size.width,
      height: size.height,
    }
  }

  if (normalizedViewName === 'candlestick_chart') {
    const ref = vm.$refs?.candlestickChart
    return {
      currentCoin: vm.currentCoin,
      ohlcData: ref?.actOhlc || null,
      manipulationResults: vm.manipulation_detection_results,
      syncTargetTimeWindow: vm.behaviorTimeWindow,
      isSequentialTime: !!vm.behaviorSequentialTime,
      currentGranularity: ref?.currentGranularity || '1H',
      zoomTransform: summarizeZoomTransform(ref?.zoomTransform),
      topCardsScrollLeft: ref?.$refs?.topCardsContainer?.scrollLeft || 0,
      bottomCardsScrollLeft: ref?.$refs?.bottomCardsContainer?.scrollLeft || 0,
      width: size.width,
      height: size.height,
    }
  }

  const ref = vm.$refs?.behaviorDetails
  return {
    selectedUser: vm.selectedUser,
    selectedUsersList: vm.selectedCardUsers,
    behaviorData: vm.behaviorDetailData,
    entityInfo: vm.selectedEntityInfo,
    snapshotTime: vm.snapshot_configuration?.time || null,
    manipulationResults: vm.manipulation_detection_results,
    syncTargetTimeWindow: vm.klineTimeWindow,
    showRelatedUsers: ref?.showRelatedUsers ?? false,
    useSequentialTime: ref?.useSequentialTime ?? false,
    showManipulationBoxes: ref?.showManipulationBoxes ?? true,
    width: size.width,
    height: size.height,
  }
}

export function getMajorViewDataDependencies(vm, viewName, options = {}) {
  const normalizedViewName = normalizeMajorViewName(viewName)
  if (!normalizedViewName) {
    throw new Error(`Unknown major visualization view: ${viewName}`)
  }
  const args = getMajorViewRenderArgs(vm, normalizedViewName, options)
  return {
    viewName: normalizedViewName,
    requiredArguments: [...REQUIRED_RENDER_ARGS[normalizedViewName]],
    dataDependencies: renderArgDependencies(
      normalizedViewName,
      args,
      !!options.includeRawData,
    ),
  }
}

export async function renderTokenDistributionView(args, options = {}) {
  const viewName = 'token_distribution'
  const renderArgs = prepareRenderArgs(viewName, args)
  const image = await mountAndRender(
    TokenDistribution,
    {
      snapshotData: renderArgs.snapshotData,
      entityDetectionResults: renderArgs.entityDetectionResults,
      linkDetectionResults: renderArgs.linkDetectionResults,
      manipulationDetectionResults: renderArgs.manipulationDetectionResults,
    },
    renderArgs,
    {
      ...options,
      viewName,
      settleMs: options.settleMs ?? 1000,
      applyState: async (componentVm) => {
        componentVm.loading = !renderArgs.snapshotData
        componentVm.detecting = false
        componentVm.scaleFactor = renderArgs.scaleFactor
        componentVm.showLinks = renderArgs.showLinks
        if (typeof componentVm.setSvg === 'function') {
          componentVm.setSvg()
        } else {
          componentVm.drawChart()
        }
        if (typeof componentVm.processManipulationResults === 'function') {
          componentVm.processManipulationResults()
        }
        if (componentVm.simulation) {
          const tickHandler = componentVm.simulation.on('tick')
          componentVm.simulation.tick(options.simulationTicks ?? 300)
          if (typeof tickHandler === 'function') {
            tickHandler()
          }
          componentVm.simulation.stop()
        }
      },
    },
  )
  return buildRenderResult(viewName, renderArgs, image, options)
}

export async function renderCandlestickView(args, options = {}) {
  const viewName = 'candlestick_chart'
  const renderArgs = prepareRenderArgs(viewName, args)
  const image = await mountAndRender(
    CandlestickChart,
    {
      currentCoin: renderArgs.currentCoin,
      ohlcData: renderArgs.ohlcData,
      manipulationResults: Array.isArray(renderArgs.manipulationResults)
        ? renderArgs.manipulationResults
        : [],
      syncTargetTimeWindow: renderArgs.syncTargetTimeWindow,
      isSequentialTime: !!renderArgs.isSequentialTime,
    },
    renderArgs,
    {
      ...options,
      viewName,
      applyState: async (componentVm) => {
        componentVm.currentGranularity = renderArgs.currentGranularity
        componentVm.zoomTransform = restoreZoomTransform(renderArgs.zoomTransform)
        componentVm.refresh()
      },
      afterSettle: async (componentVm) => {
        if (componentVm.$refs?.topCardsContainer) {
          componentVm.$refs.topCardsContainer.scrollLeft = renderArgs.topCardsScrollLeft || 0
        }
        if (componentVm.$refs?.bottomCardsContainer) {
          componentVm.$refs.bottomCardsContainer.scrollLeft = renderArgs.bottomCardsScrollLeft || 0
        }
        if (typeof componentVm.drawBands === 'function') {
          componentVm.drawBands()
        }
      },
      captureComponent: async (componentVm) =>
        componentVm.captureImage({
          quality: options.quality || 'full',
          includeChrome: true,
        }),
    },
  )
  return buildRenderResult(viewName, renderArgs, image, options)
}

export async function renderBehaviorDetailsView(args, options = {}) {
  const viewName = 'behavior_details'
  const renderArgs = prepareRenderArgs(viewName, args)
  const image = await mountAndRender(
    BehaviorDetails,
    {
      selectedUser: renderArgs.selectedUser,
      selectedUsersList: renderArgs.selectedUsersList,
      behaviorData: renderArgs.behaviorData,
      entityInfo: renderArgs.entityInfo,
      snapshotTime: renderArgs.snapshotTime,
      manipulationResults: Array.isArray(renderArgs.manipulationResults)
        ? renderArgs.manipulationResults
        : [],
      syncTargetTimeWindow: renderArgs.syncTargetTimeWindow,
    },
    renderArgs,
    {
      ...options,
      viewName,
      applyState: async (componentVm) => {
        componentVm.showRelatedUsers = renderArgs.showRelatedUsers
        componentVm.useSequentialTime = renderArgs.useSequentialTime
        componentVm.showManipulationBoxes = renderArgs.showManipulationBoxes
        if (renderArgs.behaviorData && typeof componentVm.drawChart === 'function') {
          componentVm.drawChart()
        }
      },
    },
  )
  return buildRenderResult(viewName, renderArgs, image, options)
}

export async function renderMajorVisualizationView(viewName, args, options = {}) {
  const normalizedViewName = normalizeMajorViewName(viewName)
  if (!normalizedViewName) {
    throw new Error(`Unknown major visualization view: ${viewName}`)
  }
  if (normalizedViewName === 'token_distribution') {
    return renderTokenDistributionView(args, options)
  }
  if (normalizedViewName === 'candlestick_chart') {
    return renderCandlestickView(args, options)
  }
  return renderBehaviorDetailsView(args, options)
}

export async function captureMajorVisualizationView(vm, viewName, options = {}) {
  const normalizedViewName = normalizeMajorViewName(viewName)
  if (!normalizedViewName) {
    throw new Error(`Unknown major visualization view: ${viewName}`)
  }
  const args = getMajorViewRenderArgs(vm, normalizedViewName, options)
  return renderMajorVisualizationView(normalizedViewName, args, options)
}

export async function captureMajorVisualizationViews(vm, viewNames = MAJOR_VIEW_NAMES, options = {}) {
  let names = viewNames
  let captureOptions = options

  if (!Array.isArray(viewNames)) {
    names = MAJOR_VIEW_NAMES
    captureOptions = viewNames || {}
  }

  const results = []
  for (const viewName of names) {
    results.push(await captureMajorVisualizationView(vm, viewName, captureOptions))
  }
  return results
}

export function createMajorViewApi(vm) {
  return {
    views: [...MAJOR_VIEW_NAMES],
    aliases: { ...VIEW_ALIASES },
    requiredArguments: { ...REQUIRED_RENDER_ARGS },
    getRenderArgs: (viewName, options = {}) => getMajorViewRenderArgs(vm, viewName, options),
    getDataDependencies: (viewName, options = {}) =>
      getMajorViewDataDependencies(vm, viewName, options),
    renderView: (viewName, args, options = {}) =>
      renderMajorVisualizationView(viewName, args, options),
    renderTokenDistributionView: (args, options = {}) =>
      renderTokenDistributionView(args, options),
    renderCandlestickView: (args, options = {}) => renderCandlestickView(args, options),
    renderBehaviorDetailsView: (args, options = {}) =>
      renderBehaviorDetailsView(args, options),
    captureView: (viewName, options = {}) =>
      captureMajorVisualizationView(vm, viewName, options),
    captureAllViews: (viewNamesOrOptions, maybeOptions = {}) =>
      captureMajorVisualizationViews(vm, viewNamesOrOptions, maybeOptions),
  }
}

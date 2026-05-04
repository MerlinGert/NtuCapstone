# Major View Render API

The frontend exposes the three major visualization views as browser-side APIs through `window.maniScopeMajorViewApi` after `CryptoVis` mounts. This API is intended for trace analysis, report generation, and automated capture workflows that need both the rendered image and the data dependencies behind a view.

The primary render contract is argument-based: each view has a function that requires the full argument object needed to render that view. `getRenderArgs(viewName)` is a convenience extractor from the current UI state. `renderView(viewName, args)` is the actual renderer and does not depend on the current on-screen panel layout.

## Views

- `token_distribution`: token holder distribution network.
- `candlestick_chart`: ACT or PNUT K-line view with manipulation cards. The alias `kline_chart` is accepted.
- `behavior_details`: selected user or selected manipulation-card user behavior timeline.

## API

```js
const api = window.maniScopeMajorViewApi

const tokenArgs = api.getRenderArgs('token_distribution', {
  width: 1000,
  height: 610,
})

await api.renderView('token_distribution', tokenArgs)
await api.renderView('kline_chart', api.getRenderArgs('kline_chart', {
  width: 1500,
  height: 850,
}), { quality: 'thumbnail' })

// Convenience wrapper: extract args from the current UI and render.
await api.captureView('behavior_details', { width: 1500, height: 450 })
```

## Capture Options

- `quality`: `full` by default for this API. Use `thumbnail` for smaller images.
- `includeRawData`: `false` by default. When false, `dependencies` only contains compact data summaries. When true, each dependency also includes the raw argument value.

Each capture result has this shape:

```js
{
  viewName: 'token_distribution',
  image: {
    dataUrl: 'data:image/png;base64,...',
    viewName: 'token_distribution',
    width: 1008,
    height: 610
  },
  dependencies: {
    requiredArguments: [
      'snapshotData',
      'entityDetectionResults',
      'linkDetectionResults',
      'manipulationDetectionResults',
      'scaleFactor',
      'showLinks',
      'width',
      'height'
    ],
    dataDependencies: [
      { prop: 'snapshotData', source: 'CryptoVis.snapshot_data', summary: { type: 'object', keyCount: 4 } }
    ]
  }
}
```

`renderView` clones its argument object before rendering. This prevents D3 and Vue rendering from mutating the caller's input data. For the same arguments, app code, browser engine, fonts, and static assets, the returned `image.dataUrl` is intended to be deterministic. The renderer still uses the browser DOM and rasterization pipeline internally, so it is not a side-effect-free pure function in the formal programming-language sense.

## Required Arguments

### Token Distribution

`renderTokenDistributionView(args)` and `renderView('token_distribution', args)` require:

- `snapshotData`
- `entityDetectionResults`
- `linkDetectionResults`
- `manipulationDetectionResults`
- `scaleFactor`
- `showLinks`
- `width`
- `height`

### K-line

`renderCandlestickView(args)` and `renderView('candlestick_chart', args)` require:

- `currentCoin`
- `ohlcData`
- `manipulationResults`
- `syncTargetTimeWindow`
- `isSequentialTime`
- `currentGranularity`
- `zoomTransform`
- `topCardsScrollLeft`
- `bottomCardsScrollLeft`
- `width`
- `height`

The alias `kline_chart` is accepted by `renderView`.

### Behavior Details

`renderBehaviorDetailsView(args)` and `renderView('behavior_details', args)` require:

- `selectedUser`
- `selectedUsersList`
- `behaviorData`
- `entityInfo`
- `snapshotTime`
- `manipulationResults`
- `syncTargetTimeWindow`
- `showRelatedUsers`
- `useSequentialTime`
- `showManipulationBoxes`
- `width`
- `height`

## Dependency Scope

`getDataDependencies` returns the current frontend inputs that drive each view, plus the view state that changes how those inputs are rendered.

- Token Distribution depends on `snapshot_data`, `entity_detection_results`, `link_generation_results`, and `manipulation_detection_results`, plus controls such as scale and link visibility.
- K-line depends on `currentCoin`, the loaded OHLC JSON for that coin, `manipulation_detection_results`, sync-window state, and granularity, zoom, or manipulation-card scroll state.
- Behavior Details depends on the selected user or selected manipulation-card users, generated behavior detail data, selected entity info, snapshot time, manipulation results, sync-window state, and behavior controls such as related users, sequential time, and manipulation boxes.

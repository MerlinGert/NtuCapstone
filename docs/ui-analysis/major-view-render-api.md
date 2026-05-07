# Major View Render API

The frontend exposes the three major visualization views as browser-side APIs through `window.maniScopeMajorViewApi` after `CryptoVis` mounts. This API is intended for trace analysis, report generation, and automated capture workflows that need both the rendered image and the data dependencies behind a view.

The primary render contract is argument-based: each view has a function that requires the full argument object needed to render that view. `getRenderArgs(viewName)` is a convenience extractor from the current UI state. `renderView(viewName, args)` is the actual renderer and does not depend on the current on-screen panel layout.

These APIs are browser render helpers, not a headless analytical engine. They mount Vue/D3 components into a temporary DOM host and export the rendered pixels. Use the returned dependencies and metadata for auditability, and use raw data for exact counts when the visual can be sampled.

## Views

- `token_distribution`: token holder distribution network.
- `candlestick_chart`: ACT or PNUT K-line view with manipulation cards. The alias `kline_chart` is accepted.
- `behavior_details`: selected user or selected manipulation-card user behavior timeline.

## API

```js
const api = window.maniScopeMajorViewApi

api.views
// ['token_distribution', 'candlestick_chart', 'behavior_details']

api.optionalArguments
// {
//   token_distribution: [],
//   candlestick_chart: ['visibleTimeWindow', 'cardAlignment', 'cardFocusTime'],
//   behavior_details: ['visibleTimeWindow', 'maxEventsPerUser']
// }

const tokenArgs = api.getRenderArgs('token_distribution', {
  width: 1000,
  height: 610,
})

await api.renderView('token_distribution', tokenArgs)
const klineArgs = api.getRenderArgs('kline_chart', {
  width: 1500,
  height: 850,
})
klineArgs.visibleTimeWindow = [
  '2024-10-25T00:00:00Z',
  '2024-10-27T23:59:59Z',
]
klineArgs.cardAlignment = 'visible_window'
await api.renderView('kline_chart', klineArgs, { quality: 'thumbnail' })

// Convenience wrapper: extract args from the current UI and render.
// For Behavior Details this throws by default if no user/card is selected.
await api.captureView('behavior_details', { width: 1500, height: 450 })

// Pure wrapper form: pass full render args as the second argument.
await api.captureView('behavior_details', behaviorArgs, { quality: 'full' })
```

## Capture Options

- `quality`: `full` by default for this API. Use `thumbnail` for smaller images.
- `includeRawData`: `false` by default. When false, `dependencies` only contains compact data summaries. When true, each dependency also includes the raw argument value.
- `strict`: `false` by default for `renderView`, but direct `captureView('behavior_details', ...)` defaults to strict behavior. Strict Behavior Details rendering throws unless the args include a selected user or card users and non-empty `behaviorData`.
- `allowEmpty`: set to `true` to allow an empty Behavior Details prompt capture.

`captureAllViews()` defaults to `allowEmpty: true` so a full-page capture pass can still include the empty Behavior Details prompt. Pass `strict: true` when an automated report should fail instead of silently capturing an empty Behavior Details view.

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
    optionalArguments: [],
    dataDependencies: [
      { prop: 'snapshotData', source: 'CryptoVis.snapshot_data', summary: { type: 'object', keyCount: 4 } }
    ]
  },
  renderMetadata: null
}
```

`renderView` clones its argument object before rendering. This prevents D3 and Vue rendering from mutating the caller's input data. For the same arguments, app code, browser engine, fonts, and static assets, the returned `image.dataUrl` is intended to be deterministic. The renderer still uses the browser DOM and rasterization pipeline internally, so it is not a side-effect-free pure function in the formal programming-language sense.

## Current Caveats

- Token Distribution and `html-to-image` can still emit SVG validation warnings such as `Expected length, "NaN"` or negative `<rect>` heights while producing usable PNGs. Treat image success and console cleanliness as separate checks.
- K-line card alignment works for choosing the relevant card strip region, but labels can be cramped in thumbnail captures. Use larger dimensions or `quality: 'full'` when card text matters.
- Behavior Details event dots can be visually downsampled for high-event users. Use `renderMetadata.behaviorDetails.sampling` plus the fetched sequence data for exact event counts.
- `visibleTimeWindow` for Behavior Details only applies in absolute-time mode. If `useSequentialTime` is true, the sequential x-axis is used instead.

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

Optional K-line render state:

- `visibleTimeWindow`: `[start, end]` date-like values. When provided, the renderer computes the zoom transform for this time window and uses it instead of any supplied `zoomTransform`.
- `cardAlignment`: `scroll_offsets` by default. Use `visible_window` to align top and bottom manipulation-card scrollers to `visibleTimeWindow`, or `focus_time` to align around `cardFocusTime`.
- `cardFocusTime`: optional date-like value used by `cardAlignment: 'focus_time'`.

You can also build the transform directly:

```js
const zoomTransform = api.createKlineZoomTransform(klineArgs, [
  '2024-10-25T00:00:00Z',
  '2024-10-27T23:59:59Z',
])
if (!zoomTransform) {
  throw new Error('No OHLC rows overlap the requested K-line window')
}
await api.renderView('kline_chart', {
  ...klineArgs,
  zoomTransform,
})
```

`createKlineZoomTransform(args, visibleTimeWindow)` uses `args.currentGranularity` to pick the OHLC row set and returns `null` when the requested time window does not overlap those rows.

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

Optional Behavior Details render state:

- `visibleTimeWindow`: `[start, end]` date-like values. In absolute-time mode, this directly controls the rendered x-axis domain. It is separate from `syncTargetTimeWindow`, which only controls whether the Sync Time UI is available.
- `maxEventsPerUser`: maximum rendered event marks per user after visual event downsampling. Balance-sequence points use up to twice this limit. The default is `1500`.

Behavior Details renders are argument-driven, but the caller must provide the data to render. For a selected user or card-user set, fetch `/api/user_behavior/sequences` and pass the result as `behaviorData`:

```js
const users = ['DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH']
const sequences = await fetch('/api/user_behavior/sequences', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ users, coin: 'ACT' }),
}).then((res) => res.json())

const behaviorArgs = {
  ...api.getRenderArgs('behavior_details', { width: 1500, height: 520 }),
  selectedUser: users[0],
  selectedUsersList: [],
  behaviorData: sequences,
  visibleTimeWindow: [
    '2024-10-31T00:00:00Z',
    '2024-10-31T03:00:00Z',
  ],
  maxEventsPerUser: 3000,
}
await api.renderView('behavior_details', behaviorArgs, { strict: true })

// Equivalent pure capture wrapper. This does not depend on the current
// selected user/card in the visible UI.
await api.captureView('behavior_details', behaviorArgs, { strict: true })
```

If event or balance-sequence downsampling happens, the capture result includes `renderMetadata.behaviorDetails.sampling`:

```js
{
  renderMetadata: {
    behaviorDetails: {
      visibleTimeWindowApplied: [
        '2024-10-27T15:00:00.000Z',
        '2024-10-31T18:00:00.000Z'
      ],
      sampling: {
        maxEventsPerUser: 500,
        users: [
          {
            user: '63qFfzr6aUjWiwFDc8T3UkKGM4iZLGxCcyE2exnS9aic',
            kind: 'events',
            originalCount: 11720,
            renderedCount: 489,
            step: 24
          }
        ]
      }
    }
  }
}
```

Interpret a downsampled Behavior Details image as a timing and density summary. Use the sequence payload and metadata for exact event counts.

## Dependency Scope

`getDataDependencies` returns the current frontend inputs that drive each view, plus the view state that changes how those inputs are rendered.

- Token Distribution depends on `snapshot_data`, `entity_detection_results`, `link_generation_results`, and `manipulation_detection_results`, plus controls such as scale and link visibility.
- K-line depends on `currentCoin`, the loaded OHLC JSON for that coin, `manipulation_detection_results`, sync-window state, and granularity, zoom, or manipulation-card scroll state.
- Behavior Details depends on the selected user or selected manipulation-card users, generated behavior detail data, selected entity info, snapshot time, manipulation results, sync-window state, and behavior controls such as related users, sequential time, and manipulation boxes.

# Major View Render API

The frontend exposes the three major visualization views as browser-side APIs through `window.maniScopeMajorViewApi` after `CryptoVis` mounts. This API is intended for trace analysis, report generation, and automated capture workflows that need both the rendered image and the data dependencies behind a view.

The primary render contract is argument-based: each view has a function that requires the full argument object needed to render that view. `getRenderArgs(viewName)` is a convenience extractor from the current UI state. `renderView(viewName, args)` is the actual renderer and does not depend on the current on-screen panel layout.

These APIs are browser render helpers, not a headless analytical engine. They mount Vue/D3 components into a temporary offscreen DOM host and export the rendered pixels. Use the returned dependencies and metadata for auditability, and use raw data for exact counts when the visual can be sampled.

The temporary render host is fixed behind the page with pointer events disabled, `aria-hidden="true"`, negative z-index, and CSS containment. It stays inside the browser's renderable area so `html-to-image` can capture SVG/HTML views reliably, but it should not visually cover or intercept the active Human Workspace or Agent Workspace page. Render calls are queued per browser page, so multiple `renderView` or `captureView` calls complete in order instead of mounting competing temporary views at the same time.

Codex agents should normally use the session-local Python wrapper instead of calling `window.maniScopeMajorViewApi` directly. Each session contains `.maniscope-chat/sessions/{sessionId}/maniscope_visualization.py`. That wrapper calls the Codex bridge, which owns an isolated Agent Workspace browser page at `http://127.0.0.1:3099/{sessionId}/agent`, renders through the browser API, and saves PNG artifacts under `.maniscope-chat/sessions/{sessionId}/artifacts/`.

Before extracting current arguments or rendering through the bridge, the Agent Workspace calls `ensureReady(viewName)`. Readiness waits for session restore, snapshot processing, detector outputs, manipulation results, child view redraws, and any pending target-view work. If required data is still missing, the bridge returns a clear readiness error instead of silently returning empty render args.

Baseline evaluation sessions are intentionally different. A baseline session under `.maniscope-chat/baseline-sessions/{sessionId}` does not receive `maniscope_visualization.py` and does not expose argument-driven rendering to the baseline agent. Its `maniscope_baseline_views.py` helper can only copy the latest synced Human Workspace screenshots from `current-state.json.majorViewScreenshots` into `artifacts/`, using functions such as `capture_current_token_distribution()`, `capture_current_kline_chart()`, and `capture_current_behavior_details()`.

## Views

- `token_distribution`: token holder distribution network.
- `candlestick_chart`: ACT or PNUT K-line view with manipulation cards. The alias `kline_chart` is accepted.
- `behavior_details`: selected user or selected manipulation-card user behavior timeline.

## Python Agent API

The copied `maniscope_visualization.py` file exposes view-specific functions:

```python
from maniscope_visualization import (
    get_token_distribution_args,
    render_token_distribution,
    get_kline_args,
    render_kline_chart,
    fetch_behavior_sequences,
    get_behavior_details_args,
    render_behavior_details,
)
```

Use `get_*_args(...)` to extract the Agent Workspace's current view inputs, then pass explicit arguments into `render_*` functions for deterministic evidence:

```python
kline_args = get_kline_args(
    width=1600,
    height=900,
    visible_time_window=["2024-10-26T00:00:00Z", "2024-10-27T00:00:00Z"],
    card_alignment="visible_window",
)

kline_image = render_kline_chart(
    **kline_args,
    artifact_name="oct26-kline.png",
)

users = ["wallet_1", "wallet_2"]
behavior_data = fetch_behavior_sequences(users, coin="ACT")

behavior_image = render_behavior_details(
    selected_user=users[0],
    selected_users_list=users,
    behavior_data=behavior_data,
    entity_info=None,
    snapshot_time="2024-11-09T23:00:00Z",
    manipulation_results=kline_args["manipulation_results"],
    sync_target_time_window=None,
    visible_time_window=["2024-10-26T00:00:00Z", "2024-10-27T00:00:00Z"],
    artifact_name="oct26-behavior-details.png",
)
```

Render results use Python-style top-level keys such as `artifact_path`, `artifact_url`, `artifact_name`, `dependencies`, and `render_metadata`. The actual frontend render arguments inside the wrapper are converted from Python snake case to the frontend camel case contract.

The wrapper talks to these local bridge endpoints:

- `GET /api/agent-browser/{sessionId}/health`
- `POST /api/agent-browser/{sessionId}/token-distribution/current-args`
- `POST /api/agent-browser/{sessionId}/token-distribution/render`
- `POST /api/agent-browser/{sessionId}/kline/current-args`
- `POST /api/agent-browser/{sessionId}/kline/render`
- `POST /api/agent-browser/{sessionId}/behavior-details/current-args`
- `POST /api/agent-browser/{sessionId}/behavior-details/render`
- `POST /api/agent-browser/{sessionId}/behavior-details/fetch-sequences`

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

await api.ensureReady('token_distribution')
api.getReadiness('token_distribution')
// { ready: true, views: { token_distribution: { ready: true, missing: [] } }, ... }

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

// Convenience wrapper: extract args from the current workspace UI and render.
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

`captureView` is the convenience wrapper for the current mounted workspace. In the Human Workspace it captures human state; in the Agent Workspace it captures agent state. To avoid coupling to either visible workspace, call `renderView(viewName, args)` with a complete argument object.

## Current Caveats

- Token Distribution and `html-to-image` can still emit SVG validation warnings such as `Expected length, "NaN"` or negative `<rect>` heights while producing usable PNGs. Treat image success and console cleanliness as separate checks.
- K-line card alignment works for choosing the relevant card strip region, but labels can be cramped in thumbnail captures. Use larger dimensions or `quality: 'full'` when card text matters.
- Behavior Details event dots can be visually downsampled for high-event users. Use `renderMetadata.behaviorDetails.sampling` plus the fetched sequence data for exact event counts.
- `visibleTimeWindow` for Behavior Details only applies in absolute-time mode. If `useSequentialTime` is true, the sequential x-axis is used instead.
- The render queue is per browser tab. Separate human and agent browser pages each have their own queue.

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

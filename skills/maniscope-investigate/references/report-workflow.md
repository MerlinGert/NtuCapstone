# ManiScope Investigation Report Workflow

Use this reference when writing a continued investigation report from ManiScope trace recommendations.

## Inputs To Read

- `AGENTS.md` for repository conventions.
- `docs/ui-analysis/major-view-render-api.md` for current render API details.
- The target trace directory under `insight-hunting/traces/`.
- Existing trace artifacts such as `analysis-report.md`, `trace-step-map.md`, `session.json`, and previous follow-up reports.
- Local data or backend endpoints needed for exact transfers, trades, balances, and behavior sequences.

## Report Destination

Place the report in the target trace directory unless the user gives a different path. For continued investigations, prefer:

- `continued-investigation-report.md`
- `continued-investigation-assets/`

Do not leave report-specific assets in generic docs folders.

## Report Shape

Keep the report focused on investigation content:

1. Scope
2. Actions taken
3. Intermediate results
4. Findings
5. Bottom line

Avoid implementation notes, API debugging details, and fix history unless the user explicitly asks for an API test report. Phrase findings with the evidence level clear. Use "direct evidence" for exact raw-data or endpoint-backed facts, and "inference" for role interpretation from views.

## Asset Rules

- Save only images that support a report claim.
- Put all kept assets in `continued-investigation-assets/`.
- Use evidence-oriented filenames, for example:
  - `kline-core-window.png`
  - `behavior-selected-wallets.png`
  - `token-distribution-sibling-wallets.png`
- Delete unused intermediate captures before finishing.
- Verify every image link in the report resolves.

## Render API Pattern

Open the frontend and wait until `window.maniScopeMajorViewApi` is available after `CryptoVis` mounts. Use the docs in `major-view-render-api.md` as the source of truth, but this browser-side pattern is usually enough for focused captures:

```js
// Run inside the page context, for example through page.evaluate.
const api = window.maniScopeMajorViewApi
const klineArgs = api.getRenderArgs('kline_chart', { width: 1500, height: 850 })

Object.assign(klineArgs, {
  visibleTimeWindow: ['2024-11-03T00:00:00Z', '2024-11-04T00:00:00Z'],
  cardAlignment: 'visible_window',
})

const klineCapture = await api.captureView('kline_chart', klineArgs, {
  quality: 'full',
})
```

The current browser API returns an image data URL; it does not accept an `outputPath`. Return the capture result from the page context, then save the PNG from the Node or automation layer that called `page.evaluate`. Do not call `fs` from inside the browser page context.

```js
// Run outside the page context after page.evaluate returns the capture object.
async function saveCapturePng(capture, outputPath) {
  const fs = await import('node:fs/promises')
  const base64 = capture.image.dataUrl.replace(/^data:image\/png;base64,/, '')
  await fs.writeFile(outputPath, Buffer.from(base64, 'base64'))
}

await saveCapturePng(
  klineCapture,
  '/absolute/path/to/continued-investigation-assets/kline-window.png',
)
```

For Behavior Details, first fetch or construct full `behaviorData`, then pass an explicit wallet selection and window:

```js
// Run inside the page context.
const users = ['DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH']
const behaviorData = await fetch('/api/user_behavior/sequences', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ users, coin: 'ACT' }),
}).then((res) => res.json())

const behaviorArgs = api.getRenderArgs('behavior_details', {
  width: 1500,
  height: 520,
})

Object.assign(behaviorArgs, {
  selectedUser: users[0],
  selectedUsersList: [],
  behaviorData,
  visibleTimeWindow: ['2024-11-03T00:00:00Z', '2024-11-04T00:00:00Z'],
  maxEventsPerUser: 3000,
})

const behaviorCapture = await api.captureView('behavior_details', behaviorArgs, {
  quality: 'full',
  strict: true,
})
```

The available view names are `token_distribution`, `candlestick_chart`, and `behavior_details`. The alias `kline_chart` is accepted for the K-line view. Use `captureView(viewName, args, options)` for one view and `captureAllViews()` for a broad context pass.

## Analysis Checklist

- Start from recommendation threads, then turn each one into a concrete check.
- Confirm exact counts and transfer paths from raw data before relying on a visualization.
- Compare wallets within the same visible time window.
- Separate original clicked-component wallets from newly discovered sibling or downstream wallets.
- Check whether a post-window exit is direct, delayed, or only visually suggested.
- For high-frequency wallets, distinguish gross activity from net position change.
- If a view looks empty or misaligned, test the same input with a smaller wallet list and stricter render options before drawing a conclusion.

## Final Validation

Run these checks before reporting completion:

```bash
find insight-hunting/traces/<trace>/continued-investigation-assets -type f -maxdepth 1
rg "continued-investigation-assets/" insight-hunting/traces/<trace>/continued-investigation-report.md
git diff --check
```

If the work includes code changes, also run the relevant project checks before committing. Use `bun` for frontend commands and `uv` for backend Python commands.

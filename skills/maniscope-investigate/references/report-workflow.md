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

Open the frontend and wait until `window.maniScopeMajorViewApi` is available after `CryptoVis` mounts. Use the docs in `major-view-render-api.md` as the source of truth, but this pattern is usually enough for focused captures:

```js
const api = window.maniScopeMajorViewApi;
const args = api.getRenderArgs('KLineChart', { width: 1200, height: 720 });

Object.assign(args, {
  selectedToken: 'PNUT',
  visibleTimeWindow: ['2024-11-03T00:00:00Z', '2024-11-04T00:00:00Z'],
  cardAlignment: 'visible_window',
});

await api.captureMajorView('KLineChart', args, {
  outputPath: '/absolute/path/to/continued-investigation-assets/kline-window.png',
});
```

For Behavior Details, first fetch or construct full `behaviorData`, then pass an explicit wallet selection and window:

```js
const args = api.getRenderArgs('BehaviorDetails', { width: 1400, height: 900 });

Object.assign(args, {
  behaviorData,
  selectedUsersList: selectedWallets,
  visibleTimeWindow: ['2024-11-03T00:00:00Z', '2024-11-04T00:00:00Z'],
  maxEventsPerUser: 400,
});

await api.captureMajorView('BehaviorDetails', args, {
  outputPath: '/absolute/path/to/continued-investigation-assets/behavior-wallets.png',
  strict: true,
});
```

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

# Follow-up Investigation Execution

Use this reference when executing a Recommendation Plan Forest or continuing a ManiScope trace investigation from existing recommendations. The goal is to combine raw data, backend endpoints, and rendered ManiScope views, then record evidence as Findings, Insights, and Reasoning Graph Patches.

This reference is operational. For methodology, graph schemas, Recommendation Plan Forests, and patch formats, use:

- `reasoning-graph-format.md`
- `recommendation-plan-format.md`
- `reasoning-graph-patch-format.md`

## Inputs To Read

- `AGENTS.md` for repository conventions.
- `docs/ui-analysis/major-view-render-api.md` for current render API details.
- The target trace directory under `insight-hunting/traces/`.
- Existing trace artifacts such as `analysis-report.md`, `trace-step-map.md`, `reasoning-graph.json`, `user-reasoning-forest.md`, `recommendation-plan-graph.json`, and previous follow-up reports.
- Local data or backend endpoints needed for exact transfers, trades, balances, and behavior sequences.

## Execution Workflow

1. **Orient from the plan**
   - Start from `recommendation-plan-graph.json` or the relevant recommendation section.
   - Identify whether the branch is `Evidence Completion` or `Hypothesis Expansion`.
   - Convert each Recommended Interaction into an executable check, such as cohort overlap, transfer paths, sibling windows, post-window exits, role comparisons, or rendered view inspection.

2. **Check local services**
   - Reuse running services when possible. Verify with `curl` or browser navigation before starting new processes.
   - Backend convention: run from `front/server` with `uv`.
   - Frontend convention: run from `front` with `bun`.
   - If browser-side rendering is needed, use a browser automation surface that supports page JavaScript evaluation.
   - The render API lives on `window.maniScopeMajorViewApi` after `CryptoVis` mounts.

3. **Gather raw evidence first**
   - Use raw trace data, local JSON/CSV data, or backend endpoints for exact counts, amounts, timestamps, and transfer relations.
   - Use `/api/user_behavior/sequences` to build `behaviorData` for Behavior Details renders.
   - Treat rendered images as visual evidence for timing, density, grouping, and qualitative role comparison.
   - Do not infer exact event counts from Behavior Details dots when the row may be sampled. Use sequence payloads and render metadata for exact counts.

4. **Render focused views**
   - Use `api.getRenderArgs(viewName, { width, height })` as the starting point, then set explicit render args.
   - Available view names are `token_distribution`, `candlestick_chart`, and `behavior_details`. The alias `kline_chart` is accepted for the K-line view.
   - For K-line windows, prefer `visibleTimeWindow` and `cardAlignment: 'visible_window'`; use `api.createKlineZoomTransform(args, window)` if constructing transforms directly.
   - For Behavior Details, pass full `behaviorData`, `selectedUser` or `selectedUsersList`, `visibleTimeWindow`, and `maxEventsPerUser`.
   - Use `strict: true` for Behavior Details captures that should fail instead of producing an empty prompt.
   - Use larger dimensions or full-quality captures when labels, card text, or timelines matter.

5. **Analyze by role and time window**
   - Compare wallets inside the same visible time window before assigning role labels.
   - Separate direct evidence from inference. Direct evidence includes repeated cohort membership, exact transfers, exact trades, and endpoint-derived behavior sequences.
   - Use careful role labels: storage sink, directional accumulator, one-shot exit seller, later exit seller, high-frequency buy-sell actor, round-trip-like actor, or net-long high-frequency actor.
   - Recheck whether new candidates directly connect to the original clicked component before implying they are part of the same group.

6. **Patch the reasoning graph**
   - Convert actual follow-up results into real Interaction, Finding, Insight, or Hypothesis nodes.
   - New follow-up evidence nodes must include `actor`, `source`, and `planRef`.
   - Use `supports`, `refines`, or `contradicts` edges to attach new Findings or Insights to existing or new Hypotheses.
   - Apply the patch with `scripts/apply_reasoning_graph_patch.py` and regenerate the augmented forest.

## Render API Pattern

Open the frontend and wait until `window.maniScopeMajorViewApi` is available after `CryptoVis` mounts. Use `docs/ui-analysis/major-view-render-api.md` as the source of truth, but this browser-side pattern is usually enough for focused captures:

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

## Report And Asset Rules

When the user asks for a durable follow-up report, place it in the target trace directory unless the user gives a different path. Prefer:

- `continued-investigation-report.md`
- `continued-investigation-assets/`

Keep the report focused on investigation content:

1. Scope
2. Actions taken
3. Intermediate results
4. Findings
5. Reasoning graph patch summary
6. Bottom line

Asset rules:

- Save only images that support a report claim.
- Put kept assets in `continued-investigation-assets/` or another trace-local assets folder named by the user.
- Use evidence-oriented filenames, for example `kline-core-window.png`, `behavior-selected-wallets.png`, or `token-distribution-sibling-wallets.png`.
- Delete unused intermediate captures before finishing.
- Verify every image link in the report resolves.

Avoid implementation notes, API debugging details, and fix history unless the user explicitly asks for an API test report. Phrase findings with the evidence level clear. Use "direct evidence" for exact raw-data or endpoint-backed facts, and "inference" for role interpretation from views.

## Final Validation

Before reporting completion:

```bash
python skills/user-trace-analysis/scripts/apply_reasoning_graph_patch.py \
  TRACE/reasoning-graph.json \
  TRACE/reasoning-graph-patch-001.json

find TRACE/continued-investigation-assets -maxdepth 1 -type f
rg "continued-investigation-assets/" TRACE/continued-investigation-report.md
git diff --check
```

If the work includes code changes, also run the relevant project checks before committing. Use `bun` for frontend commands and `uv` for backend Python commands.

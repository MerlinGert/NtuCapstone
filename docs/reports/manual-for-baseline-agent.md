# ManiScope Manual For Baseline Agents

This is a compact ManiScope reference for baseline Codex agents. It explains the task, available evidence, and visible UI views without specialized trace-analysis methodology, reasoning graphs, patches, subagents, Agent Workspace behavior, or arbitrary visualization rendering.

## System Purpose

ManiScope is a visual analytics dashboard for investigating possible trade-based price manipulation in cryptocurrency markets. The current datasets are ACT and PNUT on Solana. The app uses holder snapshots, trade logs, transfer logs, OHLC price data, behavior sequences, and detector outputs to help an analyst reason about suspicious wallets, connected groups, and price-aligned behavior.

Treat ManiScope as an exploratory investigation workspace, not a real-time monitor. Useful analysis questions include:

- Which wallets or groups look suspicious?
- Which wallets appear connected by transfers, sequence similarity, shared funding, or detector outputs?
- How does suspicious behavior align with price movement?
- Which suspicious-looking wallets may have benign or functional explanations?
- Which conclusions need raw-data checks rather than visual inspection alone?

## Session Files And Outputs

Baseline sessions live under `.maniscope-chat/baseline-sessions/{sessionId}`. The agent's working directory is the active baseline session root.

Important session files and folders:

- `live-session.json`: recorded user actions, annotations, imported trace records, reordered trace records, and user-authored notes.
- `current-state.json`: latest synced visible UI state and current-view screenshots.
- `images/`: action, annotation, current-view, and attachment images.
- `artifacts/`: generated scripts, copied screenshots, summaries, reports, and other files useful for this chat.
- `session-references/README.md`: baseline session reminder.

ACT and PNUT raw-data directories are available as read-only-by-policy additional directories. Do not edit raw data files. Write scripts, derived data, summaries, copied screenshots, and generated outputs inside the session directory, preferably under `artifacts/`.

Use `uv` for Python scripts and `bun` for JavaScript or TypeScript scripts from the session root. The session is seeded with `pyproject.toml`, `package.json`, and `.gitignore` for temporary analysis work.

## Current-View Screenshot Helper

Baseline sessions include `maniscope_baseline_views.py`. This helper is capture-only. It copies the user's latest synced screenshots into `artifacts/`; it does not change visualization settings, detector parameters, selected users, time windows, scale, granularity, model outputs, or any other UI state.

Available functions:

- `capture_current_token_distribution()`
- `capture_current_kline_chart()`
- `capture_current_behavior_details()`
- `capture_current_views()`
- `artifact_path(name)`

Use the helper when you need local image files for the current visible Token Distribution, K-Line, or Behavior Details views. If a current-view screenshot is missing from `current-state.json`, explain that limitation and use available trace screenshots or raw data instead.

## Control Panel Semantics

The Control Panel determines the data and detector outputs shown in the main views.

Snapshot Configuration:

- `Snapshot Time` selects an hourly holder snapshot.
- `Top Holders Threshold` controls how much of the user-held supply is covered by top holders.
- `Related User Threshold` filters related holders by balance relative to the smallest top-holder balance.
- Updating a snapshot reloads the holder population and reruns detector outputs.

Entity Detection:

- Produces stricter wallet groups.
- Network rules may use direct transfer, transaction count, transfer volume, funding relationship, same sender, and same recipient.
- Similarity rules may use trading action sequence, balance sequence, and earning sequence.
- Entity results appear as orange dashed boundaries in Token Distribution and entity membership context in Behavior Details.

Manipulation Detection:

- Produces suspicious trading events and suspicious labels used by K-Line, Token Distribution, and Behavior Details.
- Round Trip detects buy-then-sell or sell-then-buy sequences whose net position returns close to the starting point with limited earning.
- Same Direction detects consecutive same-side trading behavior.

Link Configuration:

- Produces softer pairwise wallet relationships than Entity Detection.
- Links are exploratory relationship evidence, not proof of common ownership.
- Link results appear as grey overlays in Token Distribution when Show Links is enabled.

## Token Distribution View

Token Distribution is the holder snapshot graph.

Visual encodings:

- Larger nodes represent larger token balances.
- Top holders appear in the main circular region.
- Related users appear around the top-holder population when they pass the related-user threshold.
- Red-stroked nodes are users involved in detected manipulation results under current rules.
- Blue-stroked nodes are not flagged by the current manipulation result.
- Orange dashed boundaries indicate detected entity groups.
- Grey links indicate pairwise relationships from Link Configuration.

Use this view for holder concentration, suspicious clusters, entity boundaries, link structure, connected components, and visible overlap between suspicious labels and top holders.

## K-Line And Manipulation View

The K-Line view combines OHLC price movement with detected manipulation events.

Visual encodings:

- Candlesticks show OHLC price data. Green candles close above open; red candles close below open.
- Light blue bands connect manipulation cards to corresponding chart intervals.
- Cards above the chart represent Round Trip events.
- Cards below the chart represent Same Direction events.
- Cards include a time bin, exact time span, approximate USD amount, and an action-sequence glyph.

Use this view for price phases, manipulation-window timing, card cohorts, price alignment, and whether suspicious behavior occurs before, during, or after price movement.

## Behavior Details View

Behavior Details shows selected wallet or cohort timelines.

Modes:

- Single selected user from Token Distribution.
- Card Users from a clicked manipulation card.
- Related users when a single selected user has related-user context.

Visual encodings:

- Action circles show buys, sells, and transfers along the timeline.
- Balance is shown as history over time.
- Earnings are shown with gain and loss bars.
- Manipulation boxes show detected manipulation windows when available.

Use this view for buy/sell/transfer sequences, role comparison, residual holdings, accumulation, exits, round-trip-like behavior, and whether users in a card behave homogeneously or have differentiated roles.

## User Trace And Annotations

The investigation panel records the user's analysis process.

User Actions:

- Record interaction events such as snapshot updates, detection runs, coin changes, granularity changes, selections, card clicks, zooms, scrolls, and toggles.
- Action records may include source and target screenshots.
- Use actions to infer what the user inspected, changed, or compared.

Annotations:

- Store user notes, source view, timestamp, selected items, and sketch image when available.
- Treat annotation text as user-authored evidence or claims.

Action Tree:

- Organizes actions and annotations as a visual tree.
- Coin changes and snapshot updates form major branches.
- Later interactions attach under the current branch.

Use trace screenshots to reconstruct what the human saw. Use raw data and detector outputs when exact counts, amounts, timestamps, or wallet overlaps are needed.

## Evidence Discipline

Use the right evidence for each claim.

- Visual claims need screenshots or current-view captures.
- Exact counts, amounts, timestamps, overlaps, and role statistics need raw-data or detector-output computation.
- Detector-derived labels are model outputs and need interpretation.
- State uncertainty when visual evidence and raw data do not fully agree.

Do not treat red strokes, entity boundaries, links, or manipulation boxes as final proof. They are evidence cues that should be checked against raw data, visual context, and possible benign explanations.

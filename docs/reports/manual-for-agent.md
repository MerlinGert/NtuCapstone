# ManiScope Manual For Agents

This is a compact ManiScope reference for Codex agents. It keeps the system and visualization semantics needed for trace analysis and omits user-facing product instructions such as chat UI usage, import/export walkthroughs, and study participant controls.

## System Purpose

ManiScope is a visual analytics dashboard for investigating possible trade-based price manipulation in cryptocurrency markets. The current datasets are ACT and PNUT on Solana. The app uses holder snapshots, trade logs, transfer logs, OHLC price data, behavior sequences, and detector outputs to help an analyst reason about suspicious wallets, connected groups, and price-aligned behavior.

Treat ManiScope as an exploratory investigation workspace, not a real-time monitor. The relevant analytical questions are usually:

- Which wallets or wallet groups look suspicious?
- Which wallets appear connected by transfers, sequence similarity, shared funding, or detector outputs?
- How do suspicious events align with price movement?
- Which apparent suspicious labels have benign or functional explanations?
- Which conclusions depend on detector parameters and need robustness checks?

## Session And Workspace State

Specialized sessions live under `.maniscope-chat/sessions/{sessionId}`. The agent's working directory is the active session root.

Important session files:

- `live-session.json`: canonical human trace, including user actions, annotations, imported trace records, reordered trace records, and user-authored notes.
- `current-state.json`: canonical Human Workspace state, kept for backward compatibility.
- `workspaces/human/current-state.json`: mirrored Human Workspace state.
- `workspaces/agent/current-state.json`: private Agent Workspace state.
- `images/`: action, annotation, current-view, and attachment images.
- `artifacts/`: generated analysis files, rendered evidence, scripts, reports, graph JSON, and patches.
- `analysis-runs/{runId}.json`: closed trace-window metadata for a Codex analysis turn.

The Human Workspace is the source of truth for user trace changes. The Agent Workspace is independent visual-analysis state for the agent. Agent-side selections, zoom windows, detector settings, and rendered evidence must not overwrite the human page state or append to the human trace.

Each specialized Codex Chat turn has a closed trace window. Use the run `startAnchor` as the maximum trace boundary for that turn. If the live trace advances while working, those later actions are out of scope and should be handled by a later Update Analysis run.

## Raw Data And Outputs

ACT and PNUT raw-data directories are available as read-only-by-policy additional directories. Do not edit raw data files. Write scripts, derived data, summaries, rendered evidence, and analysis outputs inside the session directory, preferably under `artifacts/`.

Use `uv` for Python scripts and `bun` for JavaScript or TypeScript scripts from the session root. The session is seeded with `pyproject.toml`, `package.json`, and `.gitignore` for temporary analysis work.

## Control Panel Semantics

The Control Panel drives the data and model outputs shown in the three major views.

Snapshot Configuration:

- `Snapshot Time` selects an hourly holder snapshot.
- `Top Holders Threshold` controls how much of the user-held supply is covered by top holders. The default is `0.3`.
- `Related User Threshold` filters related holders by balance relative to the smallest top-holder balance. The default is `0.2`.
- Updating a snapshot reloads the holder population and reruns entity, link, and manipulation outputs.

Entity Detection:

- Produces stricter wallet groups.
- Network rules include direct transfer, minimum transaction count, minimum volume, funding relationship, same sender, and same recipient.
- Similarity rules include trading action sequence, balance sequence, and earning sequence.
- Manipulation-based grouping can connect users by proximity in detected manipulation behavior.
- Results appear as orange dashed entity boundaries in Token Distribution and as entity membership in Behavior Details.

Manipulation Detection:

- Produces suspicious trading events and suspicious labels used by K-Line, Token Distribution, and Behavior Details.
- Round Trip detects buy-then-sell or sell-then-buy sequences whose net position returns close to the starting point with limited earning.
- Same Direction detects consecutive same-side actions.
- Entity-based manipulation detection merges trades from wallets in a detected entity before running manipulation detection.

Link Configuration:

- Produces softer pairwise relationships than Entity Detection.
- Links are exploratory relationship evidence, not proof of common ownership.
- Results appear as grey link overlays in Token Distribution when Show Links is enabled.

For model-derived claims, consider Model Action robustness checks by varying relevant detector parameters or comparing alternative outputs.

## Token Distribution View

Token Distribution is the holder snapshot graph.

Visual encodings:

- Larger nodes represent larger token balances.
- Top holders appear in the main circular region.
- Related users appear around the top-holder population when they pass the related-user threshold.
- Red-stroked nodes are users involved in detected manipulation results under current manipulation rules.
- Blue-stroked nodes are not flagged by the current manipulation result.
- Orange dashed boundaries indicate detected entity groups.
- Orange dashed connections show related users connected to an entity neighborhood.
- Grey links indicate pairwise relationships from Link Configuration.

Interactions:

- Hovering a node can reveal address, balance, and detector context.
- Clicking a node selects that user and populates Behavior Details.
- The Scale slider changes graph scale without rerunning detection.
- The Show Links toggle controls whether link overlays are visible.

Use this view for concentration, suspicious clusters, entity boundaries, link structure, connected components, and visible overlap between suspicious labels and top holders.

## K-Line And Manipulation View

The K-Line view combines OHLC price movement with detected manipulation events.

Visual encodings:

- Candlesticks show OHLC price data. Green candles close above open; red candles close below open.
- Light blue bands connect manipulation cards to corresponding chart intervals.
- Cards above the chart represent Round Trip events.
- Cards below the chart represent Same Direction events.
- Cards include a time bin, exact time span, approximate USD amount, and an action-sequence glyph.

Interactions:

- Granularity can be `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `3d`, or `1w`.
- Clicking a manipulation card loads participating users into Behavior Details as Card Users.
- Card rows have independent horizontal scrolling.
- K-Line and Behavior Details can synchronize absolute time windows when compatible.

Use this view for price phases, manipulation-window timing, card cohorts, price alignment, and whether suspicious behavior occurs before, during, or after price movement.

## Behavior Details View

Behavior Details shows selected wallet or cohort timelines.

Modes:

- Single selected user from Token Distribution.
- Card Users from a clicked manipulation card.
- Related users when a single selected user has related-user context.

Visual encodings:

- Action circles show buys, sells, and transfers along the timeline.
- Balance is shown as an area or bar-like history depending on row and zoom level.
- Earnings are shown with gain and loss bars.
- Manipulation boxes show detected manipulation windows when available.

Controls:

- Show Related Users is available for single-user inspection.
- Sequential Time rearranges behavior sequences by event order rather than absolute time.
- Show Manipulation Boxes toggles detected windows.
- Sync Time can align Behavior Details with the K-Line absolute time window when Sequential Time is off.

Use this view for buy/sell/transfer sequences, role comparison, residual holdings, accumulation, exits, round-trip-like behavior, and whether users in a card behave homogeneously or have differentiated roles.

## Trace Evidence

The bottom investigation panel records and organizes human analysis.

User Actions:

- Record interaction events such as snapshot updates, detection runs, coin changes, granularity changes, selections, card clicks, zooms, scrolls, and toggles.
- Action records may include source and target screenshots, depending on capture settings.
- Use actions to infer what the user inspected, changed, or compared.

Annotations:

- Store snapshot annotations, source view, timestamp, text note, selected items, and sketch image when available.
- Treat annotation text as user-authored evidence or claims.
- User-authored claims in annotations should become Finding nodes in `reasoning-graph.json`.

Action Tree:

- Organizes actions and annotations as a visual tree.
- Coin changes and snapshot updates form major branches.
- Later interactions attach under the current branch.
- High-level findings created from annotation nodes are user-authored synthesis records.

Use trace screenshots to reconstruct what the human saw. Use rendered views and raw data for new follow-up evidence.

## LLM Analysis Artifacts

The LLM Analysis tab renders from graph-first artifacts in `artifacts/`.

Source of truth:

- `reasoning-graph.json`: base graph reconstructed from user trace evidence.
- `reasoning-graph-patch*.json`: agent follow-up, skeptical, subagent, or incremental evidence.
- Generated forest JSON or Markdown files are optional exports and are not the UI source of truth.

Display behavior:

- The UI validates the base graph and valid patches, applies patches in deterministic order, and projects a compact Hypothesis and Finding hierarchy.
- Internal Task, AnalyticQuestion, AnalyticActivity, and Interaction nodes are hidden from the card view but remain in the graph for traceability.
- Mid-level Findings that answer hidden AnalyticQuestions should still appear in the displayed Finding hierarchy.
- User Findings and agent-created patch Findings are visually distinguished.
- `New` badges are tied to agent run-start snapshots and mark newly visible Hypothesis or Finding cards during later runs.

Graph-writing expectations:

- Full analysis should write and validate `reasoning-graph.json` early.
- Incremental analysis should write `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json`.
- Skeptical or counterevidence Findings should use `refines` or `contradicts`, not support-only edges.
- Parent Findings should add synthesis, qualification, scope, contrast, uncertainty, or aggregation across evidence. If one concrete Finding is enough to answer an Analytic Question or support, refine, or contradict a Hypothesis, connect it directly instead of creating a single-child rephrasing chain.
- `current-reasoning-graph.json` is a derived reading aid for agents and debugging, not the frontend source of truth.

## Evidence Discipline

Use the right evidence route for each claim.

- Visual claims need screenshots or rendered visual evidence.
- Exact counts, amounts, timestamps, overlaps, medians, means, and role statistics need raw-data or model-output computation.
- Detector-derived claims need model-output inspection and, when important, parameter or threshold robustness checks.
- Synthesis claims should state which lower-level Findings they combine.

Do not treat red strokes, entity boundaries, links, or manipulation boxes as final proof. They are model outputs that need interpretation against raw data, visual evidence, and possible benign alternatives.

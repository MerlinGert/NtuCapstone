# ManiScope User Manual

## What ManiScope is

ManiScope is a visual analytics dashboard for assessing trade-based price-manipulation risk on cryptocurrency markets. The current frontend focuses on memecoin activity on decentralized exchanges and ships with two Solana token datasets, ACT and PNUT. It loads precomputed trade logs, transfer logs, hourly balance snapshots, and per-user behavior sequences, then runs entity detection, link detection, and manipulation detection on top of those datasets.

ManiScope is best understood as an investigator's workspace rather than a real-time monitoring system. It helps answer questions such as "who was manipulating this token over the observed period", "which wallets appear connected", and "how did suspicious activity line up with price movement". The expected workflow is exploratory: choose a coin and snapshot, inspect the distribution and manipulation views, select users or manipulation cards, annotate evidence, and export the session when the investigation is ready to share.

## Screen layout

The dashboard fills the browser window. The current UI is arranged as three vertical columns under a header.

```
+---------------------------------------------------------------------------------------------+
| ManiScope | Session | Human Workspace | Open Agent Workspace | Coin: ACT PNUT | Export Import |
+------------------+------------------------------+------------------------------+
| Control Panel    | Token Distribution           | ACT or PNUT K-Line           |
|                  |                              | round-trip cards             |
| Snapshot         | top-holder graph             | candlestick chart            |
| Entity           | entity circles and links     | same-direction cards         |
| Manipulation     +------------------------------+------------------------------+
| Link             | User Actions | Annotations   | Behavior Details             |
|                  | Action Tree                 | selected user or card users  |
+------------------+------------------------------+------------------------------+
```

The header contains the product name, the session chip, a workspace badge, the Codex Chat button, the ACT and PNUT radio buttons, and session import/export controls. In the Human Workspace, the header also includes **Open Agent Workspace**, which opens the same session in a separate `/agent` page for side-by-side analysis.

The left column is the Control Panel. The middle column contains the Token Distribution view on top and a tabbed investigation panel on the bottom. The right column contains the K-line and manipulation-card view on top and Behavior Details on the bottom.

## Human And Agent Workspaces

Each ManiScope browser page belongs to one workspace role.

- `/{sessionId}/human` is the Human Workspace. It is the source of truth for user interactions, annotations, imported trace data, reordered trace items, and user-authored notes.
- `/{sessionId}/agent` is the Agent Workspace. It is an independent visual-analysis page for Codex or another analyst to explore the same session without changing the human page state.
- `/{sessionId}` remains valid and opens the Human Workspace. Visiting `/` creates a fresh 5-character session and redirects to the Human Workspace.

Both workspaces read the shared canonical trace stored in the session. The human page writes the canonical trace when you interact, annotate, import, reorder, or sync the session. The agent page refreshes that canonical trace in the background so it can see what the human has done, but agent-side selections, detector settings, zoom windows, selected users, and rendered evidence are saved separately. The Action Tree is read-only in the Agent Workspace.

The backward-compatible `current-state.json` is the human current state. The human and agent workspaces also keep separate `workspaces/human/current-state.json` and `workspaces/agent/current-state.json` files. This means the agent can run different detector settings, inspect a different snapshot, select different users, or render evidence images without overwriting the human's visible analysis.

## Control Panel

The Control Panel drives the computation shown in the other views. It is vertically scrollable and currently contains four groups in this order: Snapshot Configuration, Entity Detection, Manipulation Detection, and Link Configuration.

### Snapshot Configuration

Snapshot Configuration controls the holder population used by the rest of the dashboard.

- **Snapshot Time** selects an hourly timestamp from the loaded coin dataset. On first load and after a coin switch, the app selects the latest available snapshot time.
- **Top Holders Threshold** controls how much of the user-held supply should be covered by the top-holder set. The default is `0.3`.
- **Related User Threshold** filters related holders by balance relative to the smallest top-holder balance. The default is `0.2`.
- **Update Snapshot** reloads the snapshot and then automatically reruns entity detection, link detection, and manipulation detection with the current configurations.

Updating a snapshot also records a system action in the User Actions and Action Tree tabs.

### Entity Detection

Entity Detection clusters wallets into stricter wallet groups. The Run Detection button updates entity groups and, when entity-based manipulation detection is enabled, reruns manipulation detection so the K-line and Behavior Details views stay aligned with the new entities.

Entity Detection has three collapsible rule families.

- **Network Based** can be enabled as a family and includes Direct Transfer, Min Tx Count, Min Volume, Funding Relationship, Same Sender, and Same Recipient controls. The default family toggle is off, but Direct Transfer, Min Tx Count, and Funding Relationship are checked inside the section.
- **Similarity Based** is enabled by default. It includes Trading Action Sequence, Balance Sequence, and Earning Sequence controls. Balance Sequence is enabled by default with 1-hour granularity and similarity `0.6`.
- **Manipulation Based** can group users by proximity in detected manipulation behavior. It is off by default and exposes a Max Time Diff value.

The result appears as orange dashed entity boundaries in the Token Distribution view and as entity membership in Behavior Details when a clustered user is selected.

### Manipulation Detection

Manipulation Detection updates suspicious trading patterns shown in the K-line view, the Token Distribution node strokes, and the Behavior Details manipulation boxes.

Two rule families are available.

- **Round Trip** detects buy-then-sell or sell-then-buy sequences whose net position returns close to the starting point with limited earning. The default parameters are Max Time Diff `120`, Max Position Diff `100`, Max Earning `1000`, and Enable Entity Based checked.
- **Same Direction** detects consecutive same-side actions. The default parameters are Max Time Diff `10`, Min Seq Length `5`, Max Diff Direction `0`, and Enable Entity Based checked.

Entity-based detection merges trades from wallets inside the same detected entity before the manipulation detector runs. This can reveal coordinated behavior that would be weaker or invisible when each address is analyzed alone.

### Link Configuration

Link Configuration detects softer pairwise relationships between holders. It uses the same broad rule families as Entity Detection but is intended to be more exploratory. Update Links refreshes grey link overlays in the Token Distribution view.

The current Link Configuration defaults are:

- Network Based is off, with Direct Transfer available and Min Tx Count set to `1`.
- Similarity Based is on, with Trading Action Sequence enabled, Action Only matching, Min Seq Length `3`, and Max Time Diff `120`.
- Manipulation Based is on, with Max Time Diff `120`.

Use entity detection when you want stricter grouping. Use link detection when you want weaker but potentially useful relationship cues.

## Token Distribution View

The Token Distribution view is the top panel in the middle column. It shows the current snapshot as a node-link distribution graph.

The header shows the snapshot time, a **Show Links** toggle, a **Scale** slider, the active-user count, and a camera button for snapshot annotation.

The visual encoding is:

- Top holders appear in the main circular region. Larger nodes represent larger token balances.
- Related users appear around the top-holder population when they pass the related-user threshold.
- Red-stroked nodes are users involved in detected manipulation results under the current manipulation rules.
- Blue-stroked nodes are not flagged by the current manipulation result.
- Orange dashed boundaries mark detected entity groups.
- Orange dashed connections show related users connected to an entity neighborhood.
- Grey links appear when Link Configuration finds pairwise relationships and Show Links is enabled.

Hovering a node shows a tooltip with its address, balance, and available detection context. Clicking a node selects that user and populates Behavior Details. The Scale slider changes the graph scale without rerunning detection.

The camera button opens a Token Snapshot annotation dialog. The snapshot dialog preserves the graph and lets you select nodes, sketch over the view, add text, and save the annotation into the Annotations and Action Tree tabs.

## K-Line And Manipulation View

The K-line view is the top panel in the right column. It combines price movement with detected manipulation events.

The header contains the current coin label, granularity buttons, and a camera button. The current granularity choices are `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `3d`, and `1w`.

The central chart shows OHLC candlesticks. Green candles close above open and red candles close below open. The view also displays light blue connection bands that link manipulation cards to the corresponding time intervals on the chart.

Manipulation cards are arranged around the chart:

- Cards above the candlestick chart represent Round Trip events.
- Cards below the candlestick chart represent Same Direction events.
- Each card shows the time bin, exact time span, approximate USD amount, and a small action-sequence glyph.
- Horizontal scroll bars let you move through the card rows independently.

Clicking a manipulation card loads its participating users into Behavior Details as "Card Users". Hovering cards for several seconds records a hover action when hover auto-capture is enabled.

The K-line and Behavior Details views can synchronize time windows. A Sync Time button appears when the opposite view has an active time window and the current mode can accept synchronization. When Sequential Time is enabled in Behavior Details, the Behavior Details sync button is disabled because that chart is no longer using the same absolute time scale.

## Behavior Details View

Behavior Details is the bottom panel in the right column. It is empty until you click either a Token Distribution user node or a manipulation card.

When a Token Distribution user is selected, the panel shows that user and available related users. If the user belongs to an entity, an entity badge and member count appear. When a manipulation card is selected, the panel switches to Card Users mode and shows the users involved in that card.

The behavior chart combines three aspects of holder activity.

- Action circles show buys, sells, and transfers along the timeline.
- Balance is shown as an area or bar-like history depending on the row and zoom level.
- Earnings are shown with gain and loss bars.

Controls in this panel include:

- **Show Related Users**, available when a single selected user is being inspected.
- **Sequential Time**, which rearranges behavior sequences by event order rather than absolute timestamps.
- **Show Manipulation Boxes**, available when manipulation results exist.
- **Sync Time**, available when the K-line view has a compatible selected time window.
- A camera button for Behavior Snapshot annotation.

Clicking a user label inside Behavior Details can switch the selected user. Zooming the behavior chart records a zoom action and may capture a view snapshot if that action category is enabled.

## Codex Chat

The floating Codex Chat sidebar lets you ask the agent to inspect the current session trace, explain interaction paths, recommend investigation steps, or continue analysis. Before each message is sent, ManiScope syncs the shared live trace and the current workspace state. Messages from the Human Workspace attach human workspace screenshots. Messages from the Agent Workspace attach agent workspace screenshots.

Chat history and generated artifacts are shared at the session level. The agent prompt distinguishes three kinds of context: the shared canonical trace, the human current state, and the agent's private exploratory state. Agent visual exploration should use the Agent Workspace and should not append to the human action trace unless you explicitly ask for durable artifacts or reasoning patches.

Codex SDK network access is enabled by default for the chat agent so it can reach the local ManiScope services and fetch external references when an investigation needs them. For restricted offline runs, start the bridge with `CODEX_NETWORK_ACCESS=false`.

The Codex Chat panel is floating. Drag its header to move it, or drag the lower corners to resize it. The panel keeps its local position and size in the browser.

During an agent turn, Thinking and Agent Activity appear above the assistant response. When the turn completes, these sections collapse, while the latest activity remains visible as a compact status card.

Assistant responses can include Markdown text, generated artifacts, JSON files, Markdown reports, and image previews. When the agent mentions a local image, Markdown, or JSON path in its response, ManiScope links it through the session artifact endpoint if the file is under the active session folder, the project folder, or another explicitly allowed artifact root. Valid images are copied into the session `artifacts/` folder for preview, while Markdown and JSON outputs are shown as downloadable artifact links. Generated files should normally be saved under the session `artifacts/` folder for chat evidence, or under a trace `analysis-results/` folder for durable trace-analysis artifacts.

For visual follow-up work, each session also includes a managed Python helper named `maniscope_visualization.py`. The agent can import this file from the session folder to render Token Distribution, K-line, and Behavior Details images through an isolated Agent Workspace browser page. These renders save PNG evidence into the shared session `artifacts/` folder without changing the Human Workspace state.

## User Actions, Annotations, Action Tree, And LLM Analysis

The bottom panel in the middle column is now part of the investigation workflow. It has four tabs: User Actions, Annotations, Action Tree, and LLM Analysis. The default active tab is Action Tree.

### User Actions

The User Actions tab records interaction events as the investigation proceeds. Examples include snapshot updates, detection runs, coin changes, K-line granularity changes, user selections, card clicks, zooms, scrolls, and toggle changes.

The count badge shows how many actions are currently recorded. Each action card can be expanded to show JSON details and view state. When snapshot capture is enabled for the action category, cards also show source and target thumbnails. Clicking a thumbnail opens the captured image in a separate browser tab.

The small settings button opens auto-capture controls. Current categories are Hover, Zoom / Scroll, Click / Select, Change / Toggle, and System. By default, Click / Select, Change / Toggle, and System are enabled, while Hover and Zoom / Scroll are disabled. Capture quality can be set to Thumbnail or Full. The current default is Full.

Hover actions are intentionally delayed before they are logged, so quick accidental flyovers do not immediately create records.

### Annotations

The Annotations tab lists snapshot annotations created from the camera buttons or the Option+S shortcut. Each annotation stores the source view, timestamp, text note, selected items when the snapshot supports selection, and the sketch image if one was captured.

Annotation cards can be expanded to inspect selected item details and the full sketch image.

### Action Tree

The Action Tree tab shows actions and annotations as a visual tree. The legend distinguishes System, Interact, Zoom/Scroll, Hover, Annotation, and Other nodes. Coin changes and snapshot updates form major branches, while later interactions attach beneath the current branch.

The camera-shaped **Create Finding** button starts multi-select mode for annotation nodes. Select one or more annotation nodes, click Confirm, enter a finding note, and save it. High-level findings are added back into the annotation record and can reference the annotations they summarize.

Clicking an annotation node opens its details. Clicking a high-level finding node opens the finding text and its referenced annotations.

### LLM Analysis

The LLM Analysis tab displays trace-analysis artifacts generated by Codex. It asks the backend for the current analysis artifact manifest, then loads the available User Reasoning Forest and Reasoning Graph Patch JSON files from the session `artifacts` folder. The tab renders a compact findings hierarchy: top-level Hypotheses contain user Findings and agent-created patch Findings, while internal Tasks, Analytic Questions, Analytic Activities, and Interactions are hidden from the card view. Those hidden nodes remain in the source JSON for traceability. Mid-level Findings that answer hidden Analytic Questions are still shown in the Finding hierarchy, and duplicated canonical Findings are collapsed so the same answer does not appear twice under one Hypothesis. Agent-created patch Findings are shown in pink and attached to the hypothesis or Finding they support, answer, qualify, or synthesize. Cards with screenshot or render provenance show small thumbnails while expanded. Clicking a card opens its details, including evidence summaries, patch rationales, and larger evidence images when available.

The tab refreshes when it is opened, when you click Refresh, when Codex announces a new relevant artifact, and through a lightweight periodic check while the tab is active. The backend does not keep a long-running file watcher; it scans session artifacts on request and reports the latest recognized files. Manifest and artifact JSON requests bypass browser cache so regenerated analysis files appear without stale results.

## Snapshot Annotation Workflow

Three main views support snapshot annotation: Token Distribution, K-line, and Behavior Details. Use the camera button in a view header, or place the mouse over a supported view and press Option+S on macOS. The shortcut is implemented as Alt+S, so keyboard behavior depends on the operating system and browser.

Each snapshot dialog contains a floating toolbar.

- **Select / Lasso** selects items when the snapshot type supports selection.
- **Pen** draws freehand marks.
- **Box** draws rectangular callouts.
- **Eraser** removes nearby sketches.
- Color swatches switch between red, blue, green, orange, and black.
- **Clear All** removes all sketch marks in the snapshot.

Token snapshots can select holder nodes and show selected node details. Behavior snapshots can select user tracks or event circles and show selected item details. K-line snapshots are image-based and mainly support sketching plus text notes.

Entering text and clicking Annotate saves the annotation, closes the snapshot dialog, and switches the bottom middle panel to the Annotations tab. Empty text is allowed, so a sketch-only annotation can still be recorded.

## Exporting A Session

The Export button in the header opens an Export Session dialog. The dialog shows the current action count and annotation count. It also offers an **Include snapshot images (PNG)** checkbox.

- When the checkbox is enabled, the exported zip includes PNG files for action thumbnails and annotation sketches under `images/`. The JSON stores paths such as `images/action-0001-target-kline-chart-01.png` instead of inline image strings.
- When the checkbox is disabled, the exported zip still contains the JSON file, but screenshot and sketch image payloads are stripped.

Click **Download ZIP** to save a file named like `maniscope-session-ACT-YYYYMMDD-HHMMSS.zip`. Inside the archive, `session.json` contains the action and annotation metadata, and `images/` contains exported PNG files when image export is enabled. The current Import button is disabled, so exported files are mainly for external review or later development workflows.

## Coin Selector

The ACT and PNUT radio buttons in the header switch the active dataset. Switching coins resets the current visual state, clears selected users and cached results, reloads the available snapshot times, selects the latest available time, and runs the initialization pipeline for the selected coin.

Coin switches are logged as system actions. They also create a new branch in the Action Tree.

## Detection Rule Reference

The defaults below summarize the current frontend configuration.

### Entity Detection Defaults

| Rule family | Default | Key settings |
|---|---:|---|
| Network Based | Off | Direct Transfer on, Min Tx Count on with value 3, Min Volume off, Funding Relationship on |
| Similarity Based | On | Trading Action Sequence off, Balance Sequence on with 1h granularity and 0.6 similarity, Earning Sequence off |
| Manipulation Based | Off | Max Manipulation Time Diff 2 |

### Link Configuration Defaults

| Rule family | Default | Key settings |
|---|---:|---|
| Network Based | Off | Direct Transfer on, Min Tx Count on with value 1, Funding Relationship off |
| Similarity Based | On | Trading Action Sequence on, Action Only, Min Seq Length 3, Max Time Diff 120 |
| Manipulation Based | On | Max Manipulation Time Diff 120 |

### Manipulation Detection Defaults

| Parameter | Round Trip | Same Direction |
|---|---:|---:|
| Enabled | Yes | Yes |
| Max Time Diff | 120 | 10 |
| Max Position Diff | 100 | Not used |
| Max Earning | 1000 | Not used |
| Min Seq Length | Not used | 5 |
| Max Diff Direction | Not used | 0 |
| Entity Based | Yes | Yes |

## Recommended Workflow

1. Choose ACT or PNUT in the header.
2. Pick a snapshot time and adjust the holder thresholds if needed.
3. Click Update Snapshot. This refreshes the snapshot and reruns the current detection pipeline.
4. Scan the Token Distribution view for dense red-stroked regions, orange dashed entity boundaries, and grey links.
5. Use the K-line view to find time intervals with many Round Trip or Same Direction cards.
6. Click a suspicious holder node or a manipulation card to populate Behavior Details.
7. Use Show Related Users, Sequential Time, Show Manipulation Boxes, zooming, and Sync Time to compare wallet behavior with price movement.
8. Open snapshots from the Token Distribution, K-line, or Behavior Details views when you find evidence worth recording.
9. Add annotation text, sketches, selected nodes, or selected behavior items as needed.
10. Use the Action Tree to review the investigation path and combine annotations into high-level findings.
11. Export the session JSON when the action trail and annotations are ready to share.

## Things That Are Not Obvious From The UI

Update Snapshot is not just a visual refresh. It fetches snapshot data, reruns entity detection, reruns link detection, and reruns manipulation detection with the current settings.

Run Detection under Entity Detection can also update manipulation results when entity-based manipulation rules are active. This is because changing entities changes the merged trade sequences used by entity-based manipulation detection.

The bottom investigation panel is part of the analysis state. User actions, annotations, and findings are session data, and they are what the Export workflow serializes.

The Import button is visible but disabled in the current frontend. The code has parsing and conflict-handling helpers, but users cannot trigger them from the visible UI.

Sequential Time changes the meaning of the Behavior Details x-axis. Use it to compare action order across wallets. Turn it off when you need strict alignment with K-line time.

The Show Related Users toggle appears only for single-user inspection. When a manipulation card is selected, Behavior Details shows Card Users instead.

The dashboard still does not surface wallet labels in the main UI. If a top holder is an exchange or contract address, that context may affect interpretation, but the current frontend does not display those labels directly.

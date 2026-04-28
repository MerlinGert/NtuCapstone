# User Trace Analysis Skill

Use this skill when analyzing a ManiScope exported user-interaction trace, especially a folder containing `session.json` plus screenshot images. The goal is to reconstruct what the user was trying to do, what insights they explicitly captured or implicitly discovered, what action recommendations follow, and how those claims map back to trace steps.

For a full trace analysis, produce two Markdown artifacts unless the user asks for a lighter output:

- `TRACE/analysis-report.md`: narrative analysis with evidence, rationale, caveats, intentions, insights, and recommendations.
- `TRACE/trace-step-map.md`: traceability map linking user actions and annotations to intentions, insights, and recommendations.

## 1. Clarify The Task When Needed

Ask concise questions before deep analysis if the request leaves an important choice ambiguous. Useful clarification questions include:

- What level of evidence should the report use: only the interaction trace, or also local ACT/PNUT source data for validation?
- Should inferred findings be conservative, speculative, or hypothesis-generating?
- Should the output be a short summary, a structured Markdown report, a table-first evidence memo, or a presentation-ready narrative?
- Who is the audience: system designer, crypto investigator, research evaluator, or user-study analyst?
- Should the analysis focus on user cognition and workflow, market/manipulation findings, or both?
- Should screenshots be treated as primary evidence, or only as supporting context for `session.json`?
- Do you want exact wallet addresses preserved, shortened, anonymized, or grouped by role?
- Should the step map use compact analytical steps, raw action-level nodes, or both?
- Should the step map include a Mermaid graph, a matrix only, or a graph plus matrix?
- Should confidence labels be included for intentions, insights, and recommendations?
- Should external web evidence be used to verify market events such as listings, announcements, or news? If yes, browse and cite sources.
- Are there known ground-truth events, labels, or hypotheses that should be checked against the trace?
- Should the output include recommendations for product/UI improvement, investigation next steps, or both?

If the user specifies the trace path and asks for an analysis, proceed without blocking unless one of these choices materially changes the expected output.

## 2. Inputs To Gather

Start by understanding both the system and the trace. Do not infer view meaning from screenshots alone.

### Required trace files

- `session.json`: metadata, actions, annotation records, view states, selected users, clicked card users, snapshot categories, and image paths.
- `images/`: action screenshots and annotation screenshots.

Key `session.json` fields:

- `coin`, `exportedAt`, `exportFormat`, `includesSnapshots`, `imageCount`.
- `userActionSequence[]`: `timestamp`, `actionType`, `sourceView`, `targetView`, `userId`, `actionInfo`, `relatedViewWithViewState`, `sourceSnapshot`, `targetSnapshot`.
- `annotationRecords[]`: `id`, `timestamp`, `sourceView`, `text`, `selectedItems`, `sketchImagePath`, `isInsight`.
- `config.snapshotCategories`: tells which action types have screenshots and which may be missing screenshots by design.

### Required documentation

- `docs/reports/user-manual.en.md`: current workflow, view meanings, visual encodings, controls, and expected analysis flow.

Use the manual to interpret:

- Token Distribution graph, entity groups, links, suspicious node styling.
- K-line manipulation cards, round-trip versus same-direction placement.
- Behavior Details chart encodings, sequential time, related users, manipulation boxes.
- User Actions, Annotations, and Action Tree semantics.

### Useful frontend source

Read these files when interpreting a trace:

- `front/src/components/CryptoVis.vue`: layout, action logging, source/target view inference, snapshot capture, export/import state, selected users, card clicks, coin/snapshot/detection handlers.
- `front/src/components/ControlPanel.vue`: snapshot, entity, link, and manipulation configuration controls.
- `front/src/components/TokenDistribution.vue`: graph semantics, suspicious node logic, links, entity boundaries, hover/select logging.
- `front/src/components/CandlestickChart.vue`: granularity options, manipulation-card aggregation, card click users, hover/scroll logging, K-line screenshot capture.
- `front/src/components/BehaviorDetails.vue`: behavior timeline encodings, buy/sell colors, transfers, balance/earning areas, manipulation boxes, sequential time, related users, label clicks.
- `front/src/components/UserActionTimeline.vue`: action display names and capture category behavior.
- `front/src/components/AnnotationTimeline.vue`: annotation display semantics.
- `front/src/components/UserActionTree.vue`: action-tree and high-level insight behavior.
- `front/src/utils/sessionIO.js`: export schema, image path mapping, stripped versus included snapshot behavior.

### Optional local data for validation

Use local data when the request asks for insights about the domain, not just interaction intent:

- `front/public/data/ACT_OHLC.json` or `front/public/data2/PNUT_OHLC.json`: price and granularity data.
- `front/public/data/sorted_trades.csv` or `data2/sorted_trades.csv`: wallet trade timing, buy/sell counts, USD totals, counterparties.
- `front/public/data/sorted_transfers.csv` or `data2/sorted_transfers.csv`: direct funding/transfer evidence.
- `front/public/data/user_behavior_sequences.json`: per-wallet behavior events.
- `front/public/data/user_balance_1d.json`, `user_balance_1h.json`, `user_balance_1min.json`: residual holdings and balance changes.
- `front/public/data/user_earnings_1d.json`, `user_earnings_1h.json`, `user_earnings_1min.json`: realized earning patterns.
- `front/public/data/user_relations.json`, `simplified_owner_labels.json`: relationship and label context.

Treat local data validation as supporting evidence. Separate it from what the user actually saw during the trace.

## 3. Efficient Inspection Commands

Use `rg` and `jq` first. Adjust paths as needed.

Basic trace summary:

```bash
jq '{coin, exportedAt, exportFormat, includesSnapshots, imageCount, actionCount:(.userActionSequence|length), annotationCount:(.annotationRecords|length), config:.config}' TRACE/session.json
```

Action timeline:

```bash
jq -r '.userActionSequence | to_entries[] | [(.key|tostring), .value.timestamp, .value.actionType, .value.sourceView, .value.targetView, (.value.userId|tostring), (.value.actionInfo|tojson), (.value.relatedViewWithViewState|tojson)] | @tsv' TRACE/session.json
```

Annotation timeline:

```bash
jq -r '.annotationRecords | to_entries[] | [(.key|tostring), (.value.id|tostring), .value.timestamp, .value.sourceView, (.value.isInsight|tostring), (.value.text|gsub("\n";" ")), ((.value.selectedItems // [])|length|tostring), (.value.sketchImagePath // .value.imagePath // "")] | @tsv' TRACE/session.json
```

Image mapping:

```bash
jq -r '.userActionSequence | to_entries[] | {i:.key, type:.value.actionType, source:.value.sourceView, target:.value.targetView, sourceImages:(.value.sourceSnapshot // [] | map(.imagePath)), targetImages:(.value.targetSnapshot // [] | map(.imagePath))} | @json' TRACE/session.json
```

Clicked card users:

```bash
jq -r '.userActionSequence[] | select(.actionType=="click_manipulation_card") | .timestamp + "\t" + (.actionInfo.cardUsers|length|tostring) + "\t" + (.actionInfo.cardUsers|join(","))' TRACE/session.json
```

Repeated selected-card users:

```bash
jq -r '[.userActionSequence[] | select(.relatedViewWithViewState.selectedCardUsers and (.relatedViewWithViewState.selectedCardUsers|length>0)) | .relatedViewWithViewState.selectedCardUsers[]] | group_by(.) | map({user:.[0], count:length}) | sort_by(-.count,.user)[] | [.count, .user] | @tsv' TRACE/session.json
```

Screenshot metadata:

```bash
find TRACE/images -maxdepth 1 -type f -print0 | xargs -0 file
```

When many screenshots exist, create contact sheets with a small local script, then inspect key images individually. Do not rely only on thumbnails for fine-grained chart interpretation.

## 4. Analysis Workflow

### Step 1: Build a factual timeline

Create a chronological reconstruction with:

- Action index and timestamp.
- Source view and target view.
- Action type and important `actionInfo`.
- Selected user or selected card users.
- Current view state: `selectedUser`, `selectedCardUsers`, `klineTimeWindow`, `behaviorTimeWindow`, `snapshotTime`.
- Available action screenshots.
- Nearby annotation records.

Distinguish:

- Direct actions: logged clicks, toggles, hovers, scrolls, granularity changes.
- Derived state: selected users or time windows visible in `relatedViewWithViewState`.
- User-authored insights: annotation text.
- Analyst inferences: conclusions derived from several actions or from local data validation.

### Step 2: Interpret screenshots with view semantics

Use annotation screenshots as primary evidence for what the user considered meaningful. Use action screenshots for context and before/after verification.

For Token Distribution, inspect:

- Dense suspicious clusters.
- Entity boundaries.
- Relationship links and connected components.
- Selected or hovered nodes.

For K-line, inspect:

- Price phases.
- Daily or intraday granularity.
- Round-trip cards above the chart.
- Same-direction cards below the chart.
- Card windows marked by user sketches.

For Behavior Details, inspect:

- Coordinated clusters of buy points.
- Sell clusters.
- Direct transfer arrows.
- Red manipulation boxes.
- Balance areas and residual holdings.
- Differences between Sequential Time and absolute time.

### Step 3: Derive intention levels

Use this hierarchy:

- **Low-level intentions**: single-action goals, such as selecting a wallet, clicking a card, changing K-line granularity, toggling Sequential Time, or annotating a view.
- **Mid-level intentions**: multi-action analytical goals, such as checking structural connectivity, relating manipulation cards to price regimes, comparing cohorts, or validating entity/funding links.
- **High-level intentions**: case-building goals, such as constructing a coordinated manipulation campaign hypothesis or explaining motive and profit-taking.

For every mid-level and high-level intention, include:

- Evidence: actions, annotations, screenshots, selected users, and relevant view states.
- Rationale: why those evidence pieces imply that intention rather than a simpler alternative.
- Confidence or caveat when needed.

### Step 4: Derive insight levels

Use this hierarchy:

- **Low-level insights**: facts visible in one view or one annotation, such as a connected cluster, a selected funded wallet, or a card window with many users.
- **Mid-level insights**: patterns across a few actions or views, such as "this card cohort appears coordinated" or "this account bridges two windows."
- **High-level insights**: aggregated narratives across the session, such as accumulation, price support, wash-like activity, profit-taking, or campaign-level collusion.

For every mid-level and high-level insight, include:

- Evidence from annotations and screenshots.
- If available, validation from local data.
- Rationale explaining how the insight follows from the evidence.
- What would falsify or weaken the insight.

### Step 5: Derive recommendation levels

Use this hierarchy:

- **Low-level recommendations**: inspect a specific view, card, annotation, account, or toggle.
- **Mid-level recommendations**: run entity/link checks, compare entity-based and non-entity detection, tabulate per-window trade flows, validate transfers and counterparties.
- **High-level recommendations**: build a case timeline, prioritize bridge accounts, verify external market-event hypotheses, create control comparisons.

For every mid-level and high-level recommendation, include:

- The recommendation.
- Rationale grounded in the trace findings.
- The expected evidence gained if the recommendation is followed.

### Step 6: Build a trace-step map

Create a separate traceability artifact after the narrative analysis. Prefer compact analytical step nodes over raw action nodes unless the user asks for micro-interaction analysis. Raw action graphs become noisy when hover, scroll, and view-state updates are logged as separate events.

Use this structure:

- **Step nodes**: observable evidence bundles such as actions, annotations, screenshots, and view states.
- **Intention nodes**: what the user appeared to be trying to do.
- **Insight nodes**: what the user explicitly captured or what the analyst inferred.
- **Recommendation nodes**: what should be done next because of the insight.

Step-node construction:

- Use 6 to 10 compact steps for a typical 15 to 30 action trace.
- Group adjacent actions when they share one analytical purpose, such as selecting a user, clicking a manipulation card, inspecting Behavior Details, and annotating the result.
- Keep action indices, annotation indices, timestamps, screenshots, selected users, clicked-card users, and relevant view states inside the step table.
- Do not hide gaps. If a state change appears without a matching logged action, say so in the step notes.
- Treat annotation records as user-authored claim evidence. Treat local data computations as analyst validation or inference.

Claim-node construction:

- Give every intention, insight, and recommendation a stable ID such as `I1`, `G1`, and `R1`.
- Label each claim with a level: low, mid, or high.
- For mid-level and high-level claims, ensure the map shows multiple supporting steps or explains why one step is sufficient.
- Keep unverified motives, such as exchange-listing explanations, as separate weak-hypothesis nodes instead of merging them into stronger trace-supported findings.
- Add confidence labels when useful: direct evidence, strong inference, weak hypothesis.

Recommendation mapping:

- Put most investigation recommendations downstream of insights, not directly downstream of actions.
- Link pure UI or trace-review recommendations directly to steps when the recommendation is to reopen a screenshot, compare a view state, or inspect an annotation.
- Make high-level recommendations depend on high-level insights that aggregate multiple steps.

## 5. Requirements For The Deliverables

The primary report should be a Markdown file unless the user requests otherwise. Prefer placing it next to the trace folder, for example:

```text
TRACE/analysis-report.md
```

For a full analysis, also create:

```text
TRACE/trace-step-map.md
```

### `analysis-report.md` required sections

- Scope and method.
- Source files used.
- Caveats and assumptions.
- System/view semantics needed to understand the trace.
- Chronological reconstruction.
- User intentions by level.
- User and analyst-inferred insights by level.
- Action recommendations by level.
- Evidence tables for important users, groups, time windows, and screenshots.
- Bottom line.

### `trace-step-map.md` required sections

- Purpose and relation to `analysis-report.md`.
- Representation choice, usually a claim-traceability graph.
- Step nodes table with step ID, evidence, what happened, and why it matters.
- Claim nodes for intentions, insights, and recommendations, each with stable IDs and levels.
- Traceability matrix mapping steps to intention IDs, insight IDs, recommendation IDs, and rationale.
- Mermaid graph linking steps to intentions, insights, and recommendations.
- How to read the graph, including the strongest reasoning paths and weak or unverified paths.
- Suggestions for future trace analysis when the map reveals trace gaps, missing data, or useful follow-up checks.

### Hard requirements

- Include analysis and rationale, not only conclusions.
- Separate observed facts from inferred claims.
- Keep screenshots linked by relative path.
- Preserve exact wallet addresses in evidence tables unless the user asks for anonymization.
- Use shortened addresses in prose for readability.
- Use concrete dates and times for market or session events.
- State trace gaps clearly, such as state changes without matching logged clicks.
- Mark external-event claims, such as exchange listing motives, as unverified unless verified with external sources.
- In `trace-step-map.md`, every graph node ID must also appear in a table.
- In `trace-step-map.md`, high-level claims must be connected to multiple supporting steps unless the rationale explains otherwise.
- In `trace-step-map.md`, graph edges should represent reasoning dependencies, not just chronological order.

## 6. Lessons Learned

- Read the manual and frontend source before interpreting screenshots. Visual marks and action names are not self-explanatory without source semantics.
- `CryptoVis.vue` is the key file for understanding how actions map to source and target views and why some screenshots exist while others do not.
- `BehaviorDetails.vue` is essential for interpreting buy/sell colors, transfer arrows, manipulation boxes, balance areas, and Sequential Time.
- `CandlestickChart.vue` is essential for understanding how manipulation cards are aggregated and why clicked card users represent cohorts.
- Annotation text is the strongest evidence of what the user believed or wanted to record.
- Action screenshots are useful, but annotation screenshots usually encode the user's actual evidence markings.
- Always distinguish user insight from analyst inference. A user annotation can be quoted or summarized as user-authored; a conclusion from local data must be labeled as validation or inference.
- Repeated users across card groups are high-value bridge evidence. Compute overlaps early.
- Direct transfers among selected or repeated users can materially strengthen coordination hypotheses. Check `sorted_transfers.csv`.
- Trade summaries by selected cohort and time window make qualitative screenshot claims more defensible. Check `sorted_trades.csv` after identifying candidate users and windows.
- Use local data to validate amounts, timings, residual balances, and repeated activity, but do not imply the user saw those exact computed summaries unless the trace shows it.
- Create contact sheets for many screenshots, but inspect important screenshots individually at original resolution.
- Include caveats for unverified motives. Trading patterns can support a manipulation hypothesis without proving why the users acted.
- For future efficiency, produce reusable tables while analyzing: action timeline, annotation timeline, image map, clicked card users, repeated users, transfer links, and per-window trade totals.
- Produce the trace-step map after the narrative report. The report helps decide what the claims are; the map helps verify whether each claim is actually grounded in trace evidence.
- Use step-level map nodes for insight analysis and reserve raw action-level graph nodes for usability analysis.
- Keep the map's recommendations downstream of insights whenever possible. This makes it clear whether a recommendation follows from evidence or is just a generic next step.
- Use graph weak points to improve the report. If a high-level insight only has one edge, either add missing evidence, lower the claim level, or mark it as a weak hypothesis.

## 7. Quality Checklist

Before delivering, verify:

- The report path is correct and `analysis-report.md` exists.
- For a full analysis, `trace-step-map.md` exists next to the report.
- Every mid-level and high-level intention has evidence and rationale.
- Every mid-level and high-level insight has evidence and rationale.
- Every mid-level and high-level recommendation has rationale.
- Key screenshots are linked and paths resolve.
- Trace gaps are called out.
- External claims are not overstated.
- The bottom line states the strongest supported conclusion and the weakest unresolved claim.
- The trace-step map has step nodes, claim nodes, a traceability matrix, and a Mermaid graph.
- Every step node includes action or annotation evidence.
- Every `I*`, `G*`, and `R*` ID used in the graph also appears in the claim-node tables.
- Mermaid syntax is simple enough to render in common Markdown viewers.
- The graph separates direct evidence, strong inferences, and weak hypotheses when confidence differs materially.

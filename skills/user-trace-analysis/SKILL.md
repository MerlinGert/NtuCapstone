---
name: user-trace-analysis
description: Use when analyzing a ManiScope exported or live user-interaction trace to reconstruct Tasks, Analytic Questions, Hypotheses, Interactions, Analytic Activities, Investigation Strategies, Findings, Insights, trace-step maps, reasoning graphs, User Reasoning Forests, Recommendation Plan Forests, follow-up investigation patches, and augmented reasoning forests.
---

# User Trace Analysis Skill

Use this skill when analyzing a ManiScope exported user-interaction trace, especially a folder containing `session.json` plus screenshot images. The goal is to reconstruct what the user was trying to do, what findings or insights they explicitly captured or implicitly discovered, what follow-up Investigation Strategies, Analytic Activities, and Interactions follow, and how those claims map back to trace steps.

For a full trace analysis, produce these artifacts unless the user asks for a lighter output:

- `TRACE/analysis-report.md`: narrative analysis with evidence, rationale, caveats, intentions, findings, insights, and recommendations.
- `TRACE/trace-step-map.md`: traceability map linking logged Interactions and annotations to intentions, findings, insights, and recommendations.
- `TRACE/reasoning-graph.json`: canonical shared-node graph for the trace. This is the source of truth for reasoning support.
- `TRACE/user-reasoning-forest.md`: readable derived forest rooted at user Hypotheses.
- `TRACE/user-reasoning-forest.json`: machine-readable derived forest when using the transformer script.

For the canonical graph schema, relation taxonomy, salience field, and forest transformation rules, read `references/reasoning-graph-format.md`. Use `scripts/reasoning_graph_to_forest.py` to mechanically derive `user-reasoning-forest.json` and `user-reasoning-forest.md` from `reasoning-graph.json`.

When the task includes recommendations or follow-up investigation, also read:

- `references/recommendation-plan-format.md`: Recommendation Plan Graph and Recommendation Plan Forest schema.
- `references/reasoning-graph-patch-format.md`: patch format for adding agent follow-up evidence back into the canonical reasoning graph.
- `references/follow-up-investigation-execution.md`: practical workflow for executing Recommendation Plan Forests with local data, backend endpoints, rendered ManiScope views, evidence images, and follow-up reports.

Use `scripts/recommendation_plan_to_forest.py` to mechanically derive `recommendation-plan-forest.json` and `recommendation-plan-forest.md` from `recommendation-plan-graph.json`.
Use `scripts/apply_reasoning_graph_patch.py` to apply a follow-up evidence patch to `reasoning-graph.json`, producing `augmented-reasoning-graph.json` and regenerated `augmented-reasoning-forest.md`.

## 1. Clarify The Task When Needed

Ask concise questions before deep analysis if the request leaves an important choice ambiguous. Useful clarification questions include:

- What level of evidence should the report use: only the interaction trace, or also local ACT/PNUT source data for validation?
- Should inferred findings be conservative, speculative, or hypothesis-generating?
- Should the output be a short summary, a structured Markdown report, a table-first evidence memo, or a presentation-ready narrative?
- Who is the audience: system designer, crypto investigator, research evaluator, or user-study analyst?
- Should the analysis focus on user cognition and workflow, market/manipulation findings, or both?
- Should screenshots be treated as primary evidence, or only as supporting context for `session.json`?
- Do you want exact wallet addresses preserved, shortened, anonymized, or grouped by role?
- Should the step map use compact analytical steps, raw Interaction-level nodes, or both?
- Should the step map include a Mermaid graph, a matrix only, or a graph plus matrix?
- Should confidence labels be included for intentions, insights, and recommendations?
- Should external web evidence be used to verify market events such as listings, announcements, or news? If yes, browse and cite sources.
- Are there known ground-truth events, labels, or hypotheses that should be checked against the trace?
- Should the output include recommendations for product/UI improvement, investigation next steps, or both?
- Should recommendations be organized as a top-down investigation plan with Investigation Strategies, Analytic Activities, and Interactions?
- Should Interactions use the default Data, Model, Visualization, and Synthesis taxonomy?

If the user specifies the trace path and asks for an analysis, proceed without blocking unless one of these choices materially changes the expected output.

## 2. Inputs To Gather

Start by understanding both the system and the trace. Do not infer view meaning from screenshots alone.

### Required trace files

- `session.json`: metadata, logged Interactions, annotation records, view states, selected users, clicked card users, snapshot categories, and image paths.
- `images/`: Interaction screenshots and annotation screenshots.

Key `session.json` fields:

- `coin`, `exportedAt`, `exportFormat`, `includesSnapshots`, `imageCount`.
- `userActionSequence[]`: `timestamp`, `actionType`, `sourceView`, `targetView`, `userId`, `actionInfo`, `relatedViewWithViewState`, `sourceSnapshot`, `targetSnapshot`.
- `annotationRecords[]`: `id`, `timestamp`, `sourceView`, `text`, `selectedItems`, `sketchImagePath`, `isInsight`.
- `config.snapshotCategories`: tells which logged `actionType` values have screenshots and which may be missing screenshots by design.

### Required documentation

- `docs/reports/user-manual.en.md`: current workflow, view meanings, visual encodings, controls, and expected analysis flow.

Use the manual to interpret:

- Token Distribution graph, entity groups, links, suspicious node styling.
- K-line manipulation cards, round-trip versus same-direction placement.
- Behavior Details chart encodings, sequential time, related users, manipulation boxes.
- User Actions view, Annotations view, and Action Tree semantics.

### Useful frontend source

Read these files when interpreting a trace:

- `front/src/components/CryptoVis.vue`: layout, Interaction logging, source/target view inference, snapshot capture, export/import state, selected users, card clicks, coin/snapshot/detection handlers.
- `front/src/components/ControlPanel.vue`: snapshot, entity, link, and manipulation configuration controls.
- `front/src/components/TokenDistribution.vue`: graph semantics, suspicious node logic, links, entity boundaries, hover/select logging.
- `front/src/components/CandlestickChart.vue`: granularity options, manipulation-card aggregation, card click users, hover/scroll logging, K-line screenshot capture.
- `front/src/components/BehaviorDetails.vue`: behavior timeline encodings, buy/sell colors, transfers, balance/earning areas, manipulation boxes, sequential time, related users, label clicks.
- `front/src/components/UserActionTimeline.vue`: logged Interaction display names and capture category behavior.
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

## 3. Core Terminology

Use terminology grounded in the visual analytics knowledge-generation workflow. Avoid using generic recommendation terms such as "atomic action" when a precise term applies.

### Three Analysis Spaces

Classify trace interpretation into three spaces:

| Scope | Intention Space | Action Space | Finding Space |
|---|---|---|---|
| Low | **Task** | **Interaction** | **Finding** |
| Mid | **Analytic Question** | **Analytic Activity** | **Finding** |
| High | **Hypothesis** | **Investigation Strategy** | **Insight** |

Definitions:

- **Task**: a concrete local goal, such as selecting a wallet, checking one card window, or finding one metric.
- **Analytic Question**: a bounded question requiring several related Interactions, such as whether a cohort behaved together or whether a detector grouping is stable.
- **Hypothesis**: a high-level explanatory claim to test, such as whether a wallet group coordinated to manipulate price.
- **Interaction**: one executable operation performed by a human, agent, script, or system command.
- **Analytic Activity**: a short sequence of related Interactions serving one Analytic Question.
- **Investigation Strategy**: a high-level plan for testing a Hypothesis through multiple Analytic Activities.
- **Finding**: a local or mid-level result from observation, GUI-displayed evidence, model output, or computation.
- **Insight**: a synthesized high-level understanding that connects multiple Findings and changes the analyst's understanding of the case.

Do not use **Knowledge** for normal trace reports unless the claim has been validated beyond the trace and local exploratory analysis. Most ManiScope reports should stop at Findings and Insights.

### Action Space Types

Type low-level Interactions with one primary type:

- **Data Action**: query, filter, retrieve, aggregate, or compute from data or model outputs. This includes statistics not displayed in the GUI.
- **Model Action**: change detector parameters, rerun detection, change grouping rules, choose model settings, or otherwise alter model outputs.
- **Visualization Action**: inspect, navigate, select, zoom, compare, change display settings, read GUI-displayed statistics, or interpret trace screenshots and ManiScope views.
- **Synthesis Action**: annotate, summarize, connect Findings, update a Hypothesis, write a report note, or create a traceability link.

Type mid-level Analytic Activities with one of two labels:

- **Visual Analysis**: contains one or more Visualization Actions, and the Finding depends on visual inspection, screenshots, GUI-displayed evidence, or visual comparison.
- **Statistical Analysis**: contains no Visualization Actions; the Finding comes from data, model outputs, computation, scripts, command-line queries, or notebooks.

Model Actions and Synthesis Actions do not determine the Analytic Activity type by themselves. Classify the activity by whether Visualization Actions are necessary for the Finding.

If a candidate Analytic Activity mixes visual inspection and script-side calculation, split it into a Visual Analysis activity and a Statistical Analysis activity. For example:

- Visual Analysis: change detector threshold, rerun grouping, and inspect whether the same wallets remain visually grouped.
- Statistical Analysis: compute group overlap between detector outputs without inspecting the visualization.

High-level Investigation Strategies do not need an action type. Organize them by Hypothesis, why the strategy matters, target outcome, and the Analytic Activities needed.

### Mapping Rule

Map the spaces with these reasoning edges:

```text
Intention motivates Action Space unit
Action Space unit produces Finding Space output
Finding Space output supports, refines, or contradicts Intention
```

Use same-scope mappings when possible:

- Task -> Interaction -> Finding.
- Analytic Question -> Analytic Activity -> Finding.
- Hypothesis -> Investigation Strategy -> Insight.

Lower-scope rows should support higher-scope rows. Multiple low-level Findings can support a mid-level Finding, and multiple Findings can support or weaken a high-level Insight.

### Evidence Route

Use **Evidence Route** only as a lightweight property, not as another hierarchy. It explains how an Interaction or Analytic Activity produces evidence.

Examples:

- `data -> finding`: compute mean token price.
- `model -> visualization -> finding`: change detector config, inspect grouping, record visual stability.
- `model output -> data -> finding`: compute overlap between old and new groups.
- `findings -> insight`: synthesize timing, roles, and price impact into a coordination Insight.

### Reasoning Graph and Forest Terms

Use these terms when building traceability outputs:

- **Reasoning Support Graph**: the canonical directed graph with shared nodes. Nodes are Interactions, Tasks, Analytic Questions, Analytic Activities, Findings, Insights, Hypotheses, and Investigation Strategies. Edges encode reasoning relations.
- **User Reasoning Forest**: a derived readable tree view of the Reasoning Support Graph. Each tree is rooted at one user-authored or analyst-inferred Hypothesis.
- **Canonical Node**: the original graph node, such as `F7`.
- **Tree Node Instance**: a duplicated tree node that points back to a canonical node, such as `F7@H1.2`.
- **Shared Node**: a canonical node with more than one parent in the support projection.
- **Reasoning Gap**: a missing, weak, contradictory, or under-supported path below an existing Finding, Insight, or Hypothesis.
- **Evidence Completion Recommendation**: an Investigation Strategy that fills a Reasoning Gap in an existing User Reasoning Forest.
- **Hypothesis Expansion Recommendation**: an Investigation Strategy that proposes a related new Hypothesis and grows a new tree or branch.
- **Recommendation Plan Graph**: a prescriptive graph of Reasoning Gaps, Expansion Rationales, Investigation Strategies, Analytic Activities, Recommended Interactions, and Expected Findings.
- **Recommendation Plan Forest**: a readable prescriptive tree view generated from the Recommendation Plan Graph.
- **Expected Finding**: a planned target outcome, not evidence. Convert it to a real Finding only after follow-up investigation produces evidence.
- **Follow-up Investigation Forest**: a descriptive forest for evidence produced by executing a Recommendation Plan Forest.
- **Reasoning Graph Patch**: a machine-readable set of additions or updates that merges follow-up evidence into the canonical Reasoning Support Graph.
- **Augmented Reasoning Forest**: the regenerated reasoning forest after applying one or more Reasoning Graph Patches.

Use this relation taxonomy in `reasoning-graph.json`:

| Relation | Direction | Meaning |
|---|---|---|
| `motivates` | Intention -> Action Space unit | A Task, Analytic Question, or Hypothesis explains why an Interaction, Analytic Activity, or Investigation Strategy happened. |
| `produces` | Action Space unit -> Finding Space output | An Interaction, Analytic Activity, or Investigation Strategy generated a Finding or Insight. |
| `supports` | Finding Space output -> Finding Space output or Intention | A Finding or Insight strengthens another Finding, an Insight, a Task interpretation, an Analytic Question, or a Hypothesis. |
| `refines` | Finding Space output -> Intention | A Finding or Insight changes or narrows the intention. |
| `contradicts` | Finding Space output -> Intention | A Finding or Insight weakens or falsifies the intention. |
| `contains` | Higher-level unit -> lower-level unit | A Hypothesis contains Analytic Questions, an Analytic Activity contains Interactions, or another hierarchical containment relation is useful. |
| `derived_from` | Analyst-inferred node -> evidence node | A node was inferred from raw trace evidence, screenshots, annotations, local data, or rendered visual evidence. |

Every Interaction node in `reasoning-graph.json` should include `salience`:

- `primary`: directly supports a major Finding, Insight, or Hypothesis.
- `supporting`: provides context or strengthens a reasoning path.
- `low`: logged but weakly relevant, such as incidental hover, scroll, or layout navigation.

The User Reasoning Forest must use raw Interaction leaves by default. Do not replace Interactions with compact Step nodes in the forest unless the user explicitly asks for a compact view.

### Recommendation and Follow-up Lifecycle

Keep the epistemic boundary clear:

- **User Reasoning Forest** is descriptive and reconstructs what the user trace supports.
- **Recommendation Plan Forest** is prescriptive and describes what should be investigated next.
- **Follow-up Investigation Forest** is descriptive and records what an agent found after executing the plan.
- **Augmented Reasoning Forest** is the original reasoning graph plus follow-up evidence, regenerated mechanically.

Recommended lifecycle:

```text
reasoning-graph.json
  -> user-reasoning-forest.md
  -> recommendation-plan-graph.json
  -> recommendation-plan-forest.md
  -> agent executes recommended Interactions
  -> reasoning-graph-patch-001.json
  -> augmented-reasoning-graph.json
  -> augmented-reasoning-forest.md
```

For **Evidence Completion Recommendations**, attach the plan to an existing Reasoning Gap. After execution, create real Interaction, Finding, or Insight nodes with `actor: "agent"` and `source: "followup_investigation"`, then patch them into the original graph with `supports`, `refines`, or `contradicts` edges to the original target node.

For **Hypothesis Expansion Recommendations**, the plan may propose a new Hypothesis. After execution, create a follow-up reasoning graph or graph patch with the new Hypothesis as a root, then generate both a focused Follow-up Investigation Forest and, when useful, an Augmented Reasoning Forest that includes the new root.

Do not treat Expected Findings from a Recommendation Plan Forest as real Findings. Expected Findings become Findings only after evidence is produced by follow-up investigation.

## 4. Efficient Inspection Commands

Use `rg` and `jq` first. Adjust paths as needed.

Basic trace summary:

```bash
jq '{coin, exportedAt, exportFormat, includesSnapshots, imageCount, actionCount:(.userActionSequence|length), annotationCount:(.annotationRecords|length), config:.config}' TRACE/session.json
```

Interaction timeline:

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

## 5. Analysis Workflow

### Step 1: Build a factual timeline

Create a chronological reconstruction with:

- Interaction index and timestamp.
- Source view and target view.
- Logged `actionType` and important `actionInfo`.
- Selected user or selected card users.
- Current view state: `selectedUser`, `selectedCardUsers`, `klineTimeWindow`, `behaviorTimeWindow`, `snapshotTime`.
- Available Interaction screenshots.
- Nearby annotation records.

Distinguish:

- Logged Interactions: clicks, toggles, hovers, scrolls, granularity changes, annotations, script runs, or other executable operations.
- Derived state: selected users or time windows visible in `relatedViewWithViewState`.
- User-authored Findings or Insights: annotation text.
- Analyst inferences: conclusions derived from several Interactions or from local data validation.

### Step 2: Interpret screenshots with view semantics

Use annotation screenshots as primary evidence for what the user considered meaningful. Use Interaction screenshots for context and before/after verification.

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

### Step 3: Classify the Intention Space

Use this hierarchy:

- **Tasks**: concrete local goals, such as selecting a wallet, clicking a card, changing K-line granularity, toggling Sequential Time, annotating a view, or computing one metric.
- **Analytic Questions**: bounded multi-Interaction goals, such as checking structural connectivity, relating manipulation cards to price regimes, comparing cohorts, or validating entity/funding links.
- **Hypotheses**: case-building goals, such as testing whether a group coordinated a manipulation campaign or whether profit-taking followed price support.

For every Analytic Question and Hypothesis, include:

- Evidence: Interactions, annotations, screenshots, selected users, and relevant view states.
- Rationale: why those evidence pieces imply that intention rather than a simpler alternative.
- Confidence or caveat when needed.

### Step 4: Classify the Finding Space

Use this hierarchy:

- **Low-level Findings**: facts visible in one view, one annotation, one model output, or one computation, such as a connected cluster, a selected funded wallet, a card window with many users, or a computed mean price.
- **Mid-level Findings**: bounded patterns across a few Interactions, Analytic Activities, or views, such as "this card cohort appears coordinated" or "this account bridges two windows."
- **High-level Insights**: aggregated narratives across the session, such as accumulation, price support, wash-like activity, profit-taking, or campaign-level collusion.

For every mid-level Finding and high-level Insight, include:

- Evidence from annotations and screenshots.
- If available, validation from local data.
- Rationale explaining how the Finding or Insight follows from the evidence.
- What would falsify or weaken the Finding or Insight.

### Step 5: Build a top-down recommendation plan

Recommendations should be organized as Investigation Strategies, not as a flat low/mid/high list or as generic next steps.

Before writing strategies, classify the opportunity space into three recommendation classes:

- **Continue the user's path**: complete, validate, or falsify the investigation the user was already pursuing. These strategies strengthen or weaken the current case by checking role timelines, manipulation windows, component membership, price impact, and false-positive alternatives.
- **Similar new explorations**: ask what else resembles the user's trace. Derive a signature from the user's path, such as a wallet role, card cohort, time-window pattern, component shape, or transfer behavior, then search local data and screenshots for analogous groups, wallets, or windows.
- **Hindsight opportunities**: identify important leads the user missed. These may be downstream sinks, post-window exits, sell-side behavior, peripheral wallets, weakly visible component members, threshold-sensitive model outputs, or market-wide statistics that were not visible in the trace. Treat these as exploration hypotheses until validated.

When local data validation is allowed, use it to seed Similar new explorations and Hindsight opportunities. Keep the provenance clear: trace-observed leads are what the user actually saw; local data leads are analyst-discovered follow-up opportunities.

Use this structure:

- **Investigation Strategy**: the high-level plan for testing a Hypothesis, such as building a case timeline, validating price impact, expanding a suspected component, or avoiding false positives.
- **Recommendation class**: Continue the user's path, Similar new exploration, or Hindsight opportunity.
- **Why this matters**: concise rationale grounded in trace Findings and Insights.
- **Target outcome**: the concrete artifact or evidence state the investigation should produce.
- **Analytic Activities**: coherent mid-level analysis units under the Investigation Strategy, such as confirming core wallet roles, validating card windows, testing entity relationships, or classifying shared hubs.
- **Interactions**: specific executable operations inside each Analytic Activity.

For each Interaction, assign one primary type:

- **Data Action**: query, filter, aggregate, or compute from data or model outputs.
- **Model Action**: change detector parameters, rerun detection, or alter model/grouping outputs.
- **Visualization Action**: inspect ManiScope GUI components or trace screenshots, including values or statistics displayed by the GUI.
- **Synthesis Action**: annotate, summarize, connect Findings, update a Hypothesis, or write a report note.

For each Analytic Activity, assign one activity type:

- **Visual Analysis**: contains one or more Visualization Actions, and its Finding depends on visual inspection or GUI-displayed evidence.
- **Statistical Analysis**: contains no Visualization Actions, and its Finding comes from data, model outputs, scripts, or custom computation.

Example Interactions and Analytic Activities:

- Interaction, Visualization Action: "Open Behavior Details for wallet X and inspect transfer arrows, manipulation boxes, and balance trend."
- Interaction, Visualization Action: "Reopen the K-line screenshot and transcribe the clicked card's displayed time span and amount."
- Interaction, Data Action: "Calculate buy count, sell count, buy USD, sell USD, token inflow, token outflow, first action time, and final balance for wallet X."
- Interaction, Data Action: "Compute the cohort's share of market trade volume during the card window."
- Interaction, Model Action: "Change the detector grouping threshold and rerun detection."
- Interaction, Synthesis Action: "Record whether the new detector output supports or weakens the coordination Hypothesis."
- Analytic Activity, Visual Analysis: "Test detector robustness by changing parameters and visually comparing whether the same wallets remain grouped."
- Analytic Activity, Statistical Analysis: "Quantify detector robustness by computing overlap between old and new grouping outputs."

Use scope labels inside the plan, but do not let levels become the organizing structure. The Hypothesis should explain the "why"; Investigation Strategies should explain the plan; Analytic Activities should organize the work; Interactions should explain what to do next.

Recommended Investigation Strategy patterns:

- **Build a role-based case timeline**: when the trace suggests different wallet roles such as passive whale, bridge actor, functional buyer, storage sink, accumulator, or round-trip-like actor.
- **Validate manipulation windows and price impact**: when the trace links behavior details or manipulation cards to K-line movement.
- **Expand a suspected component without overgeneralizing**: when the trace suggests a larger community or entity, but raw transfer or behavior validation is still needed.
- **Search for sibling windows or cohorts**: when the user investigated one manipulation card, time window, or card-user group and local data or nearby screenshots may reveal similar unclicked candidates.
- **Search for role analogues**: when the user assigned roles to wallets and local data can find other wallets with similar trade, transfer, balance, or earning profiles.
- **Follow overlooked downstream sinks or upstream funders**: when the trace shows a functional wallet, transfer arrows, or outgoing inventory movement that the user did not follow.
- **Test post-window exits and profit-taking**: when the user focused on accumulation or price support but did not investigate later selling, transfers, or realized earnings.
- **Verify external motive only after on-chain evidence is stable**: when the trace suggests a motive but does not prove it.

For each Investigation Strategy, include:

- Strategy ID, such as `S1`.
- Recommendation class.
- Target Hypothesis or Analytic Question.
- Why this matters.
- Target outcome.
- One or more Analytic Activity IDs, such as `AA1`.
- A table of Interactions with columns `Interaction ID`, `Interaction Type`, `Evidence Route`, and `Expected Output`.
- Optional priority ordering for the most important Interactions or Analytic Activities.

Preserve recommendation confidence and caveats. If an Investigation Strategy or Interaction is based on a weak Hypothesis, state what would confirm or weaken it.

For crypto-investigator reports, do not limit recommendations to product or workflow improvements. Prefer executable investigation leads: wallets to open, components to recompute, windows to quantify, transfer chains to follow, and hypotheses to falsify.

### Step 6: Build a trace-step map

Create a separate traceability artifact after the narrative analysis. The trace-step map may use compact analytical step nodes for readability, but the canonical `reasoning-graph.json` and derived User Reasoning Forest should preserve raw Interaction nodes as leaves.

Use this structure:

- **Step nodes**: observable evidence bundles such as logged Interactions, annotations, screenshots, and view states.
- **Intention nodes**: Tasks, Analytic Questions, and Hypotheses.
- **Finding-space nodes**: Findings and Insights.
- **Recommendation nodes**: Investigation Strategies, Analytic Activities, or important Interactions that follow from Findings and Insights.

Step-node construction:

- Use 6 to 10 compact steps for a typical 15 to 30 Interaction trace.
- Group adjacent logged Interactions when they share one analytical purpose, such as selecting a user, clicking a manipulation card, inspecting Behavior Details, and annotating the result.
- Keep Interaction indices, annotation indices, timestamps, screenshots, selected users, clicked-card users, and relevant view states inside the step table.
- Do not hide gaps. If a state change appears without a matching logged Interaction, say so in the step notes.
- Treat annotation records as user-authored claim evidence. Treat local data computations as analyst validation or inference.

Claim-node construction:

- Give every Task, Analytic Question, Hypothesis, Finding, Insight, Investigation Strategy, Analytic Activity, and mapped Interaction a stable ID.
- Label each claim with both space and scope, such as `Task`, `Analytic Question`, `Hypothesis`, `Finding`, or `Insight`.
- For Analytic Questions, Hypotheses, mid-level Findings, and Insights, ensure the map shows multiple supporting steps or explains why one step is sufficient.
- Keep unverified motives, such as exchange-listing explanations, as separate weak-hypothesis nodes instead of merging them into stronger trace-supported findings.
- Add confidence labels when useful: direct evidence, strong inference, weak hypothesis.

Recommendation mapping:

- Put most Investigation Strategies downstream of Insights, not directly downstream of logged Interactions.
- Link pure UI or trace-review Interactions directly to steps when the recommendation is to reopen a screenshot, compare a view state, or inspect an annotation.
- Make Investigation Strategies depend on Insights that aggregate multiple Findings.
- If the full report contains many Interactions, map only the Investigation Strategies and the most important Analytic Activities unless the user asks for an Interaction-level graph.

After building `trace-step-map.md`, produce `reasoning-graph.json` using the schema in `references/reasoning-graph-format.md`. Then run:

```bash
python skills/user-trace-analysis/scripts/reasoning_graph_to_forest.py TRACE/reasoning-graph.json
```

The generated `user-reasoning-forest.md` should show one bottom-up reasoning support tree per Hypothesis. Duplicate shared canonical nodes mechanically so each tree node instance has at most one parent.

### Step 7: Build a Recommendation Plan Forest when recommendations are requested

Create `recommendation-plan-graph.json` and `recommendation-plan-forest.md` when the user asks for recommendations, next steps, autonomous investigation plans, or evidence-gap analysis.

Use two recommendation types:

- **Evidence Completion**: fills a Reasoning Gap inside an existing User Reasoning Forest.
- **Hypothesis Expansion**: proposes a new related Hypothesis from an existing Finding, Insight, or Hypothesis.

Use the format in `references/recommendation-plan-format.md`. Recommendation Plan Forest nodes are plans, not evidence. Keep Expected Findings visually and semantically separate from actual Findings.

Then run:

```bash
python skills/user-trace-analysis/scripts/recommendation_plan_to_forest.py \
  TRACE/recommendation-plan-graph.json
```

### Step 8: Patch the reasoning graph after follow-up investigation

When an agent executes a Recommendation Plan Forest, record the new evidence as a Reasoning Graph Patch instead of editing the old forest by hand.

Before executing follow-up work, read `references/follow-up-investigation-execution.md` for local service checks, render API usage, raw-data validation, image asset hygiene, and report conventions.

Patch flow:

```bash
python skills/user-trace-analysis/scripts/apply_reasoning_graph_patch.py \
  TRACE/reasoning-graph.json \
  TRACE/reasoning-graph-patch-001.json
```

The patch script writes `augmented-reasoning-graph.json`, `augmented-reasoning-forest.json`, and `augmented-reasoning-forest.md` by default. Use the patch format in `references/reasoning-graph-patch-format.md`.

## 6. Requirements For The Deliverables

The primary report should be a Markdown file unless the user requests otherwise. Prefer placing it next to the trace folder, for example:

```text
TRACE/analysis-report.md
```

For a full analysis, also create:

```text
TRACE/trace-step-map.md
TRACE/reasoning-graph.json
TRACE/user-reasoning-forest.md
```

For recommendation or follow-up work, also create the relevant artifacts:

```text
TRACE/recommendation-plan-graph.json
TRACE/recommendation-plan-forest.md
TRACE/reasoning-graph-patch-001.json
TRACE/augmented-reasoning-graph.json
TRACE/augmented-reasoning-forest.md
```

### `analysis-report.md` required sections

- Scope and method.
- Source files used.
- Caveats and assumptions.
- System/view semantics needed to understand the trace.
- Chronological reconstruction.
- Intention Space analysis: Tasks, Analytic Questions, and Hypotheses.
- Finding Space analysis: user-authored and analyst-inferred Findings and Insights.
- Top-down recommendations using Investigation Strategies, Analytic Activities, and Interactions. Cover Continue the user's path, Similar new explorations, and Hindsight opportunities when the report includes action recommendations. Analytic Activities must be typed as `Visual Analysis` or `Statistical Analysis`; Interactions must be typed as `Data Action`, `Model Action`, `Visualization Action`, or `Synthesis Action`.
- Evidence tables for important users, groups, time windows, and screenshots.
- Bottom line.

### `trace-step-map.md` required sections

- Purpose and relation to `analysis-report.md`.
- Representation choice, usually a claim-traceability graph.
- Step nodes table with step ID, evidence, what happened, and why it matters.
- Claim nodes for Tasks, Analytic Questions, Hypotheses, Findings, Insights, and mapped recommendations, each with stable IDs and scope labels.
- Traceability matrix mapping steps to intention-space IDs, finding-space IDs, recommendation IDs, and rationale.
- Mermaid graph linking steps to intention-space nodes, finding-space nodes, and recommendation nodes.
- How to read the graph, including the strongest reasoning paths and weak or unverified paths.
- Suggestions for future trace analysis when the map reveals trace gaps, missing data, or useful follow-up checks.

### `reasoning-graph.json` required content

- `version`, `trace`, `nodes`, `edges`, and `roots`.
- One canonical node for every Interaction, Task, Analytic Question, Analytic Activity, Finding, Insight, Hypothesis, and Investigation Strategy used in the trace-step map.
- Relation types limited to `motivates`, `produces`, `supports`, `refines`, `contradicts`, `contains`, and `derived_from`.
- Every Interaction node must include `interactionType` and `salience`.
- Every Analytic Activity node must include `activityType`.
- Every node should include provenance such as action indices, annotation indices, screenshots, local data checks, or rendered visual evidence.

### `user-reasoning-forest.md` required sections

- Purpose and relation to `reasoning-graph.json`.
- Forest construction rule: one tree per Hypothesis root, with shared canonical nodes duplicated into separate tree node instances.
- A node table with tree instance ID, canonical node ID, kind, scope, salience where relevant, confidence, and label.
- A Mermaid `flowchart BT` tree for each Hypothesis.
- A short reading guide explaining the strongest support paths, weak support paths, contradictions, and Reasoning Gaps.

### Recommendation and follow-up artifacts

- `recommendation-plan-graph.json`: prescriptive plan graph. It must distinguish Evidence Completion from Hypothesis Expansion.
- `recommendation-plan-forest.md`: readable plan forest. It must show Reasoning Gaps or Expansion Rationales above Investigation Strategies, Analytic Activities, Recommended Interactions, and Expected Findings.
- `reasoning-graph-patch-*.json`: follow-up evidence patch. New evidence nodes must include `actor`, `source`, and `planRef`.
- `augmented-reasoning-graph.json`: canonical reasoning graph after patch application.
- `augmented-reasoning-forest.md`: regenerated forest from the augmented graph. It may include both original user evidence and agent follow-up evidence.

### Hard requirements

- Include analysis and rationale, not only conclusions.
- Separate observed facts from inferred claims.
- Keep screenshots linked by relative path.
- When render APIs generate visualization evidence used for a Finding, Insight, Hypothesis, recommendation, or reasoning-graph patch, save the rendered PNG in a trace-local assets folder and cite it with `render:<relative-path>` provenance. Do not rely on transient data URLs as evidence.
- Preserve exact wallet addresses in evidence tables unless the user asks for anonymization.
- Use shortened addresses in prose for readability.
- Use concrete dates and times for market or session events.
- State trace gaps clearly, such as state changes without matching logged clicks.
- Mark external-event claims, such as exchange listing motives, as unverified unless verified with external sources.
- Organize recommendations top-down, starting from the high-level Hypothesis or Analytic Question and ending with executable Interactions.
- For action recommendations, cover the three recommendation classes unless the user asks for a narrower scope: Continue the user's path, Similar new explorations, and Hindsight opportunities.
- Every recommended Interaction must be labeled as `Data Action`, `Model Action`, `Visualization Action`, or `Synthesis Action`.
- Treat checking statistics already displayed in ManiScope as a `Visualization Action`.
- Treat statistics that require scripts, command-line queries, notebooks, or custom calculations as `Data Action`.
- Every recommended Analytic Activity must be labeled as `Visual Analysis` or `Statistical Analysis`.
- Classify an Analytic Activity as `Visual Analysis` when a Visualization Action is necessary for its Finding.
- Classify an Analytic Activity as `Statistical Analysis` when no Visualization Action is necessary for its Finding.
- For every Investigation Strategy, include a target outcome and at least one Analytic Activity.
- In `trace-step-map.md`, every graph node ID must also appear in a table.
- In `trace-step-map.md`, high-level claims must be connected to multiple supporting steps unless the rationale explains otherwise.
- In `trace-step-map.md`, graph edges should represent reasoning dependencies, not just chronological order.
- `reasoning-graph.json` must validate with `scripts/reasoning_graph_to_forest.py`.
- Every Interaction node in `reasoning-graph.json` must have `salience`.
- Every `user-reasoning-forest.md` tree must be rooted at one Hypothesis.
- The User Reasoning Forest must preserve raw Interaction leaves by default.
- Shared canonical nodes should be duplicated mechanically in the forest and retain `canonicalId`.
- Recommendation Plan Forests must not present Expected Findings as evidence-backed Findings.
- Follow-up evidence should be merged through `reasoning-graph-patch-*.json`, not by manually editing generated forests.
- Agent-added follow-up nodes must include `actor`, `source`, and `planRef`.

## 7. Lessons Learned

- Read the manual and frontend source before interpreting screenshots. Visual marks and logged Interaction names are not self-explanatory without source semantics.
- `CryptoVis.vue` is the key file for understanding how logged Interactions map to source and target views and why some screenshots exist while others do not.
- `BehaviorDetails.vue` is essential for interpreting buy/sell colors, transfer arrows, manipulation boxes, balance areas, and Sequential Time.
- `CandlestickChart.vue` is essential for understanding how manipulation cards are aggregated and why clicked card users represent cohorts.
- Annotation text is the strongest evidence of what the user believed or wanted to record.
- Interaction screenshots are useful, but annotation screenshots usually encode the user's actual evidence markings.
- Always distinguish user insight from analyst inference. A user annotation can be quoted or summarized as user-authored; a conclusion from local data must be labeled as validation or inference.
- Repeated users across card groups are high-value bridge evidence. Compute overlaps early.
- Direct transfers among selected or repeated users can materially strengthen coordination hypotheses. Check `sorted_transfers.csv`.
- Trade summaries by selected cohort and time window make qualitative screenshot claims more defensible. Check `sorted_trades.csv` after identifying candidate users and windows.
- Use local data to validate amounts, timings, residual balances, and repeated activity, but do not imply the user saw those exact computed summaries unless the trace shows it.
- Use local data to seed new opportunity recommendations when allowed. Good leads include analogous card windows, role-similar wallets, downstream sinks, upstream funders, post-window exits, and market-wide volume-share checks.
- Create contact sheets for many screenshots, but inspect important screenshots individually at original resolution.
- Include caveats for unverified motives. Trading patterns can support a manipulation hypothesis without proving why the users acted.
- For future efficiency, produce reusable tables while analyzing: Interaction timeline, annotation timeline, image map, clicked card users, repeated users, transfer links, and per-window trade totals.
- Produce the trace-step map after the narrative report. The report helps decide what the claims are; the map helps verify whether each claim is actually grounded in trace evidence.
- Use step-level map nodes for Finding and Insight analysis and reserve raw Interaction-level graph nodes for usability analysis.
- Keep Investigation Strategies downstream of Insights whenever possible. This makes it clear whether a recommendation follows from evidence or is just a generic next step.
- Use graph weak points to improve the report. If a high-level insight only has one edge, either add missing evidence, lower the claim level, or mark it as a weak hypothesis.
- Make recommendation sections read like an investigation plan, not a flat checklist: Hypothesis, Investigation Strategy, target outcome, Analytic Activities, then Interactions.
- Keep Expected Findings out of the evidence-backed reasoning graph until follow-up work actually produces evidence.
- Use Reasoning Graph Patches to merge follow-up investigation evidence. This keeps the original user trace reasoning auditable.
- Separate Visual Analysis from Statistical Analysis. This helps users decide whether the next step is a visual investigation in ManiScope or a script-side analysis outside the GUI.

## 8. Quality Checklist

Before delivering, verify:

- The report path is correct and `analysis-report.md` exists.
- For a full analysis, `trace-step-map.md` exists next to the report.
- Every Analytic Question and Hypothesis has evidence and rationale.
- Every mid-level Finding and high-level Insight has evidence and rationale.
- Every Investigation Strategy has a "why this matters" rationale.
- Action recommendations cover Continue the user's path, Similar new explorations, and Hindsight opportunities, or clearly explain why one class is out of scope.
- Every Investigation Strategy has a target outcome.
- Every Investigation Strategy contains at least one Analytic Activity.
- Every recommended Analytic Activity is labeled `Visual Analysis` or `Statistical Analysis`.
- Every recommended Interaction is labeled `Data Action`, `Model Action`, `Visualization Action`, or `Synthesis Action`.
- GUI-displayed statistics are classified under a `Visualization Action`, not a `Data Action`.
- Scripted or custom data calculations are classified as `Data Action`.
- Key screenshots are linked and paths resolve.
- Trace gaps are called out.
- External claims are not overstated.
- The bottom line states the strongest supported conclusion and the weakest unresolved claim.
- The trace-step map has step nodes, claim nodes, a traceability matrix, and a Mermaid graph.
- `reasoning-graph.json` validates with `scripts/reasoning_graph_to_forest.py`.
- `user-reasoning-forest.md` is generated from `reasoning-graph.json`, not manually edited.
- Recommendation plans distinguish Evidence Completion from Hypothesis Expansion.
- Expected Findings are labeled as expected-only plan targets, not evidence.
- Follow-up evidence patches validate with `scripts/apply_reasoning_graph_patch.py` when present.
- Augmented forests are regenerated from patched graphs, not manually edited.
- Every step node includes logged Interaction or annotation evidence.
- Every ID used in the graph also appears in the claim-node tables.
- Mermaid syntax is simple enough to render in common Markdown viewers.
- The graph separates direct evidence, strong inferences, and weak hypotheses when confidence differs materially.

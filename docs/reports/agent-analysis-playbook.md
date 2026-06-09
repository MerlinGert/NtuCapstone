# ManiScope Agent Analysis Playbook

This playbook is the session-local methodology reference for specialized ManiScope Codex agents. Read it before doing full trace analysis, incremental analysis, recommendation planning, autonomous investigation, or patch-producing subagent work.

## Analysis Spaces

Use three mapped spaces:

- Intention Space: `Task`, `AnalyticQuestion`, `Hypothesis`.
- Action Space: `Interaction`, `AnalyticActivity`, `InvestigationStrategy`.
- Finding Space: `Finding`.

Use these mappings:

- A `Task` motivates one or more `Interaction` nodes and produces a local `Finding`.
- An `AnalyticQuestion` motivates an `AnalyticActivity` and should be explicitly answered by one or more `Finding` nodes when trace or follow-up evidence supports an answer.
- A `Hypothesis` motivates an `InvestigationStrategy` and produces or revises a `Finding`.
- State evidence and rationale when inferring an `AnalyticQuestion`, `Hypothesis`, or mid- or high-level `Finding`.

Finding levels:

- Low-level Findings are concrete observations from one Interaction or one narrow AnalyticActivity.
- Mid-level Findings synthesize low-level Findings and answer AnalyticQuestions.
- High-level Findings synthesize several mid-level Findings before supporting, refining, or contradicting Hypotheses when evidence allows it.

Avoid redundant Finding chains. Create a parent Finding only when it adds synthesis, qualification, scope, contrast, uncertainty, or aggregation across evidence. If one concrete Finding is enough to answer an AnalyticQuestion or support, refine, or contradict a Hypothesis, connect it directly.

Use reasoning forests when traceability matters:

- Reasoning Support Graph: canonical shared-node graph of Interactions, Tasks, AnalyticQuestions, AnalyticActivities, Findings, Hypotheses, and InvestigationStrategies.
- User Reasoning Forest: descriptive forest reconstructed from the user's trace, rooted at user-authored or analyst-inferred Hypotheses.
- Recommendation Plan Forest: prescriptive forest of Reasoning Gaps, Expansion Rationales, InvestigationStrategies, AnalyticActivities, Recommended Interactions, and Expected Findings.
- Follow-up Investigation Forest: descriptive forest of evidence produced by executing recommendations.
- Reasoning Graph Patch: machine-readable additions or updates that merge follow-up evidence into the canonical graph.
- Augmented Reasoning Forest: regenerated forest after applying Reasoning Graph Patches.

## Evidence Routing

Choose the evidence route before acting:

- Visual Analysis: use when a claim depends on spatial clusters, visible grouping, detector boundaries, links, card alignment, price-window alignment, behavior timelines, manipulation boxes, balance shapes, screenshots, rendered images, or values displayed by the GUI.
- Statistical Analysis: use when a claim depends on exact counts, exact timestamps, exact amounts, transfer paths, wallet overlap, cohort market share, profit/loss, final balances, medians, means, detector-output overlap, or other derived values not displayed by the GUI.
- Model Actions: use when the claim depends on detector outputs, suspicious labels, entity groups, manipulation boxes, link construction, component membership, or threshold-sensitive groupings.
- Synthesis Actions: use when recording, comparing, qualifying, or connecting evidence already produced by visual, data, or model work.

Interaction types:

- Data Action: query, filter, retrieve, aggregate, or compute from data or model outputs, including statistics not displayed in the GUI.
- Model Action: change detector parameters, rerun detection, change grouping rules, choose model settings, vary thresholds, or otherwise alter model outputs.
- Visualization Action: inspect, navigate, select, zoom, compare, change display settings, read GUI-displayed statistics, or interpret trace screenshots and ManiScope views.
- Synthesis Action: annotate, summarize, connect Findings, update a Hypothesis, write a note, or create a traceability link.

AnalyticActivity types:

- Visual Analysis contains one or more Visualization Actions, and the Finding depends on visual inspection, screenshots, GUI-displayed evidence, rendered view evidence, or visual comparison.
- Statistical Analysis contains no Visualization Actions; the Finding comes from data, model outputs, backend endpoints, scripts, command-line queries, or custom computation.
- Model Actions and Synthesis Actions do not determine the AnalyticActivity type by themselves.
- If one candidate activity mixes visual inspection and custom computation, split it into a Visual Analysis activity and a Statistical Analysis activity, then synthesize the results.

Evidence discipline:

- Distinguish logged Interactions, derived UI state, trace screenshots, attached screenshots, user-authored annotations, user-authored Findings, newly rendered visual evidence, raw-data validation, model-output validation, and inferred analysis.
- Use trace screenshots to reconstruct what the user actually saw.
- Use current render APIs to generate new visual evidence for visual questions. Do not merely copy trace screenshots and present them as new visual analysis.
- Treat rendered views as qualitative evidence for timing, density, grouping, and visual comparison. Use raw data or backend endpoints for exact counts and amounts, especially when Behavior Details event dots may be downsampled.
- Use visual, statistical, model, and synthesis evidence together when the claim needs them, but keep them as distinct Interactions or AnalyticActivities. Do not default to script-side statistics.
- For model-derived claims, consider robustness checks by varying detector parameters or rerunning detection. If that check is unavailable or unnecessary, explain why.
- For major Hypotheses and high-level Findings, include a disconfirmation pass. When spawning a skeptical subagent, use a full-context fork with `fork_context: true` only, tell it to read `skills/maniscope-disconfirmation/SKILL.md`, and verify candidate negative Findings before adding `contradicts`, `refines`, or Reasoning Gap entries.
- If a conclusion is uncertain, say what would confirm, weaken, or falsify it.

## Visualization Tools

Use `maniscope_visualization.py` from the session root for new visual evidence. Prefer it over manual browser attachment or ad hoc JavaScript.

Major ManiScope views:

- Token Distribution View: use for holder distribution, suspicious clusters, entity boundaries, relationship links, connected components, selected or highlighted entities, and detector grouping structure.
- K-Line View: use for price phases, manipulation windows, card timing, card cohorts, round-trip versus same-direction card placement, granularity changes, and alignment between suspicious behavior and price movement.
- Behavior Details View: use for selected wallet or cohort timelines, buy/sell/transfer sequence, related users, sequential versus absolute time, manipulation boxes, balance areas, residual holdings, accumulation, exits, and role comparison.

Available view-specific functions:

- Token Distribution: `get_token_distribution_args(...)`, `render_token_distribution(...)`.
- K-Line: `get_kline_args(...)`, `render_kline_chart(...)`.
- Behavior Details: `fetch_behavior_sequences(...)`, `get_behavior_details_args(...)`, `render_behavior_details(...)`.

Treat `get_*_args(...)` outputs as editable starting templates, not constraints. You may change render and model input parameters that are semantically relevant, including time windows, selected users, cohorts, detector outputs, model thresholds, entity or link results, manipulation results, scale, link visibility, granularity, dimensions, card alignment, sequential-time mode, related-user visibility, and manipulation-box visibility.

Save rendered evidence images under `artifacts/` when they support a Finding, Hypothesis, recommendation, or Reasoning Graph Patch.

Visual rendering workflow:

1. Choose the view and evidence target.
2. Call the matching `get_*_args(...)` function to extract current Agent Workspace data and render state.
3. Modify explicit arguments needed for the question, including alternative visual, statistical, or model-derived configurations when useful.
4. Call the matching `render_*` function with a descriptive `artifact_name`.
5. Use the returned artifact path, artifact URL, dependencies, and render metadata in the analysis.
6. Mention the rendered image when it supports a Finding, Hypothesis, InvestigationStrategy, or recommendation.

Existing trace screenshots are enough only when the question is specifically about what the user previously saw and the screenshot directly shows the needed evidence.

## Graph And Artifact Contract

The frontend source of truth is:

- `artifacts/reasoning-graph.json`
- every valid `artifacts/reasoning-graph-patch*.json`

Generated forest JSON or Markdown files are optional exports and are not UI source data.

Graph rules:

- Write `reasoning-graph.json` first as the canonical source of truth.
- During full analysis, persist a valid base graph immediately after reconstructing the user's reasoning from the trace and before recommendation planning, autonomous follow-up investigation, or patch writing.
- Set `reasoning-graph.json.analysisAnchor` exactly to the run startAnchor for full analysis.
- Incremental patches must include `baseAnchor`, `targetAnchor`, and `patchType: "incremental"`.
- Original trace evidence belongs in `reasoning-graph.json`.
- Agent follow-up evidence belongs in `reasoning-graph-patch.json`.
- Verified skeptical counterevidence belongs in `reasoning-graph-patch-skeptical.json`.
- Patch-producing subagents may write assigned files named `reasoning-graph-patch-subagent-<branchId>.json`.
- User-authored annotation claims must become Finding nodes in `reasoning-graph.json`, with provenance such as `annotation:<index>`, `action:<index>`, and `screenshot:<relative-path>` when available.
- Every answerable `AnalyticQuestion` should have explicit mid-level answer Findings connected with `answers` edges.
- Unanswered AnalyticQuestions are validation warnings, not graph errors, when the trace truly contains no answer. Treat each warning as an instruction to decide whether the question is central and answerable; if it is, investigate it and add answer Findings through `reasoning-graph-patch*.json`.
- Skeptical Findings must use `refines` or `contradicts`; do not encode skeptical caveats with support-only edges.
- `user-reasoning-forest.json`, `augmented-reasoning-forest.json`, and their Markdown forms are optional static exports. Do not create or edit them for normal UI operation unless the user explicitly asks for export files.
- Build a readable Finding hierarchy when the trace contains enough evidence: low-level Findings for concrete visual, statistical, or model observations; mid-level Findings that synthesize those observations and answer AnalyticQuestions; and high-level Findings that synthesize multiple mid-level Findings before supporting Hypotheses.
- Create a parent Finding only when it adds synthesis, qualification, scope, contrast, uncertainty, or aggregation across evidence. If one concrete Finding is already enough to answer an AnalyticQuestion or support, refine, or contradict a Hypothesis, connect that Finding directly.
- Avoid both extremes: do not make a flat forest where every Finding directly supports a Hypothesis, and do not make single-child Finding chains where the parent only rephrases the child.
- Do not connect the same mid-level Finding directly to both an AnalyticQuestion and that question's parent Hypothesis unless there is no higher-level Finding to carry the Hypothesis support.
- Rich graph nodes should include `explanation`, `evidenceSummary`, and `reasoningRole`. Agent-created patch nodes must also include `patchRationale`.

Validation commands from the session root:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts
```

Run `materialize` before incremental work when patches already exist. Run `checkpoint` when the active deduplicated patch count reaches 8 or the validator recommends it, unless the user explicitly asks to preserve the unsquashed patch stack.

The validator applies all `reasoning-graph-patch*.json` files. Fix validation errors before reporting completion.

## Background Task And Subagent Orchestration

Heavy full or incremental analysis should use a bridge-owned background task. The main chat agent starts that task by running `uv run python run_full_analysis.py start` or `uv run python run_incremental_analysis.py start` from the session root, then returns quickly so the user can keep chatting. Use the same scripts with `status` or `stop` to inspect or cancel a task.

Rules for background task agents and all L2 subagent spawns:

- Use full-context forks with `fork_context: true`.
- Do not specify `agent_type`, `model`, `reasoning_effort`, or other extra config.
- Pass the same closed trace window, runId, session root, artifact directory, graph contract, and validation requirements.
- L2 subagents must not spawn additional agents.

Background task agent responsibilities:

- Own the assigned full or incremental analysis run.
- Use `session-references/agent-analysis-l2-prompts.md` when spawning L2 workers.
- Write and validate artifacts.
- Decide which independent branches can be handled by L2 workers. After writing and validating the base graph and forming a recommendation or investigation plan, prefer 2-4 high-value patch-producing L2 workers when branches can be validated independently.
- Pre-allocate branch IDs, patch filenames, runIds, node ID prefixes, and target graph IDs for patch-producing L2 workers.
- Validate all child patches, resolve conflicts, verify evidence, and integrate only reliable findings.

Use L2 workers for independent visual, statistical, model-action, skeptical, or hypothesis-expansion subtasks, including support evidence for major user Hypotheses, answer evidence for central AnalyticQuestions, executed Hypothesis Expansion branches, model-action robustness checks, and skeptical or counterevidence review. Use patch-producing workers by default for independent planned branches after a plan is produced. Use report-only workers only when the branch is exploratory, likely to need synthesis before graph integration, or too uncertain for a standalone patch.

Patch-producing L2 worker contract:

- The background task agent must pre-allocate a unique short `branchId`, exact patch filename, runId, node ID prefix, and branch target IDs before spawning the worker.
- Use `artifacts/reasoning-graph-patch-subagent-<branchId>.json` as the patch file.
- Use `subagent-<branchId>` as the runId.
- Use `SA_<branchId>_` as the new node ID prefix.
- Patch-producing workers may write at most one assigned patch file. They must not edit `reasoning-graph.json`, other patch files, generated forests, or another worker's files.
- A subagent patch may reference existing base or current graph node IDs and nodes it creates inside that same patch. It must not depend on another subagent patch.
- If cross-branch synthesis is needed, the background task agent writes a later integration patch after validation.
- Subagent patches must include complete patch node fields, unique node IDs, precise provenance, and a concise report of candidate Findings, evidence paths, suggested relations, uncertainty, rejected checks, deferred checks, and any files created.
- For skeptical subagent patches, set `patchType: "skeptical"` and use `refines` or `contradicts` as the semantic relation for each negative Finding. Do not use support-only skeptical Findings.

## Full Trace-Level Analysis

1. Refresh the canonical trace, Human Workspace state, Agent Workspace state, session git history, screenshots, annotations, and existing analysis artifacts.
2. Build and write `artifacts/reasoning-graph.json` from user Interactions upward through Tasks, AnalyticQuestions, AnalyticActivities, low-level Findings, mid-level answer Findings, high-level synthesis Findings, and Hypotheses.
3. Validate `reasoning-graph.json` with `bun trace_analysis_tools/reasoning_graph/cli.ts artifacts` and fix graph errors and missing user Finding nodes before continuing.
4. Identify Reasoning Gaps where user evidence does not sufficiently support a Finding, Hypothesis, or implied AnalyticQuestion.
5. Build Recommendation Plan Forests for Evidence Completion and Hypothesis Expansion when useful. Plans must be top-down: Hypothesis or AnalyticQuestion -> InvestigationStrategy -> AnalyticActivity -> Interaction -> ExpectedFinding.
6. Decide which planned branches can run in parallel. Prefer patch-producing L2 workers for independent support-seeking, answer-seeking, adjacent-hypothesis investigation, model-action robustness, visual/statistical checks, and skeptical review when the branches can be validated independently. Use report-only workers only for exploratory or synthesis-heavy branches.
7. Execute the highest-value InvestigationStrategies instead of stopping at recommendations.
8. Generate rendered visual evidence for visual claims, compute exact statistics for quantitative claims, and vary model or render parameters when robustness matters.
9. Review L2 outputs and patch files. Reject weak branches, resolve conflicts, and integrate only verified candidate Findings. If multiple subagent patches need synthesis, write a separate integration patch rather than making child patches depend on each other.
10. Record follow-up evidence as Reasoning Graph Patches.
11. For each executed Hypothesis Expansion branch, decide whether the adjacent Hypothesis is supported, rejected, deferred, or unsupported. Supported adjacent Hypotheses must become new agent-authored Hypothesis roots with supporting Findings and patch `add_root` operations. Rejected, deferred, or unsupported branches must be stated explicitly.
12. Validate `reasoning-graph.json` plus all `reasoning-graph-patch*.json` files together.
13. Save durable artifacts under `artifacts/`, including graph JSON, patch JSON, reports, trace-step maps, rendered images, and static forest or HTML exports when requested or useful.

## Incremental Trace Analysis

1. Refresh `live-session.json`, `current-state.json`, session git history, and the analysis artifact manifest.
2. Compare the latest applied graph anchor with the current live traceAnchor. Git history is audit context, but the semantic boundary is the trace anchor.
3. If patches exist, run `bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts` and read `current-reasoning-graph.json` as a derived complete graph.
4. If the prior anchor is missing or the old trace digest no longer matches the current trace prefix, stop and recommend full reanalysis or explicit reconciliation.
5. Analyze only new user Interactions and annotations after the baseAnchor while using the materialized graph as context.
6. Write new evidence to `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json` with `patchType: "incremental"`, `baseAnchor`, `targetAnchor`, and precise provenance.
7. Use `update_node` only to refine metadata on existing nodes. Use `add_node` and `add_edge` for new evidence and relationships.
8. For incremental runs, use L2 workers as evidence or report producers by default. Let an L2 worker write a patch only with an explicit unique patch filename, runId, node ID prefix, valid anchors, and exact target graph IDs.
9. If the new trace adds no material evidence, report that no patch was produced and explain the checked delta.
10. Validate graph plus patches. If checkpoint is recommended because active patch count reaches 8, run checkpoint unless the user asked to keep the patch stack.

## Recommendation And Investigation Flow

Recommendation planning:

- Present recommendations top-down from Hypothesis or AnalyticQuestion to InvestigationStrategy, AnalyticActivity, Interaction, and ExpectedFinding.
- Use precise terms: InvestigationStrategy, AnalyticActivity, and Interaction.
- Distinguish Evidence Completion from Hypothesis Expansion.
- Evidence Completion fills a Reasoning Gap in the existing User Reasoning Forest.
- Hypothesis Expansion proposes a related new Hypothesis and grows a new branch or tree.
- Each InvestigationStrategy must operationalize the Hypothesis through concrete targets, analytic contrasts, search concepts, decision criteria, or falsification criteria.
- Do not merely restate the Hypothesis.
- Label each recommended Interaction as Data Action, Model Action, Visualization Action, or Synthesis Action.
- Label each recommended AnalyticActivity as Visual Analysis or Statistical Analysis.

Autonomous investigation:

- First state a short InvestigationStrategy plan unless the user asks for no planning.
- Execute the needed Visual Analysis, Statistical Analysis, Model Actions, and Synthesis Actions unless the user asks for planning-only.
- For visual evidence, render focused views with `maniscope_visualization.py` unless an existing trace screenshot is exactly the needed evidence.
- For broad or deep investigations, spawn subagents when available with `fork_context: true` only and bounded assignment messages. Continue useful non-overlapping work locally. If no spawn tool is available, proceed in the current thread and say so briefly.
- For Hypothesis Expansion, produce concrete follow-up Findings from executed Interactions. Promote supported adjacent Hypotheses with patch `add_root` operations or explicitly mark them rejected, deferred, or unsupported.
- Report completed checks, blocked checks, evidence, Findings, and unresolved gaps.

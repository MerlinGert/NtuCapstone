# ManiScope Agent Analysis Prompt Templates

Use these templates when spawning background ManiScope analysis agents. The spawning agent must fill in the closed trace window, runId, branch IDs, target IDs, expected files, and any user-specific request context.

All spawned agents must use `fork_context: true` only. Do not specify `agent_type`, `model`, `reasoning_effort`, or other extra config. L2 agents must not spawn additional agents.

## Template: L1 Full Analysis Task

You are the L1 full-analysis task agent for this ManiScope session.

Read first:

- `session-references/manual-for-agent.md`
- `session-references/major-view-render-api.md`
- `session-references/agent-analysis-playbook.md`
- `session-references/agent-analysis-prompts.md`

Own the full trace-analysis pipeline for the closed trace window provided by the parent. Reconstruct the user's reasoning only up to the run `startAnchor`. Write and validate `artifacts/reasoning-graph.json` first, with `analysisAnchor` equal to the run `startAnchor`, so the LLM Analysis tab can render while you continue.

The base graph must include user-authored annotation claims as Findings, explicit answer Findings for answerable AnalyticQuestions, and a readable Finding hierarchy without pass-through single-child rephrasing chains. If one concrete Finding is already enough to answer an AnalyticQuestion or support, refine, or contradict a Hypothesis, connect it directly. Include available provenance such as `annotation:<index>`, `action:<index>`, and `screenshot:<relative-path>`.

Then plan follow-up checks, execute high-value visual/statistical/model/synthesis investigations, run skeptical review, write validated `reasoning-graph-patch*.json` files, and save final artifacts under `artifacts/`. If the live trace advances while you work, defer those later records to Update Analysis instead of revising this run. Do not create or edit generated forest JSON/Markdown files for normal UI operation unless explicitly requested; the UI reads `reasoning-graph.json` plus valid patches.

You may spawn L2 subagents with `fork_context: true` only for independent visual, statistical, model-action, skeptical, or hypothesis-expansion subtasks. L2 subagents must not spawn additional agents. Pre-allocate branch IDs, file names, runIds, node ID prefixes, target graph IDs, and the same closed trace window before spawning any L2 patch-producing worker.

For patch-producing L2 workers, assign exactly one patch file named `artifacts/reasoning-graph-patch-subagent-<branchId>.json`, runId `subagent-<branchId>`, node prefix `SA_<branchId>_`, and exact target graph IDs. Child patches must not edit `reasoning-graph.json`, depend on sibling patches, or modify generated forests. If cross-branch synthesis is needed, write a later integration patch yourself after validation.

You own validation, conflict resolution, and integration of all L2 outputs. Validate `reasoning-graph.json` plus all `reasoning-graph-patch*.json` files before reporting completion, and fix validation errors before finalizing. End with a plain-language summary or explanation in the user's language.

## Template: L1 Incremental Analysis Task

You are the L1 incremental-analysis task agent for this ManiScope session.

Read first:

- `session-references/manual-for-agent.md`
- `session-references/major-view-render-api.md`
- `session-references/agent-analysis-playbook.md`
- `session-references/agent-analysis-prompts.md`

Do not redo full trace analysis unless incremental analysis is unsafe. Refresh `live-session.json`, `current-state.json`, session git history, and the analysis artifact manifest. Compare the latest graph or patch trace anchor against the closed trace window `startAnchor` for this run. Use that `startAnchor` as `targetAnchor` and defer any later live trace changes.

If `reasoning-graph-patch*.json` files already exist, first run:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
```

Read `current-reasoning-graph.json` as the complete patched context, but do not treat it as the source of truth. Analyze only new user Interactions and annotations after the latest applied anchor. Use the existing materialized graph as context. Do not rewrite `reasoning-graph.json` unless checkpointing is required.

Write any new evidence as:

```text
reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json
```

The patch must include `patchType: "incremental"`, `baseAnchor`, `targetAnchor`, and precise provenance for the new trace range. Agent-created nodes must include `explanation`, `evidenceSummary`, `reasoningRole`, and `patchRationale`. Avoid pass-through single-child Finding chains in incremental patches; connect a concrete Finding directly when it is enough.

For incremental runs, use L2 subagents as evidence or report producers by default. Allow an L2 worker to write a patch only when you assign a unique patch filename, runId, node ID prefix, valid `baseAnchor` and `targetAnchor`, and exact target graph IDs. L2 subagents must not spawn additional agents. Child patches must not depend on sibling patches; if synthesis is needed, write a separate integration patch yourself after validation.

If the new trace delta adds no material evidence, report that no patch was produced and explain exactly what delta you checked. After writing any patch, run:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
```

Fix validation errors before reporting completion. If the validator recommends checkpointing because active patch count reaches 8, run checkpoint unless the user explicitly asks to preserve the patch stack.

Final response format:

```markdown
# Technical Audit

- previous anchor:
- new trace anchor:
- analyzed action and annotation range:
- patch file written:
- supporting evidence files:
- validation result:
- checkpoint status:
- unresolved warnings:

# Plain-Language Summary

Explain what new user behavior was analyzed, what the user seemed to be checking, what evidence was found, which Hypotheses were strengthened, weakened, or refined, whether a new Hypothesis was created, what caveats matter, and what the analyst should watch next. Do not lead with revision numbers, digests, patch filenames, node IDs, or validation counts.
```

## Template: L2 Visual Worker

You are an L2 visual-analysis worker. Do not spawn additional agents.

Read `session-references/agent-analysis-playbook.md` and `session-references/major-view-render-api.md`. Analyze only the assigned closed trace window and target IDs. Use trace screenshots to reconstruct what the user saw, and use `maniscope_visualization.py` to render new focused visual evidence when needed.

Return or write only the assigned deliverable. If patch-producing, write only the assigned patch file with the assigned runId, node ID prefix, target IDs, and provenance; do not edit `reasoning-graph.json`, other patches, or generated forests. If report-only, return concise Findings, evidence paths, rendered image paths, caveats, and rejected checks.

## Template: L2 Statistical Worker

You are an L2 statistical-analysis worker. Do not spawn additional agents.

Read `session-references/agent-analysis-playbook.md`. Analyze only the assigned closed trace window and target IDs. Use raw data, model outputs, or scripts for exact counts, timestamps, amounts, overlaps, role statistics, profits/losses, medians, means, and detector-output comparisons.

Return or write only the assigned deliverable. If patch-producing, write only the assigned patch file and do not edit `reasoning-graph.json`, other patches, or generated forests. Include script paths, input files, exact filters, computed values, caveats, and whether the result supports, refines, or contradicts the assigned target.

## Template: L2 Model-Action Worker

You are an L2 model-action robustness worker. Do not spawn additional agents.

Read `session-references/agent-analysis-playbook.md`. Analyze only the assigned closed trace window and target IDs. Vary detector parameters, grouping rules, model outputs, thresholds, or linked components when relevant to test whether a model-derived claim is robust.

Return or write only the assigned deliverable. If patch-producing, write only the assigned patch file and do not edit `reasoning-graph.json`, other patches, or generated forests. Include parameter settings, output differences, visual or statistical evidence, and whether the target claim is stable, narrowed, weakened, or unsupported.

## Template: L2 Skeptical Worker

You are an L2 skeptical-review worker. Do not spawn additional agents.

Read:

- `session-references/agent-analysis-playbook.md`
- `skills/maniscope-disconfirmation/SKILL.md`

Search for negative evidence, false positives, benign alternatives, detector-parameter failures, missing causal links, denominator mistakes, or role-label ambiguities against the assigned Hypothesis or high-level Finding.

Return or write only the assigned deliverable. If patch-producing, write only the assigned patch file and do not edit `reasoning-graph.json`, other patches, or generated forests. Verified skeptical Findings should use `refines` or `contradicts`, not support-only edges. If evidence is weak, report it as deferred or rejected rather than forcing a patch.

## Template: L2 Hypothesis-Expansion Worker

You are an L2 hypothesis-expansion worker. Do not spawn additional agents.

Read `session-references/agent-analysis-playbook.md`. Analyze only the assigned closed trace window and target IDs. Test whether an adjacent Hypothesis is supported by concrete follow-up Findings rather than plausibility alone.

Return or write only the assigned deliverable. If patch-producing, write only the assigned patch file and do not edit `reasoning-graph.json`, other patches, or generated forests. If supported, provide candidate Hypothesis, Findings, evidence paths, and suggested `add_root` or support edges. If unsupported, rejected, or deferred, state why and what evidence would be needed.

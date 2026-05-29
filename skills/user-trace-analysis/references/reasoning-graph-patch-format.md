# Reasoning Graph Patch Format

Use `reasoning-graph-patch-*.json` after executing a Recommendation Plan Forest. A patch records evidence-backed additions from follow-up investigation and merges them into the canonical `reasoning-graph.json`.

Do not manually edit generated forest Markdown. Apply patches to the graph, then regenerate forests.
For live sessions, prefer the session-local TypeScript graph tool for validation, materialization, and checkpointing.

## Patch Shape

```json
{
  "version": 1,
  "runId": "investigation-run-001",
  "patchType": "main",
  "description": "Quantified clicked cohort behavior for H3",
  "operations": []
}
```

Use these patch types:

- `main`: primary agent follow-up evidence from executed Investigation Strategies.
- `skeptical`: verified disconfirmation or counterevidence, normally saved as `reasoning-graph-patch-skeptical.json`.
- `incremental`: evidence from new user Interactions or annotations after an earlier anchored analysis.

Incremental patches must be named `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json` and include both anchors:

```json
{
  "version": 1,
  "runId": "incremental-37-52-001",
  "patchType": "incremental",
  "baseAnchor": {
    "sessionId": "abcde",
    "traceRevision": 37,
    "actionCount": 25,
    "annotationCount": 18,
    "traceDigest": "sha256:..."
  },
  "targetAnchor": {
    "sessionId": "abcde",
    "traceRevision": 52,
    "actionCount": 31,
    "annotationCount": 22,
    "traceDigest": "sha256:..."
  },
  "operations": []
}
```

The base anchor must match the latest graph anchor after applying existing patches. If the trace digest indicates that old trace content changed rather than only being appended, stop incremental work and run full reanalysis or explicit reconciliation.

Allowed operations:

- `add_node`
- `add_edge`
- `update_node`
- `add_root`

## Add Node

New follow-up evidence nodes must include all normal `reasoning-graph.json` node fields plus:

- `actor`: usually `agent`.
- `source`: usually `followup_investigation`.
- `planRef`: object linking the new node to the plan that produced it.
- `explanation`: human-readable meaning of the added node.
- `evidenceSummary`: concrete evidence produced by the follow-up investigation.
- `reasoningRole`: how this node patches, supports, refines, or expands the original User Reasoning Forest.
- `patchRationale`: why this node belongs in the augmented reasoning graph rather than only in the follow-up report.

Example:

```json
{
  "op": "add_node",
  "node": {
    "id": "AI1",
    "kind": "Interaction",
    "space": "Action",
    "scope": "Low",
    "label": "Compute clicked cohort buy/sell counts and USD volume",
    "interactionType": "Data Action",
    "salience": "primary",
    "provenance": ["data:front/public/data/sorted_trades.csv"],
    "confidence": "Direct evidence",
    "actor": "agent",
    "source": "followup_investigation",
    "explanation": "This calculation checks whether the clicked manipulation-card users have measurable trade roles rather than only visual co-occurrence.",
    "evidenceSummary": "Uses sorted ACT trades to compute buy count, sell count, USD volume, and net direction for the clicked cohort.",
    "reasoningRole": "Produces a follow-up Finding that can support or weaken the original colluding-group Hypothesis.",
    "patchRationale": "The original trace used visual card evidence; this node adds the missing statistical evidence required to patch that reasoning gap.",
    "planRef": {
      "strategyId": "RS1",
      "activityId": "AA1",
      "recommendedInteractionId": "RI1",
      "expectedFindingId": "EF1",
      "gapId": "RG1"
    }
  }
}
```

## Add Edge

Use normal reasoning graph relation types. Evidence completion commonly adds:

- `Interaction -> Finding` with `produces`.
- `Finding -> AnalyticQuestion` with `answers` when follow-up evidence directly resolves a question.
- `Finding -> Hypothesis` with `supports`, `refines`, or `contradicts`.

```json
{
  "op": "add_edge",
  "edge": {
    "source": "AI1",
    "target": "F_AGENT_1",
    "relation": "produces",
    "rationale": "The scripted calculation produced the follow-up cohort-volume finding."
  }
}
```

## Update Node

Use `update_node` only for small metadata updates, such as confidence or provenance. Do not change node identity.

```json
{
  "op": "update_node",
  "id": "H3",
  "set": {
    "confidence": "Strong inference"
  }
}
```

## Add Root

Use `add_root` when a Hypothesis Expansion follow-up creates an evidence-backed new Hypothesis. Do this whenever an adjacent Hypothesis is supported strongly enough to become a separate reasoning tree. If the follow-up does not support the proposed adjacent Hypothesis, do not add a root; document the rejection or deferral in the follow-up report and, when evidence supports it, add a `Finding` that `contradicts` or `refines` the proposed direction.

```json
{
  "op": "add_root",
  "id": "H_AGENT_1"
}
```

## Applying A Patch

For live sessions, validate and materialize with:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
```

If the active deduplicated patch count reaches 8, compact the patch stack with:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts
```

For static exported trace folders, the Python script can still produce optional forest exports:

```bash
python skills/user-trace-analysis/scripts/apply_reasoning_graph_patch.py \
  TRACE/analysis-results/reasoning-graph.json \
  TRACE/analysis-results/reasoning-graph-patch-001.json
```

By default, the script writes:

- `TRACE/analysis-results/augmented-reasoning-graph.json`
- `TRACE/analysis-results/augmented-reasoning-forest.json`
- `TRACE/analysis-results/augmented-reasoning-forest.md`

The script validates the augmented graph with `reasoning_graph_to_forest.py` before writing forest outputs.

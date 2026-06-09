# Reasoning Graph Format

Use `reasoning-graph.json` as the canonical shared-node representation for a ManiScope trace analysis. Generate the readable `user-reasoning-forest.md` from this graph instead of hand-authoring tree duplicates.

## Files

For a full trace analysis, place these files in `TRACE/analysis-results/`:

- `reasoning-graph.json`: canonical graph with shared nodes.
- `current-reasoning-graph.json`: optional derived graph produced by applying all current patch files; use as a reading aid for global context, not as the UI source of truth.
- `user-reasoning-forest.json`: generated tree instances with duplicated shared nodes.
- `user-reasoning-forest.md`: generated Markdown and Mermaid forest.

## Trace Anchors

Use anchors to record which trace version a graph or patch covers. A base graph should include `analysisAnchor`; materialized graphs and applied patch stacks may also include `latestAnchor`.

```json
{
  "analysisAnchor": {
    "sessionId": "abcde",
    "traceRevision": 37,
    "actionCount": 25,
    "annotationCount": 18,
    "lastActionId": "24",
    "lastAnnotationId": "18",
    "traceDigest": "sha256:...",
    "gitCommit": "optional"
  }
}
```

`traceRevision`, `actionCount`, and `annotationCount` must be non-negative integers. `traceDigest` is the semantic digest of the canonical trace content. A git commit may be included for audit, but it is not the semantic boundary for incremental analysis.

## Node Schema

Each node must have:

```json
{
  "id": "I14",
  "kind": "Interaction",
  "space": "Action",
  "scope": "Low",
  "label": "Click first 9-user manipulation card",
  "provenance": ["action:14", "screenshot:../images/action-0014-source-kline_chart-01.png"],
  "confidence": "Direct evidence"
}
```

Allowed `space` values:

- `Intention`
- `Action`
- `Finding`

Allowed `scope` values:

- `Low`
- `Mid`
- `High`

Allowed `kind` values:

- `Interaction`
- `Task`
- `AnalyticQuestion`
- `Hypothesis`
- `AnalyticActivity`
- `InvestigationStrategy`
- `Finding`

Required kind-specific fields:

- `Interaction`: include `interactionType` and `salience`.
- `AnalyticActivity`: include `activityType`.

Allowed `interactionType` values:

- `Data Action`
- `Model Action`
- `Visualization Action`
- `Synthesis Action`

Allowed `activityType` values:

- `Visual Analysis`
- `Statistical Analysis`

Allowed `salience` values:

- `primary`: directly supports a major Finding or Hypothesis.
- `supporting`: provides context or strengthens a reasoning path.
- `low`: logged but weakly relevant, such as incidental hover, scroll, or layout navigation.

Every node must include a non-empty `label`, `confidence`, and `provenance` list. Use `provenance` to separate evidence sources:

- `action:<index>`
- `annotation:<index>`
- `screenshot:<relative-path>`
- `data:<path-or-query>`
- `render:<relative-path>`
- `inference:<short-note>`

`screenshot:<relative-path>` and `render:<relative-path>` should be durable relative paths from `TRACE/analysis-results/`. Original trace screenshots usually use `screenshot:../images/...`. Rendered follow-up images should be saved under an assets folder inside `analysis-results`, usually `render:continued-investigation-assets/...`. Do not use transient browser data URLs as durable provenance.

Rich detail fields keep compact graph labels understandable in HTML viewers and downstream follow-up work:

- `explanation`: what the node means in human-readable terms.
- `evidenceSummary`: the concrete evidence used for the node.
- `reasoningRole`: how the node contributes to its parent, tree, or reasoning gap.
- `patchRationale`: why an agent-created follow-up node was added to the original reasoning graph.

Require `explanation` for every `Hypothesis`, `Finding`, `AnalyticQuestion`, `Task`, `InvestigationStrategy`, and `AnalyticActivity`. For `Interaction`, require `explanation` when `salience` is `primary` or the node was created by an agent follow-up. Low-salience logged interactions may stay compact when their label and provenance are sufficient.

## Edge Schema

Each edge must have:

```json
{
  "source": "I14",
  "target": "F9",
  "relation": "produces",
  "rationale": "The card click and Behavior Details inspection produced the same-direction cohort finding."
}
```

Allowed relations:

| Relation | Direction | Meaning |
|---|---|---|
| `motivates` | Intention -> Action Space unit | A Task, Analytic Question, or Hypothesis explains why an Interaction, Analytic Activity, or Investigation Strategy happened. |
| `produces` | Action Space unit -> Finding Space output | An Interaction, Analytic Activity, or Investigation Strategy generated a Finding. |
| `answers` | Mid-level Finding -> Analytic Question | A mid-level Finding directly answers, partially answers, bounds, or caveats an Analytic Question. |
| `supports` | Finding Space output -> Finding Space output or Intention | A Finding strengthens another Finding, a Task interpretation, an Analytic Question, or a Hypothesis. |
| `refines` | Finding Space output -> Intention | A Finding changes or narrows the intention. |
| `contradicts` | Finding Space output -> Intention | A Finding weakens or falsifies the intention. |
| `contains` | Higher-level unit -> lower-level unit | A Hypothesis contains Analytic Questions, an Analytic Activity contains Interactions, or another hierarchical containment relation is useful. |
| `derived_from` | Analyst-inferred node -> evidence node | A node was inferred from raw trace evidence, screenshots, annotations, local data, or rendered visual evidence. |

## Graph Schema

```json
{
  "version": 1,
  "trace": "maniscope-session-ACT-20260501-025125",
  "analysisAnchor": {
    "sessionId": "abcde",
    "traceRevision": 37,
    "actionCount": 25,
    "annotationCount": 18,
    "traceDigest": "sha256:..."
  },
  "roots": ["H3"],
  "nodes": [],
  "edges": []
}
```

Use `roots` for Hypothesis IDs. If `roots` is omitted, the transformer uses all nodes whose `kind` is `Hypothesis`.

## Forest Projection Rules

The User Reasoning Forest is a support projection of the canonical graph. It uses `flowchart BT`, so visual edges point from lower-level evidence to higher-level reasoning.

The transformer converts relations to child -> parent tree edges as follows:

| Source relation | Tree child | Tree parent |
|---|---|---|
| `produces` | edge source | edge target |
| `answers` | edge source | edge target |
| `supports` | edge source | edge target |
| `refines` | edge source | edge target |
| `contradicts` | edge source | edge target |
| `motivates` | edge target | edge source |
| `contains` | edge target | edge source |
| `derived_from` | edge target | edge source |

`contradicts` should remain visible in the forest as counter-evidence, not silently removed.

Shared canonical nodes are duplicated mechanically. Each tree node instance must keep both:

- `instanceId`: unique ID in the derived tree.
- `canonicalId`: original node ID from `reasoning-graph.json`.

The forest must preserve raw Interaction leaves by default. If a compact Step view is also useful, keep it in `trace-step-map.md`, not as a replacement for Interaction leaves in the User Reasoning Forest.

Every answerable `AnalyticQuestion` should have at least one incoming `answers` edge from a mid-level `Finding`. If the trace only yields a partial or uncertain answer, encode that caveat in the Finding's label, confidence, `explanation`, and `reasoningRole`. If the user trace does not answer the question at all, leave the question unanswered in the base reasoning graph. The validator reports this as a warning, not an error. Treat the warning as a follow-up instruction: if the question is central and answerable, investigate it and add answer Findings through a patch.

Use a real Finding hierarchy when the trace contains enough evidence:

- Low-level Findings record concrete observations from one Interaction or one narrow Analytic Activity, such as a displayed count, a visible cluster, a clicked card cohort, an exact script-derived volume, or a single rendered view check.
- Mid-level Findings answer Analytic Questions by synthesizing one or more low-level Findings. These are the normal source nodes for `answers` edges.
- High-level Findings synthesize several mid-level Findings into a session-level claim, caveat, or interpretation. They should support, refine, or contradict Hypotheses.

Create a parent Finding only when it adds synthesis, qualification, scope, contrast, uncertainty, or aggregation across evidence. If one concrete Finding is already enough to answer an Analytic Question or support, refine, or contradict a Hypothesis, connect that Finding directly. Avoid both extremes: do not make a flat forest where every Finding directly supports a Hypothesis, and do not make single-child Finding chains where the parent only rephrases the child. Keep explicit `mid Finding -> AnalyticQuestion` `answers` edges for traceability.

## Validation Expectations

Before using a graph in a report or live session:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
```

When patch files exist and an agent needs the full current graph, materialize first:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
```

This writes `current-reasoning-graph.json` as a derived reading aid. It does not replace `reasoning-graph.json`.

When the active deduplicated root-level patch count reaches 8, checkpoint the stack unless the user asks to preserve the unsquashed patch history:

```bash
bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts
```

Checkpointing archives the old base graph and active patches, then writes a new materialized `reasoning-graph.json` baseline.

The script should fail if:

- `version` is not `1`,
- `trace` is missing,
- `analysisAnchor` or `latestAnchor`, when present, is malformed,
- node IDs are duplicated,
- a node is missing `id`, `kind`, `space`, `scope`, `label`, `confidence`, or `provenance`,
- a non-trivial reasoning node is missing `explanation`,
- a primary or agent-created Interaction node is missing `explanation`,
- a node uses an unknown `kind`, `space`, or `scope`,
- a node uses a `space` or `scope` that does not match its `kind`,
- an edge references a missing node,
- an edge is a self-edge,
- a relation is unknown,
- a relation points in the wrong direction for its type,
- an Analytic Question has no incoming `answers` edge from a mid-level Finding (warning unless strict error mode is requested),
- an `answers` edge uses a non-mid-level Finding as its source,
- an edge lacks a non-empty `rationale`,
- an Interaction lacks `salience`,
- an Interaction lacks `interactionType`,
- an Interaction has an unknown `salience` or `interactionType`,
- an Analytic Activity lacks `activityType`,
- an Analytic Activity has an unknown `activityType`,
- no Hypothesis roots are available,
- a listed root is not a Hypothesis node,
- the support projection contains a cycle,
- a generated tree has no support edges,
- a generated tree has non-Interaction leaves.

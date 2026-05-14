# Reasoning Graph Format

Use `reasoning-graph.json` as the canonical shared-node representation for a ManiScope trace analysis. Generate the readable `user-reasoning-forest.md` from this graph instead of hand-authoring tree duplicates.

## Files

For a full trace analysis, place these files in the trace folder:

- `reasoning-graph.json`: canonical graph with shared nodes.
- `user-reasoning-forest.json`: generated tree instances with duplicated shared nodes.
- `user-reasoning-forest.md`: generated Markdown and Mermaid forest.

## Node Schema

Each node must have:

```json
{
  "id": "I14",
  "kind": "Interaction",
  "space": "Action",
  "scope": "Low",
  "label": "Click first 9-user manipulation card",
  "provenance": ["action:14", "screenshot:images/action-0014-source-kline_chart-01.png"],
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
- `Insight`

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

- `primary`: directly supports a major Finding, Insight, or Hypothesis.
- `supporting`: provides context or strengthens a reasoning path.
- `low`: logged but weakly relevant, such as incidental hover, scroll, or layout navigation.

Every node must include a non-empty `label`, `confidence`, and `provenance` list. Use `provenance` to separate evidence sources:

- `action:<index>`
- `annotation:<index>`
- `screenshot:<relative-path>`
- `data:<path-or-query>`
- `render:<relative-path>`
- `inference:<short-note>`

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
| `produces` | Action Space unit -> Finding Space output | An Interaction, Analytic Activity, or Investigation Strategy generated a Finding or Insight. |
| `supports` | Finding Space output -> Finding Space output or Intention | A Finding or Insight strengthens another Finding, an Insight, a Task interpretation, an Analytic Question, or a Hypothesis. |
| `refines` | Finding Space output -> Intention | A Finding or Insight changes or narrows the intention. |
| `contradicts` | Finding Space output -> Intention | A Finding or Insight weakens or falsifies the intention. |
| `contains` | Higher-level unit -> lower-level unit | A Hypothesis contains Analytic Questions, an Analytic Activity contains Interactions, or another hierarchical containment relation is useful. |
| `derived_from` | Analyst-inferred node -> evidence node | A node was inferred from raw trace evidence, screenshots, annotations, local data, or rendered visual evidence. |

## Graph Schema

```json
{
  "version": 1,
  "trace": "maniscope-session-ACT-20260501-025125",
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

## Validation Expectations

Before using a graph in a report:

```bash
python skills/user-trace-analysis/scripts/reasoning_graph_to_forest.py TRACE/reasoning-graph.json
```

The script should fail if:

- `version` is not `1`,
- `trace` is missing,
- node IDs are duplicated,
- a node is missing `id`, `kind`, `space`, `scope`, `label`, `confidence`, or `provenance`,
- a node uses an unknown `kind`, `space`, or `scope`,
- a node uses a `space` or `scope` that does not match its `kind`,
- an edge references a missing node,
- an edge is a self-edge,
- a relation is unknown,
- a relation points in the wrong direction for its type,
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

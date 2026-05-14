# Reasoning Graph Patch Format

Use `reasoning-graph-patch-*.json` after executing a Recommendation Plan Forest. A patch records evidence-backed additions from follow-up investigation and merges them into the canonical `reasoning-graph.json`.

Do not manually edit generated forest Markdown. Apply patches to the graph, then regenerate forests.

## Patch Shape

```json
{
  "version": 1,
  "runId": "investigation-run-001",
  "description": "Quantified clicked cohort behavior for H3",
  "operations": []
}
```

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

Use `add_root` when a Hypothesis Expansion follow-up creates an evidence-backed new Hypothesis. Do this whenever an adjacent Hypothesis is supported strongly enough to become a separate reasoning tree. If the follow-up does not support the proposed adjacent Hypothesis, do not add a root; document the rejection or deferral in the follow-up report and, when evidence supports it, add a `Finding` or `Insight` that `contradicts` or `refines` the proposed direction.

```json
{
  "op": "add_root",
  "id": "H_AGENT_1"
}
```

## Applying A Patch

```bash
python skills/user-trace-analysis/scripts/apply_reasoning_graph_patch.py \
  TRACE/reasoning-graph.json \
  TRACE/reasoning-graph-patch-001.json
```

By default, the script writes:

- `TRACE/augmented-reasoning-graph.json`
- `TRACE/augmented-reasoning-forest.json`
- `TRACE/augmented-reasoning-forest.md`

The script validates the augmented graph with `reasoning_graph_to_forest.py` before writing forest outputs.

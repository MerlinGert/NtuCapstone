# Recommendation Plan Format

Use `recommendation-plan-graph.json` and `recommendation-plan-forest.md` when trace analysis produces recommendations. These artifacts are prescriptive. They describe what should be investigated next, not what has already been proven. In a full trace analysis, producing the plan is not sufficient: execute the plan next unless the user explicitly requested analysis-only, recommendation-only, or planning-only output.

## Conceptual Role

The Recommendation Plan Forest is the planning counterpart of the User Reasoning Forest:

- User Reasoning Forest: descriptive, evidence-backed, rooted at user Hypotheses.
- Recommendation Plan Forest: prescriptive, future-oriented, rooted at existing or proposed Hypotheses.
- Follow-up Investigation Forest: descriptive, evidence-backed, produced after executing the plan.

## Recommendation Types

Use exactly one recommendation type per top-level recommendation branch:

- `Evidence Completion`: fills a Reasoning Gap under an existing Finding or Hypothesis.
- `Hypothesis Expansion`: proposes a new related Hypothesis from an existing Finding or Hypothesis.

## Node Kinds

Allowed plan node kinds:

- `SourceNode`: reference to a node from `reasoning-graph.json`.
- `Hypothesis`: existing or proposed Hypothesis.
- `ReasoningGap`: missing, weak, contradictory, or under-supported reasoning path.
- `ExpansionRationale`: source pattern that justifies a new Hypothesis.
- `InvestigationStrategy`: high-level plan for testing a Hypothesis.
- `AnalyticActivity`: mid-level unit typed as Visual Analysis or Statistical Analysis.
- `RecommendedInteraction`: future executable operation typed as Data Action, Model Action, Visualization Action, or Synthesis Action.
- `ExpectedFinding`: target outcome expected from the plan. This is not evidence.

Required common fields:

```json
{
  "id": "RG1",
  "kind": "ReasoningGap",
  "label": "Exact clicked-cohort volume is missing",
  "recommendationType": "Evidence Completion",
  "status": "planned"
}
```

Kind-specific fields:

- `SourceNode`: include `canonicalId` from `reasoning-graph.json`.
- `Hypothesis`: include `hypothesisStatus`, either `existing` or `proposed`.
- `ReasoningGap`: include `targetNodeId`, `gapType`, and `desiredSupport`.
- `ExpansionRationale`: include `sourceNodeId`.
- `InvestigationStrategy`: include `explanation`. When useful, include `targetContext`, `analyticContrast`, `searchConcepts`, `decisionCriteria`, and `falsificationCriteria`.
- `AnalyticActivity`: include `activityType`.
- `RecommendedInteraction`: include `interactionType`.
- `ExpectedFinding`: include `expectedOnly: true`.

Rich detail fields keep plan labels compact while making the plan executable:

- `explanation`: required for `ReasoningGap`, `InvestigationStrategy`, proposed or existing plan `Hypothesis`, `ExpansionRationale`, and `ExpectedFinding`.
- `evidenceSummary`: existing evidence or trace context that motivates the plan node.
- `reasoningRole`: how the node functions in the Recommendation Plan Forest.

`InvestigationStrategy.label` should stay compact for tree display. `InvestigationStrategy.explanation` should provide enough context for a human or follow-up agent to understand and execute the strategy without chasing shorthand IDs through other files. Expand opaque references in the explanation, such as "the 9-user Behavior Details card selected around interaction 16 (A16)" instead of only `A16`.

An `InvestigationStrategy` should operationalize a Hypothesis into an evidence-seeking direction. Valid patterns include role classification, targeted role discovery, cohort comparison, mechanism tracing, anomaly search, and falsification. Do not use an `InvestigationStrategy` that only restates the Hypothesis in plan language.

Allowed `activityType` values:

- `Visual Analysis`
- `Statistical Analysis`

Allowed `interactionType` values:

- `Data Action`
- `Model Action`
- `Visualization Action`
- `Synthesis Action`

## Plan Relations

Use these relations in `recommendation-plan-graph.json`:

| Relation | Direction | Meaning |
|---|---|---|
| `has_gap` | SourceNode or Hypothesis -> ReasoningGap | Existing reasoning has a gap to fill. |
| `expands_from` | SourceNode -> proposed Hypothesis | A new Hypothesis is derived from existing reasoning. |
| `has_rationale` | proposed Hypothesis -> ExpansionRationale | The new Hypothesis has an explicit rationale. |
| `addressed_by` | ReasoningGap -> InvestigationStrategy | The strategy is intended to fill the gap. |
| `tested_by` | Hypothesis -> InvestigationStrategy | The strategy tests the Hypothesis. |
| `contains` | InvestigationStrategy -> AnalyticActivity, or AnalyticActivity -> RecommendedInteraction | The parent plan unit contains the child plan unit. |
| `expects` | RecommendedInteraction or AnalyticActivity -> ExpectedFinding | The plan unit is expected to produce the target finding. |

## Graph Shape

Evidence Completion branch:

```text
Existing Hypothesis or SourceNode
  -> ReasoningGap
    -> InvestigationStrategy
      -> AnalyticActivity
        -> RecommendedInteraction
          -> ExpectedFinding
```

Hypothesis Expansion branch:

```text
SourceNode
  -> Proposed Hypothesis
    -> ExpansionRationale
    -> InvestigationStrategy
      -> AnalyticActivity
        -> RecommendedInteraction
          -> ExpectedFinding
```

## Example

```json
{
  "version": 1,
  "trace": "maniscope-session-ACT-20260501-025125",
  "nodes": [
    {
      "id": "SRC_H3",
      "kind": "SourceNode",
      "canonicalId": "H3",
      "label": "Oct 25-27 coordinated price activity",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    },
    {
      "id": "RG1",
      "kind": "ReasoningGap",
      "targetNodeId": "H3",
      "gapType": "missing_statistical_validation",
      "desiredSupport": "A Finding that quantifies clicked cohort buy/sell volume.",
      "label": "Exact clicked-cohort volume is missing",
      "explanation": "The trace shows the clicked manipulation-card cohort visually, but the graph does not yet quantify its exact buy/sell volume.",
      "evidenceSummary": "The source Hypothesis is supported by Behavior Details screenshots and annotations, not by a computed trade table.",
      "reasoningRole": "Marks the missing evidence that the downstream Investigation Strategy must fill.",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    },
    {
      "id": "RS1",
      "kind": "InvestigationStrategy",
      "label": "Quantify clicked cohort behavior",
      "explanation": "The user treated the clicked cohort as evidence for coordinated ACT behavior. Quantify the cohort's buy/sell volume, timing, and net direction so the existing Hypothesis is supported or weakened by concrete trade evidence rather than only by visual card inspection.",
      "evidenceSummary": "Inputs are the clicked Behavior Details cohort and local ACT trade records.",
      "reasoningRole": "Turns the Reasoning Gap into executable statistical analysis.",
      "targetContext": "Clicked manipulation-card cohort from the trace",
      "analyticContrast": "coordinated same-window behavior versus incidental co-occurrence",
      "searchConcepts": ["buy/sell imbalance", "trade timing", "volume concentration"],
      "decisionCriteria": "Support increases if the cohort has concentrated same-window activity with material net direction and volume relative to the surrounding market.",
      "falsificationCriteria": "Support weakens if activity is low-volume, temporally scattered, or directionally inconsistent with the suspected manipulation window.",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    },
    {
      "id": "AA1",
      "kind": "AnalyticActivity",
      "activityType": "Statistical Analysis",
      "label": "Compute cohort trade totals",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    },
    {
      "id": "RI1",
      "kind": "RecommendedInteraction",
      "interactionType": "Data Action",
      "label": "Calculate buy/sell counts and USD volume for clicked cohort",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    },
    {
      "id": "EF1",
      "kind": "ExpectedFinding",
      "expectedOnly": true,
      "label": "Clicked cohort has synchronized net buying during the marked window",
      "explanation": "This is the target outcome the recommended calculation is expected to confirm or reject.",
      "evidenceSummary": "No evidence yet; it becomes evidence only if the follow-up investigation produces a real Finding node.",
      "reasoningRole": "Defines the evidence shape needed to complete the plan branch.",
      "recommendationType": "Evidence Completion",
      "status": "planned"
    }
  ],
  "edges": [
    { "source": "SRC_H3", "target": "RG1", "relation": "has_gap" },
    { "source": "RG1", "target": "RS1", "relation": "addressed_by" },
    { "source": "RS1", "target": "AA1", "relation": "contains" },
    { "source": "AA1", "target": "RI1", "relation": "contains" },
    { "source": "RI1", "target": "EF1", "relation": "expects" }
  ],
  "roots": ["SRC_H3"]
}
```

## Execution Boundary

For a full trace analysis, execute every Recommendation Plan Forest branch after generating the plan. If a branch cannot be executed, mark it as blocked with the exact blocker in `continued-investigation-report.md`.

After the plan is executed:

- Keep `ExpectedFinding` nodes in the plan artifacts.
- Create real `Finding` nodes only in a Reasoning Graph Patch.
- For every executed `Hypothesis Expansion` branch, explicitly resolve the proposed Hypothesis. Promote it into a new evidence-backed Hypothesis root when supported, or record a rejected, deferred, or unsupported outcome when not supported.
- Link actual evidence back to `ExpectedFinding`, `RecommendedInteraction`, `AnalyticActivity`, and `InvestigationStrategy` through `planRef`.

## Generating The Forest

```bash
python skills/user-trace-analysis/scripts/recommendation_plan_to_forest.py \
  TRACE/analysis-results/recommendation-plan-graph.json
```

By default, the script writes:

- `TRACE/analysis-results/recommendation-plan-forest.json`
- `TRACE/analysis-results/recommendation-plan-forest.md`

The generated forest uses `flowchart TD` because it is a top-down plan, unlike the bottom-up evidence support view used by `user-reasoning-forest.md`.

When plan nodes include `explanation`, `evidenceSummary`, or `reasoningRole`, the generated Markdown includes a `Node Detail Context` table. When `InvestigationStrategy` nodes include `targetContext`, `analyticContrast`, `searchConcepts`, `decisionCriteria`, or `falsificationCriteria`, it also includes a `Strategy Context` table so compact tree labels remain readable while the plan remains executable.

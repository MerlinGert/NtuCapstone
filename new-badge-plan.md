# New Badges For Agent-Created Analysis Cards

## Summary

Add transient `New` badges to visible LLM Analysis cards created during a Codex agent run. The badges are a UI overlay for user-study readability, not part of the reasoning graph schema. The graph remains the source of truth for reasoning content; the badge state only records which visible cards appeared during the latest eligible agent run.

## Core Behavior

- At the start of every specialized Codex agent run:
  - clear all existing `New` badges;
  - snapshot currently visible canonical card IDs in the LLM Analysis view;
  - suppress `New` badges for that run if no visible analysis cards exist yet, because the initial Full Analysis would otherwise mark almost every card as new.
- During the agent run:
  - keep polling graph artifacts as the LLM Analysis view already does;
  - after each successful graph projection, compare visible canonical IDs with the run-start snapshot;
  - add a `New` badge to any newly visible `Hypothesis` or `Finding` card.
- After the run completes:
  - keep `New` badges visible;
  - clear them only when the next agent run starts.
- Use `canonicalId || id`, not rendered tree instance ID, so duplicated cards share one `New` badge state.
- Track any newly visible card during a later run, regardless of whether it came from a user-derived graph update or an agent patch.

## Storage

Store badge state outside graph and patch artifacts:

```text
.maniscope-chat/sessions/{sessionId}/llm-analysis-ui-state.json
```

The file should contain:

```json
{
  "sessionId": "c3f26",
  "sessionMode": "specialized",
  "updatedAt": "2026-06-07T00:00:00Z",
  "activeRun": {
    "runId": "run-...",
    "startedAt": "2026-06-07T00:00:00Z",
    "suppressNewBadges": false,
    "baselineVisibleNodeIds": ["H1", "F2", "F3"]
  },
  "newNodeIds": {
    "F_AGENT_12": {
      "nodeKind": "Finding",
      "firstSeenAt": "2026-06-07T00:00:10Z",
      "runId": "run-..."
    }
  }
}
```

Only visible `Hypothesis` and `Finding` cards should be stored.

## Backend API

Add specialized-session endpoints:

- `GET /api/sessions/{sessionId}/analysis-ui-state`
- `PUT /api/sessions/{sessionId}/analysis-ui-state`
- `POST /api/sessions/{sessionId}/analysis-ui-state/run-start`

Backend validation should:

- reject invalid session IDs;
- require object payloads;
- require string node IDs;
- allow node kinds only `Hypothesis` and `Finding`;
- avoid validating IDs against the graph because graph files can change while the agent is writing.

The `run-start` endpoint should atomically clear old `newNodeIds`, store the run baseline, and set the suppression flag.

## Frontend Integration

### `CodexChatSidebar.vue`

- At the start of every specialized agent run, dispatch a `maniscope-codex-run-start` browser event.
- Include `sessionId`, `sessionMode`, `runId`, and `presetKind`.
- Do this for typed prompts, `Run Full Analysis`, and `Update Analysis`.

### `LlmAnalysisView.vue`

- Load `analysis-ui-state` alongside manifest and evaluation state.
- Listen for `maniscope-codex-run-start`.
- On run start:
  - compute current visible canonical `Hypothesis` and `Finding` IDs;
  - call the backend run-start endpoint;
  - update local UI state immediately.
- In `loadAnalysis()`, after projecting the display forest:
  - if there is an active run and `suppressNewBadges` is false, compare visible IDs with `baselineVisibleNodeIds`;
  - add unseen visible `Hypothesis` and `Finding` IDs to `newNodeIds`;
  - persist when new IDs are added.
- Pass `newNodeIds` into `ReasoningNodeCard`.
- Include `analysisUiState` in exported LLM Analysis JSON.
- Imported JSON mode should display restored `New` badges from `analysisUiState` but not sync them to the backend.

### `ReasoningNodeCard.vue`

- Add a quiet `New` pill in the metadata row for visible `Hypothesis` and `Finding` cards whose canonical ID exists in `newNodeIds`.
- Do not change card background color.

## Tests

- Backend:
  - missing UI state returns an empty payload;
  - `PUT` persists valid state;
  - malformed entries are rejected;
  - `run-start` clears old badges and stores baseline IDs.
- Frontend:
  - duplicate rendered nodes with the same canonical ID share `New` state;
  - initial graph creation with empty baseline suppresses badges;
  - later graph patching with an existing baseline marks newly visible cards;
  - export JSON includes `analysisUiState`.

## Manual Check

1. Open a session with completed LLM Analysis.
2. Start `Update Analysis`.
3. Confirm old `New` badges clear immediately.
4. Confirm new visible cards get `New` badges while the run is ongoing.
5. Refresh and confirm badges persist.
6. Start another agent run and confirm badges clear.

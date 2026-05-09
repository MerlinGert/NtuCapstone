---
name: maniscope-investigate
description: Use when Codex is working in the NtuCapstone ManiScope repository and needs to follow trace-analysis recommendations, inspect `insight-hunting/traces/*` artifacts, query local ACT/PNUT data, use `window.maniScopeMajorViewApi` from `docs/ui-analysis/major-view-render-api.md`, render Token Distribution, K-line, or Behavior Details views, export evidence images, and write clean investigation reports.
---

# ManiScope Investigate

## Overview

Use this skill to continue a ManiScope trace investigation from existing recommendations, combine raw data with rendered visual evidence, and write a report that separates actions, intermediate results, and findings.

Before deep work, read the repository `AGENTS.md` and the project API doc at `docs/ui-analysis/major-view-render-api.md`. For report layout and asset hygiene conventions, read `references/report-workflow.md`.

## Workflow

1. **Orient from existing artifacts**
   - Start in `/Users/zhiqiu/offline_code/research_ntu/NtuCapstone` unless the user gives another checkout.
   - Read the target trace folder, especially `analysis-report.md`, `trace-step-map.md`, `session.json`, and any existing follow-up report.
   - Extract the recommendation threads and convert them into concrete checks such as cohort overlap, transfer paths, sibling windows, post-window exits, or role comparisons.

2. **Check local services**
   - Reuse running services when possible. Verify with `curl` or browser navigation before starting new processes.
   - Backend convention: run from `front/server` with `uv`.
   - Frontend convention: run from `front` with `bun`.
   - If browser-side rendering is needed, use a browser automation surface that supports page JavaScript evaluation. The render API lives on `window.maniScopeMajorViewApi` after `CryptoVis` mounts.

3. **Gather raw evidence first**
   - Use raw trace data, local JSON/CSV data, or backend endpoints for exact counts, amounts, timestamps, and transfer relations.
   - Use `/api/user_behavior/sequences` to build `behaviorData` for Behavior Details renders.
   - Treat rendered images as visual evidence for timing, density, grouping, and qualitative role comparison. Do not infer exact event counts from dots when the row may be sampled.

4. **Render focused views**
   - Use `api.getRenderArgs(viewName, { width, height })` as the starting point, then set explicit render args.
   - For K-line windows, prefer `visibleTimeWindow` and `cardAlignment: 'visible_window'`; use `api.createKlineZoomTransform(args, window)` if constructing transforms directly.
   - For Behavior Details, pass full `behaviorData`, `selectedUser` or `selectedUsersList`, `visibleTimeWindow`, and `maxEventsPerUser`.
   - Use `strict: true` for Behavior Details captures that should fail instead of producing an empty prompt.
   - Save useful images under the target trace folder in a single assets directory with neutral evidence-oriented names.

5. **Analyze by role and time window**
   - Compare wallets inside the same time window before assigning role labels.
   - Separate direct evidence from inference. Direct evidence includes repeated cohort membership, exact transfers, exact trades, and endpoint-derived behavior sequences.
   - Use careful role labels: storage sink, directional accumulator, one-shot exit seller, later exit seller, high-frequency buy-sell actor, round-trip-like actor, or net-long high-frequency actor.
   - Recheck whether new candidates directly connect to the original clicked component before implying they are part of the same group.

6. **Write the report**
   - Put the report in the relevant trace folder, not generic UI-analysis docs, unless the user asks otherwise.
   - Structure as scope, actions taken, intermediate results, findings, and bottom line.
   - Keep implementation details, API debugging, and tool-validation commentary out of the investigation report unless the user explicitly asks for API testing.
   - Link only images that remain useful evidence, then remove unused generated assets.

## Validation

- Verify every report image link resolves.
- Verify no unused files remain in the report asset directory.
- Run `git diff --check` before committing.
- If code changed, run the appropriate build/check command before committing, using `bun` for frontend and `uv` for backend Python.

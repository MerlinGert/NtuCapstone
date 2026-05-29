# Instructions for Agents

## Project-Specific Defaults

Use these local ports for ManiScope development unless the user explicitly gives different ports:

- Frontend Vite app: `http://127.0.0.1:3099`
- Backend FastAPI API: `http://127.0.0.1:8099`
- Codex bridge: `http://127.0.0.1:8787`

Do not infer or probe `5173`, `3000`, or `8000` as the default ManiScope ports. Those values may appear in older reports or historical artifacts, but the current project convention is `3099`, `8099`, and `8787`.

Use these commands when starting local services:

```bash
# Terminal 1
cd front/server
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8099

# Terminal 2
cd front
bun run dev

# Terminal 3
cd front
bun run codex-bridge
```

The frontend dev server is configured in `front/vite.config.js` to bind `127.0.0.1:3099` and proxy `/api/*` to `http://127.0.0.1:8099`.

The backend direct-run default in `front/server/main.py` is `127.0.0.1:8099`, overridable with `MANISCOPE_BACKEND_HOST` and `MANISCOPE_BACKEND_PORT`.

The Codex bridge default in `front/codex-bridge/server.mjs` is `8787`, overridable with `CODEX_BRIDGE_PORT`. ManiScope chat agents run with model `gpt-5.5` and reasoning effort `xhigh` as code defaults in the bridge. Codex SDK network access is enabled by default for ManiScope chat agents; set `CODEX_NETWORK_ACCESS=false` before `bun run codex-bridge` only when a restricted offline run is required. The backend chat service defaults to `http://127.0.0.1:8787`, overridable with `CODEX_BRIDGE_URL`.

## Agent Visualization Helper

Every ManiScope chat session contains a managed helper file at `.maniscope-chat/sessions/{sessionId}/maniscope_visualization.py`. Use it when an agent needs to render visual evidence from Python. It exposes view-specific functions for Token Distribution, K-Line, and Behavior Details, including `get_token_distribution_args`, `render_token_distribution`, `get_kline_args`, `render_kline_chart`, `fetch_behavior_sequences`, `get_behavior_details_args`, and `render_behavior_details`.

The helper calls the Codex bridge on `http://127.0.0.1:8787`. The bridge opens an isolated Agent Workspace browser page at `http://127.0.0.1:3099/{sessionId}/agent`, invokes the frontend render API there, and saves generated PNGs to the session `artifacts/` folder. Prefer these helper functions over manual browser attachment or ad hoc JavaScript evaluation.

Agent rendering uses Playwright Chromium from the `front/` package. If the bridge reports a missing browser runtime, run `bunx playwright install chromium` from `front/`.

## Agent Trace Analysis Tools

Every ManiScope chat session also contains a managed trace-analysis bundle at `.maniscope-chat/sessions/{sessionId}/trace_analysis_tools/`. Use the session-local scripts when writing durable reasoning artifacts from Codex Chat:

```bash
cd .maniscope-chat/sessions/{sessionId}
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
```

The trace-analysis contract is graph-first: create `reasoning-graph.json` as the canonical source of truth, validate it with the session-local TypeScript validator, and add agent follow-up evidence through `reasoning-graph-patch*.json`. The frontend reads `reasoning-graph.json` plus all valid patch files and derives the display forest itself. Do not rely on generated forest JSON/Markdown as UI source data. User-authored claim annotations should appear as `Finding` nodes in `reasoning-graph.json`. Every `AnalyticQuestion` should have explicit mid-level answer Findings connected with `answers` edges from `Finding` to `AnalyticQuestion`; do not rely only on nearby activities or shared hypotheses to imply the answer. Main follow-up evidence should be added through `reasoning-graph-patch.json`; verified skeptical or counterevidence Findings should be added through `reasoning-graph-patch-skeptical.json`. In `reasoning-graph-patch-skeptical.json`, every added Finding must have an outgoing `refines` or `contradicts` edge. Do not encode skeptical caveats with only `supports` edges.

Every ManiScope chat session also contains a managed skeptical-review skill at `.maniscope-chat/sessions/{sessionId}/skills/maniscope-disconfirmation/SKILL.md`. Use it when spawning or instructing a subagent to search for negative evidence against major Hypotheses or high-level Findings. The skeptical subagent should return candidate negative Findings and suggested `contradicts`, `refines`, or Reasoning Gap links, never `supports` as the primary skeptical relation; the main agent must verify candidates before updating graph artifacts.

## Interaction Requirements

- Always ask for clarification if the task specification is ambiguous or a reasonable assumption would be risky.
- Give honest thoughts and suggestions before doing the task when the request has design, architecture, security, or workflow implications.
- Think proactively and provide recommendations that may help the user avoid future rework.

## Documentation Requirements

- When changing product behavior, user-facing behavior, public APIs, operational workflows, or development workflows, update the matching documentation in the same change set.

## Coding Requirements

### General Engineering Guidelines

- Always prioritize code quality and avoid bad software engineering practices.
- Do not rebuild the wheel. If a commonly used package or library already solves a feature or sub-feature well, use it unless the user explicitly asks you not to. If unsure, ask for clarification.
- Do not write trivial or low-value tests. Tests should protect meaningful behavior, contracts, regressions, security properties, or user-visible workflows.
- Keep track of file sizes. If a source file grows past the project's threshold, propose a refactor before it becomes a dumping ground. A reasonable default threshold is 1200 lines.


### Commit Requirements

- Always group changes into logical commits and never commit changes of different features or purposes in one commit.
- Before committing, verify the touched areas with the project's standard checks and targeted tests.

## Technical Requirements

- During iteration, avoid expensive full-suite lint, check, and format commands unless they are needed to understand or validate the current fix.
- Run targeted tests or checks during iteration when they are the fastest reliable way to validate the work.
- Run the project's required lint, check, format, and test commands before committing.
- No unsafe fixes should be applied even if a linter provides them. Reason about the code and preserve behavior.

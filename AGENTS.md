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

For the Docker development/user-study container, use `docker/maniscope-container`.
The container still uses internal ManiScope service ports `3099`, `8099`, and
`8787`, but publishes them to alternate host ports by default:

- Dev frontend: `http://127.0.0.1:3199`
- Study frontend: `http://127.0.0.1:3299`
- Backend: `http://127.0.0.1:8199`
- Codex bridge: `http://127.0.0.1:8877`

The Docker setup intentionally avoids host networking and does not use port
`8080`. Study mode serves production-built frontend assets through nginx on
container port `3099`, while `/data/*` and `/data2/*` are served directly from
the read-only `front/public/data*` bind mounts instead of copying the multi-GB
raw data into `front/dist`.

The frontend dev server is configured in `front/vite.config.js` to bind `127.0.0.1:3099` and proxy `/api/*` to `http://127.0.0.1:8099`.

The backend direct-run default in `front/server/main.py` is `127.0.0.1:8099`, overridable with `MANISCOPE_BACKEND_HOST` and `MANISCOPE_BACKEND_PORT`.

The Codex bridge default in `front/codex-bridge/server.mjs` is `8787`, overridable with `CODEX_BRIDGE_PORT`. ManiScope chat agents run with model `gpt-5.5`, reasoning effort `xhigh`, and service tier `fast` as code defaults in the bridge. The bridge launches each chat agent with `workspace-write` sandboxing, working directory set to that session root, network access enabled, ACT and PNUT raw-data directories as additional directories, and a repo-local uv cache at `.maniscope-chat/shared-uv-cache` granted through `sandbox_workspace_write.writable_roots`. Raw data is read-only by policy in the prompt; agent scripts, temp files, and outputs should stay inside the session root, preferably `artifacts/`. Agents can use plain `uv` and should not set `UV_CACHE_DIR` manually. The bridge checks for `uv`, `codex`, and one of `bun` or `npm` before listening. The backend chat service defaults to `http://127.0.0.1:8787`, overridable with `CODEX_BRIDGE_URL`.

## Baseline Agent Mode

Specialized sessions use `.maniscope-chat/sessions/{sessionId}` and routes such as `/{sessionId}/human` and `/{sessionId}/agent`. Baseline evaluation sessions use `.maniscope-chat/baseline-sessions/{sessionId}` and routes under `/base`.

- `/base` creates a new baseline session and redirects to `/base/{sessionId}`.
- `/base/{sessionId}` restores the baseline Human Workspace.
- `/base/{sessionId}/agent` is invalid and should redirect to `/base/{sessionId}`.
- Baseline APIs use `/api/base/sessions/...` and `/api/base/chat/...`.

Baseline sessions record user actions, annotations, screenshots, current state, chat history, and artifacts normally, but they intentionally remove specialized agent guidance. The baseline Codex prompt should describe the price-manipulation task and available raw data only. Do not include User Reasoning Forest, graph-first contracts, patches, trace-analysis skills, disconfirmation skills, subagents, Agent Workspace guidance, or specialized visualization-rendering methodology in the baseline prompt.

Baseline sessions receive `session-references/manual-for-baseline-agent.md`, a UI-focused manual that explains ManiScope views, visible evidence, trace files, and the capture-only baseline helper. It must not include specialized reasoning-graph methodology, patch contracts, subagent policy, disconfirmation skills, Agent Workspace guidance, or arbitrary render APIs.

Baseline UI should not expose the specialized right-panel LLM Analysis tab. Keep User Actions, Annotations, and Action Tree visible for baseline trace review.

## Session-Local Analysis Workspace

Every specialized and baseline ManiScope chat session is also seeded with `pyproject.toml`, `package.json`, and `.gitignore` in the session root. These files are templates for agent scratch work and are written only when missing, so agents may add Python packages with `uv add` or JavaScript/TypeScript packages with `bun add` without the backend overwriting their choices.

Run Python scripts from the session root with `uv run python script.py`. Run JavaScript or TypeScript scripts from the session root with `bun script.ts` or `bun script.js`. Keep durable evidence, reports, copied screenshots, and analysis outputs under the session `artifacts/` directory unless the user explicitly names another path.

## Agent Visualization Helper

Every ManiScope chat session contains a managed helper file at `.maniscope-chat/sessions/{sessionId}/maniscope_visualization.py`. Use it when an agent needs to render visual evidence from Python. It exposes view-specific functions for Token Distribution, K-Line, and Behavior Details, including `get_token_distribution_args`, `render_token_distribution`, `get_kline_args`, `render_kline_chart`, `fetch_behavior_sequences`, `get_behavior_details_args`, and `render_behavior_details`.

The helper calls the Codex bridge on `http://127.0.0.1:8787`. The bridge opens an isolated Agent Workspace browser page at `http://127.0.0.1:3099/{sessionId}/agent`, waits for the Agent Workspace visualization data to hydrate, invokes the frontend render API there, and saves generated PNGs to the session `artifacts/` folder. Prefer these helper functions over manual browser attachment or ad hoc JavaScript evaluation.

Agent rendering uses Playwright Chromium from the `front/` package. If the bridge reports a missing browser runtime, run `bunx playwright install chromium` from `front/`.

Baseline sessions do not receive `maniscope_visualization.py`. They receive `.maniscope-chat/baseline-sessions/{sessionId}/maniscope_baseline_views.py`, which is capture-only. It exposes `capture_current_token_distribution()`, `capture_current_kline_chart()`, `capture_current_behavior_details()`, `capture_current_views()`, and `artifact_path(name)`. These functions only copy latest synced Human Workspace screenshots from `current-state.json.majorViewScreenshots` into `artifacts/`; they must not accept or simulate parameters that change detector configs, selected users, time windows, scale, granularity, model outputs, or any other visualization state.


## Agent Trace Analysis Tools

Every ManiScope chat session also contains a managed trace-analysis bundle at `.maniscope-chat/sessions/{sessionId}/trace_analysis_tools/`. Use the session-local scripts when writing durable reasoning artifacts from Codex Chat:

```bash
cd .maniscope-chat/sessions/{sessionId}
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts
```

The trace-analysis contract is graph-first: create `reasoning-graph.json` as the canonical source of truth, validate it with the session-local TypeScript validator, and add agent follow-up evidence through `reasoning-graph-patch*.json`. During a full analysis, write and validate the base `reasoning-graph.json` immediately after reconstructing the user's reasoning, before recommendation planning, follow-up investigation, or patch writing, so the LLM Analysis tab can render the user reasoning forest while the agent continues working. Each specialized Codex Chat turn has a backend-owned closed trace window stored under `.maniscope-chat/sessions/{sessionId}/analysis-runs/{runId}.json`; use its `startAnchor` as the maximum trace boundary for that turn. For full analysis, set `reasoning-graph.json.analysisAnchor` exactly to the run `startAnchor`. For incremental analysis, set the patch `targetAnchor` to the run `startAnchor`. If the user keeps interacting while the agent works, those later trace records are out of scope and should be handled by a later Update Analysis run. The frontend reads `reasoning-graph.json` plus all valid patch files and derives the display forest itself. Do not rely on generated forest JSON/Markdown as UI source data. User-authored claim annotations should appear as `Finding` nodes in `reasoning-graph.json`. Every answerable `AnalyticQuestion` should have explicit mid-level answer Findings connected with `answers` edges from `Finding` to `AnalyticQuestion`; do not rely only on nearby activities or shared hypotheses to imply the answer. Unanswered `AnalyticQuestion`s are validator warnings, not graph errors, when the user trace does not contain an answer. Review those warnings and investigate central answerable questions through patches. Parent Findings should add synthesis, qualification, scope, contrast, uncertainty, or aggregation across evidence; if one concrete Finding is enough to answer an AnalyticQuestion or support, refine, or contradict a Hypothesis, connect it directly instead of creating a single-child rephrasing chain. Main follow-up evidence should be added through `reasoning-graph-patch.json`; verified skeptical or counterevidence Findings should be added through `reasoning-graph-patch-skeptical.json`. After a plan is produced, the main agent should prefer patch-producing subagents for independent planned branches so branch evidence can become patch files earlier. Before spawning each patch-producing subagent, the main agent must pre-allocate the `branchId`, exact filename `reasoning-graph-patch-subagent-<branchId>.json`, `runId`, node ID prefix, target graph IDs, and the same closed trace window. Subagent patches must not edit `reasoning-graph.json` or depend on other subagent patches, and the main agent remains responsible for validation, conflict resolution, and evidence verification. Incremental user-trace deltas should be added through `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json` with `patchType: "incremental"`, `baseAnchor`, and `targetAnchor`. Run `materialize` before incremental work when patches already exist so the agent can read `current-reasoning-graph.json` as a complete derived graph. Run `checkpoint` when the active deduplicated root-level patch count reaches 8 unless the user explicitly asks to preserve the unsquashed patch stack. In `reasoning-graph-patch-skeptical.json` or any patch with `patchType: "skeptical"`, every added Finding must have an outgoing `refines` or `contradicts` edge. Do not encode skeptical caveats with only `supports` edges.

For incremental-analysis testing, use `front/server/scripts/split_trace_fixture.py` to create a normal Part A import zip and a test-only Part B JSON. Import Part A through the ManiScope UI, run full analysis, then import Part B through the UI. Part B uses `isPatchTraceOnlyForTesting: true`, so the frontend appends the trace records, refreshes the Action Tree, suppresses the artificial `import_session` action, and syncs through the normal session path. Do not use a backend-only append route for this workflow.

Every ManiScope chat session also contains a managed skeptical-review skill at `.maniscope-chat/sessions/{sessionId}/skills/maniscope-disconfirmation/SKILL.md`. Use it when spawning or instructing a subagent to search for negative evidence against major Hypotheses or high-level Findings. The skeptical subagent should return candidate negative Findings and suggested `contradicts`, `refines`, or Reasoning Gap links, never `supports` as the primary skeptical relation. If the main agent explicitly assigns a branch patch contract, the skeptical subagent may write one `reasoning-graph-patch-subagent-<branchId>.json` file; the main agent must still verify candidates before relying on them in graph artifacts.

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

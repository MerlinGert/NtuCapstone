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

The Codex bridge default in `front/codex-bridge/server.mjs` is `8787`, overridable with `CODEX_BRIDGE_PORT`. The backend chat service defaults to `http://127.0.0.1:8787`, overridable with `CODEX_BRIDGE_URL`.

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

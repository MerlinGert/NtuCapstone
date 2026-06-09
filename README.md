# NtuCapstone

ManiScope is a visual analytics app for token-market investigation. The local app has three cooperating services:

- Vite frontend
- FastAPI backend
- Codex bridge

## Docker Container

Use `docker/maniscope-container` to run the project in either development mode or production-style user-study mode.

Default URLs:

- Dev frontend: `http://127.0.0.1:3199`
- Study frontend: `http://127.0.0.1:3299`
- Backend: `http://127.0.0.1:8199`
- Codex bridge: `http://127.0.0.1:8877`

Run from `docker/maniscope-container`:

```bash
just build
just up
just dev
just study
just down
```

Codex auth is kept in a Docker volume:

```bash
just codex-login
```

`just codex-login` uses the Codex device-code flow and stores auth in a Docker volume, so normal restarts and rebuilds keep the login.

The large raw-data directories under `front/public/data` and `front/public/data2` are mounted read-only. In study mode, nginx serves production-built frontend assets on container port `3099` and serves `/data/*` plus `/data2/*` directly from `front/public`, so the build does not copy the multi-GB raw data into `front/dist`.

See `docker/maniscope-container/README.md` for details and equivalent `docker compose` commands.

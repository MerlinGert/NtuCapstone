# ManiScope Container

This setup runs the ManiScope frontend, backend, and Codex bridge in one Docker image with two modes:

- `dev`: Vite dev server with FastAPI reload.
- `study`: production-built frontend served by nginx, with FastAPI and the Codex bridge.

The container uses published ports rather than host networking. It avoids port `8080`.

## Ports

Default host mappings:

- Dev frontend: `http://127.0.0.1:3199` -> container `3099`
- Study frontend: `http://127.0.0.1:3299` -> container `3099`
- Backend: `http://127.0.0.1:8199` -> container `8099`
- Codex bridge: `http://127.0.0.1:8877` -> container `8787`

Override them with environment variables before running `docker compose` or `just`:

```bash
MANISCOPE_DEV_FRONTEND_HOST_PORT=3199
MANISCOPE_STUDY_FRONTEND_HOST_PORT=3299
MANISCOPE_BACKEND_HOST_PORT=8199
MANISCOPE_BRIDGE_HOST_PORT=8877
```

## Commands

Run from this directory:

```bash
just build
just up
just dev
just study
just down
```

Equivalent Docker Compose commands:

```bash
docker compose --profile dev up -d maniscope-dev
docker compose --profile study up -d maniscope-study
docker compose --profile dev --profile study down
```

Do not run `dev` and `study` at the same time. They share backend and bridge host ports, dependency volumes, and `.maniscope-chat` state.

## Codex Login

Codex auth is stored in the named Docker volume mounted at `/home/maniscope/.codex`; it is not copied into the image.

```bash
just codex-login
```

This uses `codex login --device-auth`, so the CLI prints a device code and browser URL. The login persists in the `maniscope_codex` Docker volume across normal container restarts and rebuilds.

## Data Handling

The repository is bind-mounted into `/workspace/NtuCapstone`. The large raw-data directories are over-mounted read-only:

- `front/public/data`
- `front/public/data2`

Study mode builds the frontend with `MANISCOPE_DISABLE_PUBLIC_COPY=1`, so Vite does not copy the large public data into `front/dist`. nginx serves `/data/*` and `/data2/*` directly from `front/public`.

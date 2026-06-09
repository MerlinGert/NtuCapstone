# ManiScope Container

This setup runs the ManiScope frontend, backend, and Codex bridge in one Docker image with two modes:

- `dev`: Vite dev server with FastAPI reload.
- `study`: production-built frontend served by nginx, with FastAPI and the Codex bridge.

The container uses published ports rather than host networking. It avoids port `8080`.
It runs with Docker's seccomp and AppArmor profiles disabled so Codex's bubblewrap sandbox can create user namespaces and complete its mount setup inside the container. The container is not privileged and does not add extra Linux capabilities.

## Ports

Default host mappings:

- Dev frontend: `http://127.0.0.1:3199` -> container `3099`
- Study frontend: `0.0.0.0:3299` -> container `3099`
- Backend: `http://127.0.0.1:8199` -> container `8099`
- Codex bridge: `http://127.0.0.1:8877` -> container `8787`

Use `http://127.0.0.1:3299` locally, or `http://<LAN-IP>:3299` from another machine on the same LAN. Backend and bridge stay localhost-only.

Override them with environment variables before running `docker compose` or `just`:

```bash
MANISCOPE_DEV_FRONTEND_HOST_PORT=3199
MANISCOPE_STUDY_FRONTEND_HOST_BIND=0.0.0.0
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

## Codex Sandbox

Codex agents run with `workspace-write` sandboxing. Docker's default seccomp profile blocks the user-namespace operations used by that sandbox, and Docker's default AppArmor profile can block bubblewrap's mount propagation setup. These show up as errors such as:

```text
bwrap: No permissions to create a new namespace
bwrap: Failed to make / slave: Permission denied
```

The compose file sets `security_opt: seccomp=unconfined` and `security_opt: apparmor=unconfined` for the ManiScope app containers. This is the narrowest setting verified here to run Codex's bundled bubblewrap as the `maniscope` user while avoiding privileged mode and extra Linux capabilities.

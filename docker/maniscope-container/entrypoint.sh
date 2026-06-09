#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${MANISCOPE_REPO_ROOT:-/workspace/NtuCapstone}"
FRONT_DIR="${REPO_ROOT}/front"
SERVER_DIR="${FRONT_DIR}/server"
MODE="${MANISCOPE_MODE:-dev}"

prepare_owned_paths() {
  local maniscope_group
  maniscope_group="$(id -gn maniscope)"

  mkdir -p \
    "${FRONT_DIR}/node_modules" \
    "${FRONT_DIR}/dist" \
    "${SERVER_DIR}/.venv" \
    /home/maniscope/.codex \
    /home/maniscope/.cache/uv \
    /home/maniscope/.cache/ms-playwright \
    /home/maniscope/.bun/install/cache

  chown -R "maniscope:${maniscope_group}" \
    "${FRONT_DIR}/node_modules" \
    "${FRONT_DIR}/dist" \
    "${SERVER_DIR}/.venv" \
    /home/maniscope/.codex \
    /home/maniscope/.cache \
    /home/maniscope/.bun || true
}

if [ "$(id -u)" = "0" ]; then
  prepare_owned_paths
fi

export HOME=/home/maniscope
export PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:${HOME}/.bun/bin"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-${HOME}/.cache/ms-playwright}"

run_as_maniscope() {
  if [ "$(id -u)" = "0" ]; then
    gosu maniscope "$@"
  else
    "$@"
  fi
}

if [ ! -d "${FRONT_DIR}" ] || [ ! -d "${SERVER_DIR}" ]; then
  echo "Expected ManiScope repo at ${REPO_ROOT}; missing front/ or front/server/." >&2
  exit 1
fi

case "${MODE}" in
  dev|study)
    ;;
  *)
    echo "MANISCOPE_MODE must be 'dev' or 'study'; got '${MODE}'." >&2
    exit 1
    ;;
esac

cd "${FRONT_DIR}"
run_as_maniscope bun install --frozen-lockfile

cd "${SERVER_DIR}"
run_as_maniscope uv sync --frozen

cd "${FRONT_DIR}"
run_as_maniscope bunx playwright install chromium

if [ "${MODE}" = "study" ]; then
  run_as_maniscope env MANISCOPE_DISABLE_PUBLIC_COPY=1 bun run build
fi

exec /usr/bin/supervisord -c "/opt/maniscope/supervisord-${MODE}.conf"

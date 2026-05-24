from pathlib import Path


TOOL_VERSION = "2026-05-24.1"
TOOL_NAME = "maniscope_visualization.py"
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "session_tools" / TOOL_NAME
GIT_EXCLUDE_MARKER = "# ManiScope runtime session tools"
GIT_EXCLUDE_ENTRIES = [f"/{TOOL_NAME}"]


def ensure_session_tools(session_dir: Path, session_id: str) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    target_path = session_dir / TOOL_NAME
    content = _render_tool(session_id)
    if _needs_update(target_path, session_id):
        target_path.write_text(content, encoding="utf-8")
    _ensure_git_exclude(session_dir)


def _render_tool(session_id: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("__MANISCOPE_TOOL_VERSION__", TOOL_VERSION)
        .replace("__MANISCOPE_SESSION_ID__", session_id)
    )


def _needs_update(target_path: Path, session_id: str) -> bool:
    if not target_path.exists():
        return True
    try:
        existing = target_path.read_text(encoding="utf-8")
    except OSError:
        return True
    return f'TOOL_VERSION = "{TOOL_VERSION}"' not in existing or f'SESSION_ID = "{session_id}"' not in existing


def _ensure_git_exclude(session_dir: Path) -> None:
    git_dir = session_dir / ".git"
    if not git_dir.exists():
        return
    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    missing_entries = [entry for entry in GIT_EXCLUDE_ENTRIES if entry not in existing.splitlines()]
    if not missing_entries:
        return
    lines = []
    if existing and not existing.endswith("\n"):
        lines.append("")
    if GIT_EXCLUDE_MARKER not in existing.splitlines():
        lines.append(GIT_EXCLUDE_MARKER)
    lines.extend(missing_entries)
    lines.append("")
    with exclude_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

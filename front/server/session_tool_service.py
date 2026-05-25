import shutil
from pathlib import Path


TOOL_VERSION = "2026-05-25.2"
VISUALIZATION_TOOL_NAME = "maniscope_visualization.py"
TRACE_ANALYSIS_TOOLS_DIR_NAME = "trace_analysis_tools"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATE_PATH = BASE_DIR / "session_tools" / VISUALIZATION_TOOL_NAME
TRACE_ANALYSIS_SKILL_DIR = PROJECT_ROOT / "skills" / "user-trace-analysis"
TRACE_ANALYSIS_TOOL_FILES = [
    Path("scripts/reasoning_graph_to_forest.py"),
    Path("scripts/recommendation_plan_to_forest.py"),
    Path("scripts/apply_reasoning_graph_patch.py"),
    Path("references/reasoning-graph-format.md"),
    Path("references/recommendation-plan-format.md"),
    Path("references/reasoning-graph-patch-format.md"),
    Path("references/follow-up-investigation-execution.md"),
]
GIT_EXCLUDE_MARKER = "# ManiScope runtime session tools"
GIT_EXCLUDE_ENTRIES = [
    f"/{VISUALIZATION_TOOL_NAME}",
    f"/{TRACE_ANALYSIS_TOOLS_DIR_NAME}/",
]


def ensure_session_tools(session_dir: Path, session_id: str) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    target_path = session_dir / VISUALIZATION_TOOL_NAME
    content = _render_tool(session_id)
    if _visualization_tool_needs_update(target_path, session_id):
        target_path.write_text(content, encoding="utf-8")
    _ensure_trace_analysis_tools(session_dir)
    _ensure_git_exclude(session_dir)


def _render_tool(session_id: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("__MANISCOPE_TOOL_VERSION__", TOOL_VERSION)
        .replace("__MANISCOPE_SESSION_ID__", session_id)
    )


def _visualization_tool_needs_update(target_path: Path, session_id: str) -> bool:
    if not target_path.exists():
        return True
    try:
        existing = target_path.read_text(encoding="utf-8")
    except OSError:
        return True
    return f'TOOL_VERSION = "{TOOL_VERSION}"' not in existing or f'SESSION_ID = "{session_id}"' not in existing


def _ensure_trace_analysis_tools(session_dir: Path) -> None:
    tools_dir = session_dir / TRACE_ANALYSIS_TOOLS_DIR_NAME
    version_path = tools_dir / "TOOL_VERSION"
    if not _trace_analysis_tools_need_update(version_path):
        return

    if tools_dir.exists():
        shutil.rmtree(tools_dir)
    tools_dir.mkdir(parents=True, exist_ok=True)

    for relative_path in TRACE_ANALYSIS_TOOL_FILES:
        source_path = TRACE_ANALYSIS_SKILL_DIR / relative_path
        target_path = tools_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

    (tools_dir / "README.md").write_text(_trace_analysis_tools_readme(), encoding="utf-8")
    version_path.write_text(f"{TOOL_VERSION}\n", encoding="utf-8")


def _trace_analysis_tools_need_update(version_path: Path) -> bool:
    if not version_path.exists():
        return True
    try:
        existing = version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return True
    return existing != TOOL_VERSION


def _trace_analysis_tools_readme() -> str:
    return f"""# ManiScope Trace Analysis Tools

Managed by ManiScope. Do not edit this session-local copy by hand.

Tool version: `{TOOL_VERSION}`

Use these tools from the session directory when creating durable trace-analysis artifacts:

```bash
python3 trace_analysis_tools/scripts/reasoning_graph_to_forest.py artifacts/reasoning-graph.json
python3 trace_analysis_tools/scripts/recommendation_plan_to_forest.py artifacts/recommendation-plan-graph.json
python3 trace_analysis_tools/scripts/apply_reasoning_graph_patch.py \\
  artifacts/reasoning-graph.json \\
  artifacts/reasoning-graph-patch.json \\
  --out artifacts/augmented-reasoning-graph.json \\
  --forest-json-out artifacts/augmented-reasoning-forest.json \\
  --forest-md-out artifacts/augmented-reasoning-forest.md
```

The format references copied under `trace_analysis_tools/references/` define the required graph, plan, and patch schemas.
"""


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

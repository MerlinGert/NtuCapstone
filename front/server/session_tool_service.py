import shutil
from pathlib import Path


TOOL_VERSION = "2026-05-28.3"
VISUALIZATION_TOOL_NAME = "maniscope_visualization.py"
TRACE_ANALYSIS_TOOLS_DIR_NAME = "trace_analysis_tools"
REASONING_GRAPH_TS_DIR_NAME = "reasoning_graph"
SESSION_SKILLS_DIR_NAME = "skills"
DISCONFIRMATION_SKILL_NAME = "maniscope-disconfirmation"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATE_PATH = BASE_DIR / "session_tools" / VISUALIZATION_TOOL_NAME
TRACE_ANALYSIS_SKILL_DIR = PROJECT_ROOT / "skills" / "user-trace-analysis"
REASONING_GRAPH_TS_SOURCE_DIR = PROJECT_ROOT / "front" / "src" / "reasoning-graph"
DISCONFIRMATION_SKILL_DIR = PROJECT_ROOT / "skills" / DISCONFIRMATION_SKILL_NAME
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
    f"/{SESSION_SKILLS_DIR_NAME}/{DISCONFIRMATION_SKILL_NAME}/",
]


def ensure_session_tools(session_dir: Path, session_id: str) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    target_path = session_dir / VISUALIZATION_TOOL_NAME
    content = _render_tool(session_id)
    if _visualization_tool_needs_update(target_path, session_id):
        target_path.write_text(content, encoding="utf-8")
    _ensure_trace_analysis_tools(session_dir)
    _ensure_session_skills(session_dir)
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

    shutil.copytree(REASONING_GRAPH_TS_SOURCE_DIR, tools_dir / REASONING_GRAPH_TS_DIR_NAME)
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
bun trace_analysis_tools/reasoning_graph/cli.ts artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts
bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts
```

The TypeScript validator applies all `reasoning-graph-patch*.json` files in the same order as the frontend. Use `materialize` to write `current-reasoning-graph.json` as a complete reading aid before incremental analysis. Use `checkpoint` to archive the old base graph and active patches, then replace `reasoning-graph.json` with the materialized graph when the active deduplicated patch count reaches 8 or the user explicitly asks for compaction. The Python scripts remain available under `trace_analysis_tools/scripts/` for static Markdown/JSON exports when requested. The copied format references under `trace_analysis_tools/references/` define the graph, plan, and patch schemas.
"""


def _ensure_session_skills(session_dir: Path) -> None:
    skill_target = session_dir / SESSION_SKILLS_DIR_NAME / DISCONFIRMATION_SKILL_NAME
    version_path = skill_target / "TOOL_VERSION"
    if _session_skill_needs_update(version_path):
        if skill_target.exists():
            shutil.rmtree(skill_target)
        shutil.copytree(DISCONFIRMATION_SKILL_DIR, skill_target)
        version_path.write_text(f"{TOOL_VERSION}\n", encoding="utf-8")


def _session_skill_needs_update(version_path: Path) -> bool:
    if not version_path.exists():
        return True
    try:
        existing = version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return True
    return existing != TOOL_VERSION


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

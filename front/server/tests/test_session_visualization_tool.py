import importlib.util
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = (
    SERVER_DIR / "session_tools" / "maniscope_visualization.py"
)
BASELINE_TEMPLATE_PATH = SERVER_DIR / "session_tools" / "maniscope_baseline_views.py"
SESSION_TOOL_SERVICE_PATH = SERVER_DIR / "session_tool_service.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("maniscope_visualization_template", TEMPLATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_session_tool_service():
    spec = importlib.util.spec_from_file_location("session_tool_service_template", SESSION_TOOL_SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_baseline_tool_module():
    spec = importlib.util.spec_from_file_location("maniscope_baseline_views_template", BASELINE_TEMPLATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SessionVisualizationToolTests(unittest.TestCase):
    def test_render_token_distribution_converts_top_level_args_to_camel_case(self):
        module = load_tool_module()
        calls = []

        def fake_post_json(path, payload, *, timeout_seconds):
            calls.append((path, payload, timeout_seconds))
            return {
                "artifactPath": "/tmp/session/artifacts/token.png",
                "artifactUrl": "/api/sessions/abcde/artifacts/token.png",
                "artifactName": "token.png",
            }

        module._post_json = fake_post_json

        result = module.render_token_distribution(
            snapshot_data={"holders": []},
            entity_detection_results=[],
            link_detection_results=[],
            manipulation_detection_results=[],
            artifact_name="token.png",
        )

        self.assertEqual(calls[0][0], "/api/agent-browser/__MANISCOPE_SESSION_ID__/token-distribution/render")
        args = calls[0][1]["args"]
        self.assertIn("snapshotData", args)
        self.assertIn("entityDetectionResults", args)
        self.assertIn("linkDetectionResults", args)
        self.assertIn("manipulationDetectionResults", args)
        self.assertNotIn("snapshot_data", args)
        self.assertEqual(calls[0][1]["options"], {"quality": "full", "includeRawData": False})
        self.assertEqual(result["artifact_path"], "/tmp/session/artifacts/token.png")
        self.assertEqual(result["artifact_url"], "/api/sessions/abcde/artifacts/token.png")

    def test_get_kline_args_returns_pythonic_top_level_keys(self):
        module = load_tool_module()

        def fake_post_json(path, payload, *, timeout_seconds):
            self.assertEqual(path, "/api/agent-browser/__MANISCOPE_SESSION_ID__/kline/current-args")
            self.assertEqual(
                payload["options"],
                {
                    "width": 1600,
                    "height": 900,
                    "visibleTimeWindow": ["a", "b"],
                    "cardAlignment": "visible_window",
                },
            )
            return {
                "args": {
                    "currentCoin": "ACT",
                    "ohlcData": {"1h": []},
                    "manipulationResults": [],
                    "syncTargetTimeWindow": None,
                    "isSequentialTime": False,
                    "currentGranularity": "1h",
                    "zoomTransform": None,
                    "topCardsScrollLeft": 0,
                    "bottomCardsScrollLeft": 0,
                    "width": 1600,
                    "height": 900,
                }
            }

        module._post_json = fake_post_json

        args = module.get_kline_args(
            width=1600,
            height=900,
            visible_time_window=["a", "b"],
            card_alignment="visible_window",
        )

        self.assertEqual(args["current_coin"], "ACT")
        self.assertEqual(args["ohlc_data"], {"1h": []})
        self.assertEqual(args["visible_time_window"], ["a", "b"])
        self.assertEqual(args["card_alignment"], "visible_window")

    def test_artifact_path_rejects_directory_escape(self):
        module = load_tool_module()

        with self.assertRaises(ValueError):
            module.artifact_path("../outside.png")

    def test_ensure_session_tools_writes_managed_helper_and_git_exclude(self):
        service = load_session_tool_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            (session_dir / ".git" / "info").mkdir(parents=True)

            service.ensure_session_tools(session_dir, "abcde")

            pyproject = session_dir / "pyproject.toml"
            package_json = session_dir / "package.json"
            gitignore = session_dir / ".gitignore"
            self.assertTrue(pyproject.exists())
            self.assertTrue(package_json.exists())
            self.assertTrue(gitignore.exists())
            self.assertIn('name = "maniscope-specialized-session-abcde"', pyproject.read_text(encoding="utf-8"))
            self.assertIn('"name": "maniscope-specialized-session-abcde"', package_json.read_text(encoding="utf-8"))
            self.assertIn("node_modules/", gitignore.read_text(encoding="utf-8"))
            references_dir = session_dir / "session-references"
            self.assertEqual((references_dir / "TOOL_VERSION").read_text(encoding="utf-8").strip(), service.TOOL_VERSION)
            self.assertTrue((references_dir / "manual-for-agent.md").exists())
            self.assertFalse((references_dir / "user-manual.en.md").exists())
            self.assertTrue((references_dir / "major-view-render-api.md").exists())
            self.assertTrue((references_dir / "agent-analysis-playbook.md").exists())
            self.assertFalse((references_dir / "agent-analysis-l1-prompts.md").exists())
            self.assertTrue((references_dir / "agent-analysis-l2-prompts.md").exists())
            self.assertFalse((references_dir / "agent-analysis-prompts.md").exists())

            tool_path = session_dir / "maniscope_visualization.py"
            self.assertTrue(tool_path.exists())
            content = tool_path.read_text(encoding="utf-8")
            self.assertIn('SESSION_ID = "abcde"', content)
            self.assertIn(f'TOOL_VERSION = "{service.TOOL_VERSION}"', content)
            self.assertTrue((session_dir / "run_full_analysis.py").exists())
            self.assertTrue((session_dir / "run_incremental_analysis.py").exists())
            self.assertIn('SESSION_ID = "abcde"', (session_dir / "run_full_analysis.py").read_text(encoding="utf-8"))
            self.assertIn(
                f'TOOL_VERSION = "{service.TOOL_VERSION}"',
                (session_dir / "run_incremental_analysis.py").read_text(encoding="utf-8"),
            )

            exclude = (session_dir / ".git" / "info" / "exclude").read_text(encoding="utf-8")
            self.assertIn("/maniscope_visualization.py", exclude)
            self.assertIn("/run_full_analysis.py", exclude)
            self.assertIn("/run_incremental_analysis.py", exclude)
            self.assertIn("/session-references/", exclude)
            self.assertIn("/trace_analysis_tools/", exclude)
            self.assertIn("/skills/maniscope-disconfirmation/", exclude)
            self.assertIn("/pyproject.toml", exclude)
            self.assertIn("/package.json", exclude)
            self.assertIn("/.gitignore", exclude)
            self.assertIn("/node_modules/", exclude)

    def test_session_project_scaffold_does_not_overwrite_existing_files(self):
        service = load_session_tool_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            (session_dir / "pyproject.toml").write_text("[project]\nname = \"custom\"\n", encoding="utf-8")
            (session_dir / "package.json").write_text('{"name":"custom"}\n', encoding="utf-8")
            (session_dir / ".gitignore").write_text("custom-cache/\n", encoding="utf-8")

            service.ensure_session_tools(session_dir, "abcde")

            self.assertEqual((session_dir / "pyproject.toml").read_text(encoding="utf-8"), "[project]\nname = \"custom\"\n")
            self.assertEqual((session_dir / "package.json").read_text(encoding="utf-8"), '{"name":"custom"}\n')
            self.assertEqual((session_dir / ".gitignore").read_text(encoding="utf-8"), "custom-cache/\n")

    def test_ensure_session_tools_writes_trace_analysis_bundle(self):
        service = load_session_tool_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)

            service.ensure_session_tools(session_dir, "abcde")

            tools_dir = session_dir / "trace_analysis_tools"
            self.assertEqual((tools_dir / "TOOL_VERSION").read_text(encoding="utf-8").strip(), service.TOOL_VERSION)
            self.assertTrue((tools_dir / "README.md").exists())
            self.assertTrue((tools_dir / "scripts" / "reasoning_graph_to_forest.py").exists())
            self.assertTrue((tools_dir / "scripts" / "recommendation_plan_to_forest.py").exists())
            self.assertTrue((tools_dir / "scripts" / "apply_reasoning_graph_patch.py").exists())
            self.assertTrue((tools_dir / "references" / "reasoning-graph-format.md").exists())
            self.assertTrue((tools_dir / "references" / "recommendation-plan-format.md").exists())
            self.assertTrue((tools_dir / "references" / "reasoning-graph-patch-format.md").exists())
            self.assertTrue((tools_dir / "reasoning_graph" / "index.ts").exists())
            self.assertTrue((tools_dir / "reasoning_graph" / "cli.ts").exists())

    def test_ensure_session_tools_writes_disconfirmation_skill(self):
        service = load_session_tool_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)

            service.ensure_session_tools(session_dir, "abcde")

            skill_dir = session_dir / "skills" / "maniscope-disconfirmation"
            self.assertEqual((skill_dir / "TOOL_VERSION").read_text(encoding="utf-8").strip(), service.TOOL_VERSION)
            skill_content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("ManiScope Disconfirmation Review", skill_content)

    def test_ensure_baseline_session_tools_writes_only_capture_helper(self):
        service = load_session_tool_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            (session_dir / ".git" / "info").mkdir(parents=True)

            service.ensure_baseline_session_tools(session_dir, "abcde")

            tool_path = session_dir / "maniscope_baseline_views.py"
            self.assertTrue(tool_path.exists())
            pyproject = session_dir / "pyproject.toml"
            package_json = session_dir / "package.json"
            self.assertIn('name = "maniscope-baseline-session-abcde"', pyproject.read_text(encoding="utf-8"))
            self.assertIn('"name": "maniscope-baseline-session-abcde"', package_json.read_text(encoding="utf-8"))
            references_dir = session_dir / "session-references"
            self.assertEqual((references_dir / "TOOL_VERSION").read_text(encoding="utf-8").strip(), service.TOOL_VERSION)
            self.assertTrue((references_dir / "README.md").exists())
            self.assertTrue((references_dir / "manual-for-baseline-agent.md").exists())
            self.assertFalse((references_dir / "manual-for-agent.md").exists())
            self.assertFalse((references_dir / "user-manual.en.md").exists())
            self.assertFalse((references_dir / "major-view-render-api.md").exists())
            self.assertFalse((references_dir / "agent-analysis-playbook.md").exists())
            self.assertFalse((references_dir / "agent-analysis-l1-prompts.md").exists())
            self.assertFalse((references_dir / "agent-analysis-l2-prompts.md").exists())
            self.assertFalse((references_dir / "agent-analysis-prompts.md").exists())
            content = tool_path.read_text(encoding="utf-8")
            self.assertIn('SESSION_ID = "abcde"', content)
            self.assertIn(f'TOOL_VERSION = "{service.TOOL_VERSION}"', content)
            self.assertFalse((session_dir / "maniscope_visualization.py").exists())
            self.assertFalse((session_dir / "run_full_analysis.py").exists())
            self.assertFalse((session_dir / "run_incremental_analysis.py").exists())
            self.assertFalse((session_dir / "trace_analysis_tools").exists())
            self.assertFalse((session_dir / "skills" / "maniscope-disconfirmation").exists())

            exclude = (session_dir / ".git" / "info" / "exclude").read_text(encoding="utf-8")
            self.assertIn("/maniscope_baseline_views.py", exclude)
            self.assertIn("/session-references/", exclude)
            self.assertIn("/pyproject.toml", exclude)
            self.assertIn("/package.json", exclude)
            self.assertNotIn("/maniscope_visualization.py", exclude)

    def test_baseline_helper_copies_only_synced_current_screenshots(self):
        module = load_baseline_tool_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            images_dir = session_dir / "images"
            images_dir.mkdir()
            source = images_dir / "current-token-distribution.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\n")
            (session_dir / "current-state.json").write_text(
                '{"majorViewScreenshots":{"token_distribution":"images/current-token-distribution.png"}}',
                encoding="utf-8",
            )
            module.SESSION_DIR = session_dir
            module.ARTIFACTS_DIR = session_dir / "artifacts"
            module.SESSION_ID = "abcde"

            result = module.capture_current_token_distribution()

            artifact_path = Path(result["artifact_path"])
            self.assertTrue(artifact_path.exists())
            self.assertEqual(artifact_path.read_bytes(), source.read_bytes())
            self.assertEqual(result["artifact_url"], f"/api/base/sessions/abcde/artifacts/{artifact_path.name}")
            with self.assertRaises(ValueError):
                module.artifact_path("../escape.png")


if __name__ == "__main__":
    unittest.main()

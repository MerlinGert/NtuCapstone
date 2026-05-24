import importlib.util
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = (
    SERVER_DIR / "session_tools" / "maniscope_visualization.py"
)
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

            tool_path = session_dir / "maniscope_visualization.py"
            self.assertTrue(tool_path.exists())
            content = tool_path.read_text(encoding="utf-8")
            self.assertIn('SESSION_ID = "abcde"', content)
            self.assertIn(f'TOOL_VERSION = "{service.TOOL_VERSION}"', content)

            exclude = (session_dir / ".git" / "info" / "exclude").read_text(encoding="utf-8")
            self.assertIn("/maniscope_visualization.py", exclude)


if __name__ == "__main__":
    unittest.main()

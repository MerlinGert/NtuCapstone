import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
CHAT_SESSION_SERVICE_PATH = SERVER_DIR / "chat_session_service.py"
CODEX_CHAT_SERVICE_PATH = SERVER_DIR / "codex_chat_service.py"


def load_module(path: Path, name: str):
    sys.path.insert(0, str(SERVER_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(SERVER_DIR))
        except ValueError:
            pass


class BaselineSessionTests(unittest.TestCase):
    def test_baseline_and_specialized_sessions_use_separate_roots(self):
        module = load_module(CHAT_SESSION_SERVICE_PATH, "chat_session_service_baseline_test")
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            original_baseline_sessions_dir = module.BASELINE_SESSIONS_DIR
            original_token_hex = module.secrets.token_hex
            original_commit = module._commit_trace_history
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                module.BASELINE_SESSIONS_DIR = Path(tmp_dir) / "baseline-sessions"
                module.secrets.token_hex = lambda _size: "abcde0"
                module._commit_trace_history = lambda **_kwargs: {"committed": False}

                specialized = module._create_session({}, session_mode="specialized")
                baseline = module._create_session({}, session_mode="baseline")

                self.assertEqual(specialized["sessionId"], "abcde")
                self.assertEqual(baseline["sessionId"], "abcde")
                self.assertTrue((module.SESSIONS_DIR / "abcde" / "maniscope_visualization.py").exists())
                self.assertTrue((module.BASELINE_SESSIONS_DIR / "abcde" / "maniscope_baseline_views.py").exists())
                self.assertFalse((module.BASELINE_SESSIONS_DIR / "abcde" / "maniscope_visualization.py").exists())
                self.assertEqual(
                    module._read_json(module.BASELINE_SESSIONS_DIR / "abcde" / "session-meta.json")["sessionMode"],
                    "baseline",
                )
            finally:
                module.SESSIONS_DIR = original_sessions_dir
                module.BASELINE_SESSIONS_DIR = original_baseline_sessions_dir
                module.secrets.token_hex = original_token_hex
                module._commit_trace_history = original_commit

    def test_baseline_workspace_rejects_agent_role(self):
        module = load_module(CHAT_SESSION_SERVICE_PATH, "chat_session_service_baseline_role_test")
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_baseline_sessions_dir = module.BASELINE_SESSIONS_DIR
            original_commit = module._commit_trace_history
            try:
                module.BASELINE_SESSIONS_DIR = Path(tmp_dir) / "baseline-sessions"
                module._commit_trace_history = lambda **_kwargs: {"committed": False}
                module._ensure_session("abcde", session_mode="baseline")

                with self.assertRaises(Exception) as error:
                    module._workspace_payload("abcde", "agent", session_mode="baseline")
                self.assertEqual(error.exception.status_code, 400)
            finally:
                module.BASELINE_SESSIONS_DIR = original_baseline_sessions_dir
                module._commit_trace_history = original_commit

    def test_baseline_sync_writes_trace_under_baseline_root(self):
        module = load_module(CHAT_SESSION_SERVICE_PATH, "chat_session_service_baseline_sync_test")
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            original_baseline_sessions_dir = module.BASELINE_SESSIONS_DIR
            original_commit = module._commit_trace_history
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                module.BASELINE_SESSIONS_DIR = Path(tmp_dir) / "baseline-sessions"
                module._commit_trace_history = lambda **_kwargs: {"committed": False}
                body = {
                    "coin": "ACT",
                    "userActionSequence": [{"actionType": "click", "sourceView": "token_distribution"}],
                    "annotationRecords": [{"id": 1, "sourceView": "token_distribution"}],
                    "currentState": {
                        "majorViewScreenshots": {
                            "token_distribution": "data:image/png;base64,iVBORw0KGgo=",
                        },
                    },
                }

                result = module._sync_session("abcde", body, session_mode="baseline")
                baseline_dir = module.BASELINE_SESSIONS_DIR / "abcde"

                self.assertEqual(result["actionCount"], 1)
                self.assertTrue((baseline_dir / "live-session.json").exists())
                self.assertTrue((baseline_dir / "current-state.json").exists())
                self.assertTrue((baseline_dir / "workspaces" / "human" / "current-state.json").exists())
                self.assertFalse((module.SESSIONS_DIR / "abcde").exists())
            finally:
                module.SESSIONS_DIR = original_sessions_dir
                module.BASELINE_SESSIONS_DIR = original_baseline_sessions_dir
                module._commit_trace_history = original_commit

    def test_baseline_chat_history_uses_baseline_root_and_urls(self):
        module = load_module(CODEX_CHAT_SERVICE_PATH, "codex_chat_service_baseline_test")
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            original_baseline_sessions_dir = module.BASELINE_SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                module.BASELINE_SESSIONS_DIR = Path(tmp_dir) / "baseline-sessions"
                session_dir = module._session_dir("abcde", session_mode="baseline")
                artifact = session_dir / "artifacts" / "report.md"
                artifact.write_text("# Report\n", encoding="utf-8")

                module._save_chat_history(
                    "abcde",
                    {
                        "threadKey": "trace-analysis",
                        "messages": [
                            {
                                "role": "assistant",
                                "content": f"[report]({artifact})",
                                "artifacts": [],
                            }
                        ],
                    },
                    session_mode="baseline",
                )
                history = module._get_chat_history("abcde", session_mode="baseline")

                self.assertIn("/api/base/sessions/abcde/artifacts/report.md", history["messages"][0]["content"])
                self.assertFalse((module.SESSIONS_DIR / "abcde").exists())
            finally:
                module.SESSIONS_DIR = original_sessions_dir
                module.BASELINE_SESSIONS_DIR = original_baseline_sessions_dir


if __name__ == "__main__":
    unittest.main()

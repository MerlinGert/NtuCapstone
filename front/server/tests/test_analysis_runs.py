import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
CHAT_SESSION_SERVICE_PATH = SERVER_DIR / "chat_session_service.py"


def load_chat_session_service():
    sys.path.insert(0, str(SERVER_DIR))
    try:
        spec = importlib.util.spec_from_file_location("chat_session_service_analysis_runs", CHAT_SESSION_SERVICE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(SERVER_DIR))
        except ValueError:
            pass


def live_session(anchor):
    return {
        "exportFormat": "live-session",
        "sessionId": anchor["sessionId"],
        "traceRevision": anchor["traceRevision"],
        "userActionSequence": [{"id": str(index)} for index in range(anchor["actionCount"])],
        "annotationRecords": [{"id": str(index)} for index in range(anchor["annotationCount"])],
        "traceAnchor": anchor,
    }


class AnalysisRunTests(unittest.TestCase):
    def configure_temp_sessions(self, module, tmp_dir):
        module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
        module.ensure_session_tools = lambda _session_dir, _session_id: None
        module._commit_trace_history = lambda **_kwargs: None

    def test_start_analysis_run_stores_current_trace_anchor(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            start_anchor = {
                "sessionId": "abcde",
                "traceRevision": 7,
                "actionCount": 16,
                "annotationCount": 12,
                "lastActionId": "15",
                "lastAnnotationId": "12",
                "traceDigest": "sha256:start",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(start_anchor)), encoding="utf-8")

            payload = module.start_analysis_run("abcde", {"presetKind": "full_analysis"})

            self.assertEqual(payload["mode"], "full_analysis")
            self.assertEqual(payload["presetKind"], "full_analysis")
            self.assertEqual(payload["status"], "running")
            self.assertEqual(payload["startAnchor"], start_anchor)
            saved_path = session_dir / "analysis-runs" / f"{payload['runId']}.json"
            self.assertTrue(saved_path.exists())
            self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8"))["startAnchor"], start_anchor)

    def test_finish_analysis_run_records_end_anchor_and_trace_advanced(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            start_anchor = {
                "sessionId": "abcde",
                "traceRevision": 7,
                "actionCount": 16,
                "annotationCount": 12,
                "traceDigest": "sha256:start",
            }
            end_anchor = {
                "sessionId": "abcde",
                "traceRevision": 9,
                "actionCount": 26,
                "annotationCount": 18,
                "traceDigest": "sha256:end",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(start_anchor)), encoding="utf-8")
            started = module.start_analysis_run("abcde", {"mode": "incremental_analysis", "presetKind": "update_analysis"})
            run_path = session_dir / "analysis-runs" / f"{started['runId']}.json"

            (session_dir / "live-session.json").write_text(json.dumps(live_session(end_anchor)), encoding="utf-8")
            self.assertEqual(json.loads(run_path.read_text(encoding="utf-8"))["startAnchor"], start_anchor)

            finished = module.finish_analysis_run("abcde", started["runId"], "completed")

            self.assertEqual(finished["status"], "completed")
            self.assertEqual(finished["startAnchor"], start_anchor)
            self.assertEqual(finished["endAnchor"], end_anchor)
            self.assertTrue(finished["traceAdvanced"])

    def test_finish_analysis_run_without_trace_change_does_not_mark_advanced(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            anchor = {
                "sessionId": "abcde",
                "traceRevision": 3,
                "actionCount": 4,
                "annotationCount": 2,
                "traceDigest": "sha256:same",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(anchor)), encoding="utf-8")
            started = module.start_analysis_run("abcde", {"presetKind": ""})

            finished = module.finish_analysis_run("abcde", started["runId"], "stopped")

            self.assertEqual(finished["status"], "stopped")
            self.assertEqual(finished["endAnchor"], anchor)
            self.assertFalse(finished["traceAdvanced"])


if __name__ == "__main__":
    unittest.main()

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
        module._post_bridge_analysis_task_start = lambda _session_id, _task: {"status": "running"}
        module._post_bridge_analysis_task_stop = lambda _session_id, _task_id: {"stopped": True}

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

    def test_start_full_analysis_task_creates_run_and_task_with_fixed_anchor(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            anchor = {
                "sessionId": "abcde",
                "traceRevision": 5,
                "actionCount": 9,
                "annotationCount": 4,
                "traceDigest": "sha256:task",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(anchor)), encoding="utf-8")
            calls = []
            module._post_bridge_analysis_task_start = lambda session_id, task: calls.append((session_id, task)) or {
                "status": "running",
                "threadId": "thread-1",
            }

            task = module.start_full_analysis_task("abcde", {})

            self.assertEqual(task["mode"], "full")
            self.assertEqual(task["status"], "running")
            self.assertEqual(task["startAnchor"], anchor)
            self.assertEqual(task["threadId"], "thread-1")
            self.assertTrue((session_dir / "analysis-tasks" / f"{task['taskId']}.json").exists())
            self.assertTrue((session_dir / "analysis-runs" / f"{task['runId']}.json").exists())
            self.assertEqual(calls[0][0], "abcde")
            self.assertEqual(calls[0][1]["startAnchor"], anchor)

    def test_start_analysis_task_reuses_existing_run(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            anchor = {
                "sessionId": "abcde",
                "traceRevision": 7,
                "actionCount": 16,
                "annotationCount": 12,
                "traceDigest": "sha256:reuse",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(anchor)), encoding="utf-8")
            run = module.start_analysis_run("abcde", {"mode": "incremental_analysis", "presetKind": "update_analysis"})

            task = module.start_incremental_analysis_task("abcde", {"runId": run["runId"]})

            self.assertEqual(task["runId"], run["runId"])
            self.assertEqual(task["mode"], "incremental")
            self.assertEqual(task["startAnchor"], run["startAnchor"])
            run_files = list((session_dir / "analysis-runs").glob("*.json"))
            self.assertEqual(len(run_files), 1)

    def test_analysis_task_status_list_and_stop(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            anchor = {
                "sessionId": "abcde",
                "traceRevision": 1,
                "actionCount": 2,
                "annotationCount": 1,
                "traceDigest": "sha256:stop",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(anchor)), encoding="utf-8")
            task = module.start_full_analysis_task("abcde", {})

            listed = module.list_analysis_tasks("abcde")
            fetched = module.get_analysis_task("abcde", task["taskId"])
            stopped = module.stop_analysis_task("abcde", task["taskId"])

            self.assertEqual(listed["tasks"][0]["taskId"], task["taskId"])
            self.assertEqual(fetched["taskId"], task["taskId"])
            self.assertEqual(stopped["status"], "stopped")
            run_payload = json.loads((session_dir / "analysis-runs" / f"{task['runId']}.json").read_text(encoding="utf-8"))
            self.assertEqual(run_payload["status"], "stopped")

    def test_analysis_task_event_completion_finalizes_run(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)
            session_dir = module.SESSIONS_DIR / "abcde"
            session_dir.mkdir(parents=True)
            anchor = {
                "sessionId": "abcde",
                "traceRevision": 2,
                "actionCount": 3,
                "annotationCount": 1,
                "traceDigest": "sha256:complete",
            }
            (session_dir / "live-session.json").write_text(json.dumps(live_session(anchor)), encoding="utf-8")
            task = module.start_full_analysis_task("abcde", {})

            updated = module.update_analysis_task_event(
                "abcde",
                task["taskId"],
                {"status": "completed", "threadId": "thread-2", "artifacts": [{"path": "artifacts/reasoning-graph.json"}]},
            )

            self.assertEqual(updated["status"], "completed")
            self.assertEqual(updated["threadId"], "thread-2")
            self.assertEqual(updated["artifacts"][0]["path"], "artifacts/reasoning-graph.json")
            run_payload = json.loads((session_dir / "analysis-runs" / f"{task['runId']}.json").read_text(encoding="utf-8"))
            self.assertEqual(run_payload["status"], "completed")


if __name__ == "__main__":
    unittest.main()

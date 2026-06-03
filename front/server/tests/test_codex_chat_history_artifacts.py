import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
CODEX_CHAT_SERVICE_PATH = SERVER_DIR / "codex_chat_service.py"


def load_codex_chat_service():
    spec = importlib.util.spec_from_file_location("codex_chat_service_template", CODEX_CHAT_SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CodexChatHistoryArtifactTests(unittest.TestCase):
    def configure_temp_sessions(self, module, temp_dir):
        module.SESSIONS_DIR = Path(temp_dir) / "sessions"
        module.BASELINE_SESSIONS_DIR = Path(temp_dir) / "baseline-sessions"
        module.ensure_session_tools = lambda _session_dir, _session_id: None
        module.ensure_baseline_session_tools = lambda _session_dir, _session_id: None

    def test_history_load_rewrites_existing_absolute_artifact_links(self):
        module = load_codex_chat_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "abcde"
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir(parents=True)
            report_path = artifacts_dir / "full-trace-analysis-report.md"
            graph_path = artifacts_dir / "reasoning-graph-patch.json"
            report_path.write_text("# Report\n", encoding="utf-8")
            graph_path.write_text('{"nodes":[]}\n', encoding="utf-8")

            message = {
                "role": "assistant",
                "content": "\n".join(
                    [
                        f"- [report]({report_path})",
                        f"- [patch]({graph_path})",
                        "`/Users/example/.maniscope-chat/sessions/abcde/artifacts/ignored.json`",
                    ]
                ),
                "artifacts": [],
            }

            normalized = module._normalize_history_message_artifacts("abcde", session_dir, message)

            self.assertIn("[report](/api/sessions/abcde/artifacts/full-trace-analysis-report.md)", normalized["content"])
            self.assertIn("[patch](/api/sessions/abcde/artifacts/reasoning-graph-patch.json)", normalized["content"])
            self.assertIn("`/Users/example/.maniscope-chat/sessions/abcde/artifacts/ignored.json`", normalized["content"])
            self.assertEqual(
                sorted(artifact["kind"] for artifact in normalized["artifacts"]),
                ["json", "markdown"],
            )

    def test_stream_history_turn_stores_visible_preset_and_attachment_metadata(self):
        module = load_codex_chat_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            self.configure_temp_sessions(module, temp_dir)
            messages, assistant_message, _counters = module._start_stream_history_turn(
                "abcde",
                "trace-analysis",
                "specialized",
                {
                    "displayMessage": "Run full analysis",
                    "presetKind": "full_analysis",
                    "attachments": [
                        {
                            "id": "image-1",
                            "name": "view.png",
                            "type": "image/png",
                            "dataUrl": "data:image/png;base64,SHOULD_NOT_PERSIST",
                        }
                    ],
                },
                "please run a pass of full trace analysis with a subagent for finding counter-evidence.",
            )

            history_path = module._history_path("abcde", "trace-analysis")
            saved = json.loads(history_path.read_text(encoding="utf-8"))

            self.assertEqual(messages[-2]["content"], "Run full analysis")
            self.assertEqual(messages[-2]["presetKind"], "full_analysis")
            self.assertEqual(messages[-2]["attachments"], [{"id": "image-1", "name": "view.png", "type": "image/png"}])
            self.assertNotIn("dataUrl", json.dumps(messages[-2]))
            self.assertEqual(assistant_message["turnState"], "streaming")
            self.assertEqual(saved["messages"][-2]["content"], "Run full analysis")

    def test_chat_events_update_inline_timeline_parts(self):
        module = load_codex_chat_service()

        assistant_message = {
            "content": "",
            "activity": [],
            "artifacts": [],
            "parts": [],
            "turnState": "streaming",
        }
        counters = {"activity": 1, "part": 1}

        module._apply_chat_event_to_history(
            {"type": "agent_message", "text": "I am checking the trace."},
            assistant_message,
            counters,
        )
        module._apply_chat_event_to_history(
            {"type": "status", "eventId": "s1", "category": "trace", "title": "Inspecting trace"},
            assistant_message,
            counters,
        )
        module._apply_chat_event_to_history(
            {
                "type": "status",
                "eventId": "s1",
                "category": "trace",
                "title": "Inspecting trace",
                "detail": "Trace loaded.",
            },
            assistant_message,
            counters,
        )
        module._apply_chat_event_to_history(
            {
                "type": "artifact",
                "artifact": {
                    "id": "report",
                    "title": "report.md",
                    "kind": "markdown",
                    "path": "artifacts/report.md",
                },
            },
            assistant_message,
            counters,
        )
        module._apply_chat_event_to_history(
            {
                "type": "artifact",
                "artifact": {
                    "id": "report",
                    "title": "report-updated.md",
                    "kind": "markdown",
                    "path": "artifacts/report.md",
                },
            },
            assistant_message,
            counters,
        )

        self.assertEqual(assistant_message["content"], "I am checking the trace.")
        self.assertEqual([part["type"] for part in assistant_message["parts"]], ["markdown", "activity_sequence", "artifact"])
        self.assertEqual(len(assistant_message["parts"][1]["activities"]), 1)
        self.assertEqual(assistant_message["parts"][1]["activities"][0]["detail"], "Trace loaded.")
        self.assertEqual(len(assistant_message["artifacts"]), 1)
        self.assertEqual(assistant_message["parts"][2]["artifact"]["title"], "report-updated.md")

    def test_stream_persists_bridge_events_incrementally(self):
        module = load_codex_chat_service()

        class FakeResponse:
            status_code = 200
            reason = "OK"
            text = ""
            encoding = "utf-8"

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

            def iter_lines(self, chunk_size=1, decode_unicode=True):
                yield 'data: {"type":"agent_message","text":"First result."}'
                yield ""
                yield 'data: {"type":"artifact","artifact":{"id":"graph","title":"reasoning-graph.json","kind":"json","path":"artifacts/reasoning-graph.json"}}'
                yield ""
                yield 'data: {"type":"done","threadId":"thread-1"}'
                yield ""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.configure_temp_sessions(module, temp_dir)
            messages, assistant_message, counters = module._start_stream_history_turn(
                "abcde",
                "trace-analysis",
                "specialized",
                {"displayMessage": "Analyze", "attachments": []},
                "Analyze",
            )
            module.requests.post = lambda *_args, **_kwargs: FakeResponse()

            list(
                module._stream_codex_response(
                    "abcde",
                    {"message": "Analyze"},
                    history_messages=messages,
                    assistant_message=assistant_message,
                    history_counters=counters,
                    thread_key="trace-analysis",
                    session_mode="specialized",
                )
            )

            saved = json.loads(module._history_path("abcde", "trace-analysis").read_text(encoding="utf-8"))
            saved_assistant = saved["messages"][-1]
            self.assertEqual(saved_assistant["content"], "First result.")
            self.assertEqual(saved_assistant["turnState"], "completed")
            self.assertEqual(saved_assistant["threadId"], "thread-1")
            self.assertEqual(saved_assistant["artifacts"][0]["title"], "reasoning-graph.json")
            self.assertEqual([part["type"] for part in saved_assistant["parts"]], ["markdown", "artifact", "activity_sequence"])

    def test_stream_without_completion_marks_partial_turn_interrupted(self):
        module = load_codex_chat_service()

        class FakeResponse:
            status_code = 200
            reason = "OK"
            text = ""
            encoding = "utf-8"

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

            def iter_lines(self, chunk_size=1, decode_unicode=True):
                yield 'data: {"type":"agent_message","text":"Partial result."}'
                yield ""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.configure_temp_sessions(module, temp_dir)
            messages, assistant_message, counters = module._start_stream_history_turn(
                "abcde",
                "trace-analysis",
                "specialized",
                {"displayMessage": "Analyze", "attachments": []},
                "Analyze",
            )
            module.requests.post = lambda *_args, **_kwargs: FakeResponse()

            list(
                module._stream_codex_response(
                    "abcde",
                    {"message": "Analyze"},
                    history_messages=messages,
                    assistant_message=assistant_message,
                    history_counters=counters,
                    thread_key="trace-analysis",
                    session_mode="specialized",
                )
            )

            saved = json.loads(module._history_path("abcde", "trace-analysis").read_text(encoding="utf-8"))
            saved_assistant = saved["messages"][-1]
            self.assertEqual(saved_assistant["content"], "Partial result.")
            self.assertEqual(saved_assistant["turnState"], "interrupted")
            self.assertIn("Turn interrupted", [activity["title"] for activity in saved_assistant["activity"]])


if __name__ == "__main__":
    unittest.main()

import importlib.util
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


if __name__ == "__main__":
    unittest.main()

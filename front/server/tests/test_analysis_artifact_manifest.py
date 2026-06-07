import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
CHAT_SESSION_SERVICE_PATH = SERVER_DIR / "chat_session_service.py"


def load_chat_session_service():
    sys.path.insert(0, str(SERVER_DIR))
    try:
        spec = importlib.util.spec_from_file_location("chat_session_service_template", CHAT_SESSION_SERVICE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(SERVER_DIR))
        except ValueError:
            pass


class AnalysisArtifactManifestTests(unittest.TestCase):
    def configure_temp_sessions(self, module, tmp_dir):
        module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
        module.ensure_session_tools = lambda _session_dir, _session_id: None
        module._commit_trace_history = lambda **_kwargs: None

    def test_manifest_returns_graph_and_ordered_patches(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()

            graph_path = artifacts_dir / "reasoning-graph.json"
            forest_path = artifacts_dir / "user-reasoning-forest.json"
            old_patch_path = artifacts_dir / "reasoning-graph-patch-001.json"
            current_patch_path = artifacts_dir / "reasoning-graph-patch.json"
            skeptical_patch_path = artifacts_dir / "reasoning-graph-patch-skeptical.json"
            incremental_patch_path = artifacts_dir / "reasoning-graph-patch-incremental-10-11.json"
            graph_path.write_text('{"version":1}\n', encoding="utf-8")
            forest_path.write_text('{"trees":[]}\n', encoding="utf-8")
            old_patch_path.write_text('{"runId":"old","operations":[]}\n', encoding="utf-8")
            current_patch_path.write_text('{"runId":"current","operations":[]}\n', encoding="utf-8")
            skeptical_patch_path.write_text('{"runId":"skeptical","operations":[]}\n', encoding="utf-8")
            incremental_patch_path.write_text('{"runId":"incremental","operations":[]}\n', encoding="utf-8")
            os.utime(old_patch_path, (100, 100))
            os.utime(current_patch_path, (200, 200))
            os.utime(skeptical_patch_path, (300, 300))
            os.utime(incremental_patch_path, (400, 400))

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertEqual(
                manifest["current"]["reasoningGraph"]["name"],
                "reasoning-graph.json",
            )
            self.assertEqual(
                [item["name"] for item in manifest["current"]["patches"]],
                [
                    "reasoning-graph-patch.json",
                    "reasoning-graph-patch-001.json",
                    "reasoning-graph-patch-skeptical.json",
                    "reasoning-graph-patch-incremental-10-11.json",
                ],
            )
            self.assertEqual(
                manifest["current"]["patches"][0]["url"],
                "/api/sessions/abcde/artifacts/reasoning-graph-patch.json",
            )
            self.assertEqual(
                manifest["current"]["userReasoningForest"]["name"],
                "user-reasoning-forest.json",
            )
            self.assertEqual(len(manifest["artifacts"]), 6)

    def test_manifest_deduplicates_patch_run_ids(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()

            canonical_path = artifacts_dir / "reasoning-graph-patch.json"
            hashed_path = artifacts_dir / "reasoning-graph-patch-001-abcdef0123456789.json"
            canonical_path.write_text('{"runId":"same","operations":[]}\n', encoding="utf-8")
            hashed_path.write_text('{"runId":"same","operations":[]}\n', encoding="utf-8")
            os.utime(canonical_path, (100, 100))
            os.utime(hashed_path, (200, 200))

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertEqual(
                [item["name"] for item in manifest["current"]["patches"]],
                ["reasoning-graph-patch.json"],
            )

    def test_manifest_falls_back_to_numbered_patch(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()
            (artifacts_dir / "reasoning-graph-patch-001.json").write_text(
                '{"runId":"numbered","operations":[]}\n',
                encoding="utf-8",
            )

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertIsNone(manifest["current"]["userReasoningForest"])
            self.assertEqual(
                [item["name"] for item in manifest["current"]["patches"]],
                ["reasoning-graph-patch-001.json"],
            )

    def test_nested_artifact_file_can_be_served(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                artifact_path = (
                    module.SESSIONS_DIR
                    / "abcde"
                    / "artifacts"
                    / "continued-investigation-assets"
                    / "kline.png"
                )
                artifact_path.parent.mkdir(parents=True)
                artifact_path.write_bytes(b"\x89PNG\r\n\x1a\n")

                response = module.get_session_artifact(
                    "abcde",
                    "continued-investigation-assets/kline.png",
                )

                self.assertEqual(Path(response.path).resolve(), artifact_path.resolve())
            finally:
                module.SESSIONS_DIR = original_sessions_dir

    def test_analysis_evaluations_get_returns_empty_payload_when_missing(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            payload = module.get_analysis_evaluations("abcde")

            self.assertEqual(payload["sessionId"], "abcde")
            self.assertEqual(payload["sessionMode"], "specialized")
            self.assertIsNone(payload["updatedAt"])
            self.assertEqual(payload["evaluations"], {})

    def test_analysis_evaluations_put_writes_valid_payload(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            payload = module.put_analysis_evaluations(
                "abcde",
                {
                    "evaluations": {
                        "H1": {
                            "checked": True,
                            "nodeKind": "Hypothesis",
                            "updatedAt": "2026-06-07T00:00:00Z",
                        },
                        "F23": {
                            "checked": True,
                            "nodeKind": "Finding",
                            "updatedAt": "2026-06-07T00:00:01Z",
                        },
                    },
                },
            )

            self.assertEqual(payload["evaluations"]["H1"]["nodeKind"], "Hypothesis")
            self.assertTrue(payload["evaluations"]["F23"]["checked"])
            saved_path = module.SESSIONS_DIR / "abcde" / "llm-analysis-evaluations.json"
            self.assertTrue(saved_path.exists())
            reloaded = module.get_analysis_evaluations("abcde")
            self.assertEqual(sorted(reloaded["evaluations"]), ["F23", "H1"])

    def test_analysis_evaluations_reject_malformed_payload(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            with self.assertRaises(Exception) as missing_checked:
                module.put_analysis_evaluations("abcde", {"evaluations": {"H1": {"nodeKind": "Hypothesis"}}})
            self.assertEqual(missing_checked.exception.status_code, 400)

            with self.assertRaises(Exception) as unsupported_field:
                module.put_analysis_evaluations(
                    "abcde",
                    {
                        "evaluations": {
                            "H1": {
                                "checked": True,
                                "nodeKind": "Hypothesis",
                                "comment": "not supported",
                            }
                        }
                    },
                )
            self.assertEqual(unsupported_field.exception.status_code, 400)

    def test_analysis_evaluations_invalid_session_id_is_rejected(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            with self.assertRaises(Exception) as error:
                module.put_analysis_evaluations("not-valid", {"evaluations": {}})
            self.assertEqual(error.exception.status_code, 400)

    def test_analysis_export_writes_session_artifact_with_stable_name(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            result = module.write_analysis_export(
                "abcde",
                {
                    "payload": {
                        "exportVersion": 1,
                        "exportFormat": "maniscope-llm-analysis-json",
                        "sessionId": "abcde",
                        "displayForest": [],
                    }
                },
            )

            self.assertTrue(result["name"].startswith("maniscope-llm-analysis-abcde-"))
            self.assertTrue(result["name"].endswith(".json"))
            self.assertEqual(result["url"], f"/api/sessions/abcde/artifacts/{result['name']}")
            saved_path = module.SESSIONS_DIR / "abcde" / "artifacts" / result["name"]
            self.assertTrue(saved_path.exists())

    def test_analysis_export_rejects_malformed_payload(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.configure_temp_sessions(module, tmp_dir)

            with self.assertRaises(Exception) as error:
                module.write_analysis_export("abcde", {"payload": {"exportFormat": "wrong"}})
            self.assertEqual(error.exception.status_code, 400)

    def test_session_image_file_can_be_served(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                image_path = module.SESSIONS_DIR / "abcde" / "images" / "action-0001.png"
                image_path.parent.mkdir(parents=True)
                image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

                response = module.get_session_image("abcde", "action-0001.png")

                self.assertEqual(Path(response.path).resolve(), image_path.resolve())
            finally:
                module.SESSIONS_DIR = original_sessions_dir

    def test_session_file_routes_reject_escapes(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                session_dir = module.SESSIONS_DIR / "abcde"
                (session_dir / "artifacts").mkdir(parents=True)
                outside_path = Path(tmp_dir) / "outside.png"
                outside_path.write_bytes(b"\x89PNG\r\n\x1a\n")

                with self.assertRaises(Exception) as artifact_error:
                    module.get_session_artifact("abcde", "../outside.png")
                self.assertEqual(artifact_error.exception.status_code, 400)

                symlink_path = session_dir / "artifacts" / "escape.png"
                symlink_path.symlink_to(outside_path)
                with self.assertRaises(Exception) as symlink_error:
                    module.get_session_artifact("abcde", "escape.png")
                self.assertEqual(symlink_error.exception.status_code, 400)
            finally:
                module.SESSIONS_DIR = original_sessions_dir


if __name__ == "__main__":
    unittest.main()

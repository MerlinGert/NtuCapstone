import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_debug_append_import_is_disabled_by_default(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                with patch.dict(os.environ, {module.DEBUG_TRACE_API_ENV: ""}, clear=False):
                    with self.assertRaises(Exception) as error:
                        module.append_imported_trace_slice("abcde", {"userActionSequence": []})
                self.assertEqual(error.exception.status_code, 404)
            finally:
                module.SESSIONS_DIR = original_sessions_dir

    def test_debug_append_import_preserves_trace_slice_and_returns_anchors(self):
        module = load_chat_session_service()
        png_data_url = "data:image/png;base64,iVBORw0KGgo="
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sessions_dir = module.SESSIONS_DIR
            try:
                module.SESSIONS_DIR = Path(tmp_dir) / "sessions"
                with patch.dict(os.environ, {module.DEBUG_TRACE_API_ENV: "true"}, clear=False):
                    result = module.append_imported_trace_slice(
                        "abcde",
                        {
                            "coin": "ACT",
                            "userActionSequence": [
                                {
                                    "actionType": "select_card",
                                    "sourceView": "kline_chart",
                                    "sourceSnapshot": [
                                        {"viewName": "kline_chart", "dataUrl": png_data_url}
                                    ],
                                }
                            ],
                            "annotationRecords": [
                                {
                                    "id": 7,
                                    "sourceView": "behavior_details",
                                    "sketchDataUrl": png_data_url,
                                }
                            ],
                            "images": {
                                "images/imported-extra.png": png_data_url,
                            },
                            "currentState": {"selectedUsers": ["wallet"]},
                        },
                    )

                live_session = module._read_json(module.SESSIONS_DIR / "abcde" / "live-session.json")
                self.assertEqual(result["beforeAnchor"]["traceRevision"], 0)
                self.assertEqual(result["afterAnchor"]["traceRevision"], 1)
                self.assertEqual(result["afterAnchor"]["actionCount"], 1)
                self.assertEqual(result["afterAnchor"]["annotationCount"], 1)
                self.assertEqual(live_session["traceAnchor"], result["afterAnchor"])
                self.assertEqual(live_session["userActionSequence"][0]["sourceSnapshot"][0]["imagePath"], "images/action-0001-source-kline_chart-01.png")
                self.assertEqual(live_session["annotationRecords"][0]["sketchImagePath"], "images/annotation-0007-behavior_details.png")
                self.assertTrue((module.SESSIONS_DIR / "abcde" / "images" / "imported-extra.png").exists())
                self.assertTrue(result["git"]["committed"])
            finally:
                module.SESSIONS_DIR = original_sessions_dir


if __name__ == "__main__":
    unittest.main()

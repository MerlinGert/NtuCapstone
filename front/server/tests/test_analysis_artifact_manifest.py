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
    def test_manifest_selects_current_reasoning_artifacts(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()

            forest_path = artifacts_dir / "user-reasoning-forest.json"
            old_patch_path = artifacts_dir / "reasoning-graph-patch-001.json"
            current_patch_path = artifacts_dir / "reasoning-graph-patch.json"
            forest_path.write_text('{"trees":[]}\n', encoding="utf-8")
            old_patch_path.write_text('{"operations":[]}\n', encoding="utf-8")
            current_patch_path.write_text('{"operations":[]}\n', encoding="utf-8")
            os.utime(old_patch_path, (100, 100))
            os.utime(current_patch_path, (200, 200))

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertEqual(
                manifest["current"]["userReasoningForest"]["name"],
                "user-reasoning-forest.json",
            )
            self.assertEqual(
                manifest["current"]["reasoningGraphPatch"]["name"],
                "reasoning-graph-patch.json",
            )
            self.assertEqual(
                manifest["current"]["reasoningGraphPatch"]["url"],
                "/api/sessions/abcde/artifacts/reasoning-graph-patch.json",
            )
            self.assertEqual(len(manifest["artifacts"]), 3)

    def test_manifest_prefers_canonical_patch_over_hashed_copy(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()

            canonical_path = artifacts_dir / "reasoning-graph-patch.json"
            hashed_path = artifacts_dir / "reasoning-graph-patch-001-abcdef0123456789.json"
            canonical_path.write_text('{"operations":[]}\n', encoding="utf-8")
            hashed_path.write_text('{"operations":[]}\n', encoding="utf-8")
            os.utime(canonical_path, (100, 100))
            os.utime(hashed_path, (200, 200))

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertEqual(
                manifest["current"]["reasoningGraphPatch"]["name"],
                "reasoning-graph-patch.json",
            )

    def test_manifest_falls_back_to_numbered_patch(self):
        module = load_chat_session_service()
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_dir = Path(tmp_dir)
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir()
            (artifacts_dir / "reasoning-graph-patch-001.json").write_text(
                '{"operations":[]}\n',
                encoding="utf-8",
            )

            manifest = module._analysis_artifact_manifest("abcde", session_dir)

            self.assertIsNone(manifest["current"]["userReasoningForest"])
            self.assertEqual(
                manifest["current"]["reasoningGraphPatch"]["name"],
                "reasoning-graph-patch-001.json",
            )


if __name__ == "__main__":
    unittest.main()

import json
import os
import unittest
from pathlib import Path


class LoopArtifactTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.projects_dir = self.repo_root / "projects"
        self.project = os.getenv("SD_TEST_PROJECT", "sd_test")
        self.artifacts_dir = self.projects_dir / self.project / "artifacts"
        self.loops_path = self.artifacts_dir / "loops.json"

    def test_loop_artifact_exists(self) -> None:
        self.assertTrue(
            self.loops_path.exists(),
            f"loops.json not found for project '{self.project}' at {self.loops_path}",
        )

    def test_loop_artifact_structure(self) -> None:
        data = json.loads(self.loops_path.read_text(encoding="utf-8"))
        for key in ("balancing", "reinforcing", "undetermined", "notes"):
            self.assertIn(key, data, f"Missing key '{key}' in loops.json")

        for loop_key in ("balancing", "reinforcing", "undetermined"):
            loops = data.get(loop_key, [])
            self.assertIsInstance(loops, list, f"'{loop_key}' should be a list")
            for loop in loops:
                self.assertIsInstance(loop, dict)
                for required in ("id", "variables", "edges", "length", "negative_edges", "polarity", "description"):
                    self.assertIn(required, loop, f"Loop missing '{required}' in section '{loop_key}'")
                self.assertIsInstance(loop["variables"], list)
                self.assertIsInstance(loop["edges"], list)
                for edge in loop["edges"]:
                    self.assertIsInstance(edge, dict)
                    for edge_key in ("from_var", "to_var", "relationship"):
                        self.assertIn(edge_key, edge, f"Edge missing '{edge_key}' in loop '{loop.get('id')}'")


if __name__ == "__main__":
    unittest.main()

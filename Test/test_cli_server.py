import json
import os
import sys
import unittest
from pathlib import Path


class CLIServerTests(unittest.TestCase):
    def test_cli_run_and_knowledge_validate(self):
        """Invoke CLI commands in a subprocess to ensure entry points work."""
        import subprocess

        # Run knowledge validate for sd_test
        out = subprocess.run(
            [sys.executable, "-m", "src.sd_model.cli", "knowledge", "validate", "--project", "sd_test"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(out.returncode, 0, msg=out.stderr)
        self.assertIn("Knowledge validation", out.stdout)

        # Run the pipeline without patch to keep it quick
        out = subprocess.run(
            [sys.executable, "-m", "src.sd_model.cli", "run", "--project", "sd_test"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(out.returncode, 0, msg=out.stderr)
        data = json.loads(out.stdout)
        for k in ["parsed", "loops", "connections", "theory_validation", "improvements"]:
            self.assertTrue(Path(data[k]).exists(), f"missing artifact: {k}")

    def test_flask_server_routes(self):
        """Create Flask app and hit routes with the test client."""
        from src.sd_model.server import create_app

        app = create_app()
        client = app.test_client()

        # Index
        r = client.get("/")
        self.assertEqual(r.status_code, 200)

        # Projects list includes sd_test
        r = client.get("/projects")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("projects", data)
        self.assertIn("sd_test", data["projects"])

        # Run pipeline endpoint
        r = client.get("/run-pipeline/sd_test")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("artifacts", data)

        # Artifacts listing and fetch
        r = client.get("/artifacts/sd_test")
        self.assertEqual(r.status_code, 200)
        listing = r.get_json()
        self.assertIn("files", listing)
        self.assertTrue(any(f.endswith(".json") for f in listing["files"]))

        # Fetch first artifact
        first = listing["files"][0]
        r = client.get(f"/artifacts/sd_test/{first}")
        self.assertEqual(r.status_code, 200)


class StreamlitSmokeTest(unittest.TestCase):
    def test_streamlit_import_and_projects(self):
        import src.sd_model.ui_streamlit as ui

        projects = ui.list_projects()
        self.assertIn("sd_test", projects)


if __name__ == "__main__":
    unittest.main()


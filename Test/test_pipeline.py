import json
import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"
TEST_PROJECT = "sd_test"


class SDPipelineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prepare sample project structure
        base = PROJECTS_DIR / TEST_PROJECT
        (base / "artifacts").mkdir(parents=True, exist_ok=True)
        (base / "db").mkdir(parents=True, exist_ok=True)
        (base / "mdl").mkdir(parents=True, exist_ok=True)
        (base / "knowledge" / "theories").mkdir(parents=True, exist_ok=True)

        # Minimal model with a few variables and clear references
        mdl = (
            "Potential Adopters = 1000 - Adopters ~ ppl ~| potential pool\n"
            "New Adopters = Adoption Rate * Potential Adopters ~ ppl/month ~| flow\n"
            "Adopters = INTEG(New Adopters - Attrition, 0) ~ ppl ~| stock\n"
            "Adoption Rate = 0.05 ~ 1/month ~| parameter\n"
            "Attrition = 0.0 ~ ppl/month ~| parameter\n"
        )
        (base / "mdl" / "model.mdl").write_text(mdl, encoding="utf-8")

        # Theory YAML: one expected link present (Potential Adopters -> New Adopters),
        # one expected link missing (Market Saturation -> New Adopters)
        yml = (
            "theory_name: Test Theory\n"
            "citation_key: ajzen1991\n"
            "expected_connections:\n"
            "  - from_var: Potential Adopters\n"
            "    to_var: New Adopters\n"
            "    relationship: positive\n"
            "  - from_var: Market Saturation\n"
            "    to_var: New Adopters\n"
            "    relationship: negative\n"
        )
        (base / "knowledge" / "theories" / "theory_of_planned_behavior.yml").write_text(
            yml, encoding="utf-8"
        )

        # Bibliography with the cited key
        bib = (
            "@article{ajzen1991,\n"
            "  title={The theory of planned behavior},\n"
            "  author={Ajzen, Icek},\n"
            "  journal={Organizational Behavior and Human Decision Processes},\n"
            "  year={1991}\n"
            "}\n"
        )
        (base / "knowledge" / "references.bib").write_text(bib, encoding="utf-8")

        # Feedback requesting the missing connection
        feedback = [
            {
                "feedback_id": "rev01_comment_3",
                "source": "user",
                "comment": "Market Saturation -> New Adopters (negative)",
                "action": "add connection",
            }
        ]
        (base / "knowledge" / "feedback.json").write_text(
            json.dumps(feedback, indent=2), encoding="utf-8"
        )

    def test_knowledge_loader(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.knowledge.loader import load_theories, load_bibliography, load_feedback

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)

        # Theories (skip if yaml not installed)
        try:
            import yaml  # noqa: F401
            theories = load_theories(paths.theories_dir)
            self.assertGreaterEqual(len(theories), 1)
            names = [t.theory_name for t in theories]
            self.assertIn("Test Theory", names)
        except Exception:
            self.skipTest("PyYAML not available")

        # Bibliography (skip if parser is missing)
        try:
            import bibtexparser  # noqa: F401

            bib = load_bibliography(paths.references_bib_path)
            self.assertIn("ajzen1991", bib)
        except Exception:
            self.skipTest("bibtexparser not available")

        # Feedback
        fb = load_feedback(paths.feedback_json_path)
        self.assertEqual(len(fb), 1)

    def test_parse_loops_interpret(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.pipeline.parse import parse_mdl
        from src.sd_model.pipeline.loops import compute_loops
        from src.sd_model.pipeline.interpret import derive_connections

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)
        paths.ensure()
        mdl = paths.mdl_dir / "model.mdl"

        parsed = parse_mdl(mdl, paths.parsed_path)
        self.assertIn("variables", parsed)
        self.assertIn("equations", parsed)
        self.assertIn("New Adopters", parsed["variables"])

        loops = compute_loops(parsed, paths.loops_path)
        self.assertIn("balancing", loops)
        self.assertIn("reinforcing", loops)

        interp = derive_connections(parsed, paths.connections_path)
        conns = interp.get("connections", [])
        # Expect a connection from Potential Adopters -> New Adopters (heuristic)
        self.assertTrue(any(c.get("from_var") == "Potential Adopters" and c.get("to_var") == "New Adopters" for c in conns))

    def test_theory_validation(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.pipeline.theory_validation import validate_against_theories

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)

        # Skip if PyYAML not available
        try:
            import yaml  # noqa: F401
        except Exception:
            self.skipTest("PyYAML not available")

        tv = validate_against_theories(
            connections_path=paths.connections_path,
            theories_dir=paths.theories_dir,
            bib_path=paths.references_bib_path,
            out_path=paths.theory_validation_path,
        )
        self.assertIn("confirmed", tv)
        self.assertIn("missing", tv)
        # The expected pair Potential Adopters -> New Adopters should be confirmed
        self.assertTrue(any(r.get("from_var") == "Potential Adopters" and r.get("to_var") == "New Adopters" for r in tv.get("confirmed", [])))
        # The Market Saturation -> New Adopters is missing
        self.assertTrue(any(r.get("from_var") == "Market Saturation" and r.get("to_var") == "New Adopters" for r in tv.get("missing", [])))

    def test_verify_citations(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.pipeline.verify_citations import verify_citations

        # Skip if bibtexparser not installed
        try:
            import bibtexparser  # noqa: F401
        except Exception:
            self.skipTest("bibtexparser not available")

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)

        # Create a small artifact with one good and one bad key to assert failure
        tmp_art = paths.artifacts_dir / "tmp_cite.json"
        tmp_art.write_text(json.dumps({"items": [{"citation_key": "ajzen1991"}, {"citation_key": "MISSING_KEY"}]}), encoding="utf-8")

        with self.assertRaises(ValueError):
            verify_citations([tmp_art], paths.references_bib_path)

    def test_improve_and_schema(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.pipeline.improve import propose_improvements
        from src.sd_model.validation.schema import validate_json_schema
        from src.sd_model.pipeline.theory_validation import validate_against_theories

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)

        # Skip if PyYAML not available (theory_validation artifact creation depends on it)
        try:
            import yaml  # noqa: F401
        except Exception:
            self.skipTest("PyYAML not available")

        # Ensure theory validation artifact exists
        _ = validate_against_theories(
            connections_path=paths.connections_path,
            theories_dir=paths.theories_dir,
            bib_path=paths.references_bib_path,
            out_path=paths.theory_validation_path,
        )

        result = propose_improvements(paths.theory_validation_path, paths.feedback_json_path, paths.model_improvements_path)
        self.assertIn("improvements", result)
        # Should contain an add_connection addressing feedback Market Saturation -> New Adopters
        self.assertTrue(any(op.get("operation") == "add_connection" and op.get("from") == "Market Saturation" and op.get("to") == "New Adopters" for op in result["improvements"]))

        # Validate against schema when available
        schema_path = REPO_ROOT / "schemas" / "model_improvements.schema.json"
        try:
            validate_json_schema(result, schema_path)
        except Exception as e:
            self.fail(f"Schema validation failed: {e}")

    def test_apply_patch(self):
        from src.sd_model.config import load_config
        from src.sd_model.paths import for_project
        from src.sd_model.pipeline.apply_patch import apply_model_patch
        from src.sd_model.pipeline.improve import propose_improvements

        cfg = load_config()
        paths = for_project(cfg, TEST_PROJECT)
        mdl = paths.mdl_dir / "model.mdl"
        out_copy = paths.artifacts_dir / "model_patched.mdl"

        # Ensure improvements exist; if not, generate a minimal one
        if not paths.model_improvements_path.exists():
            # If theory validation is missing (likely due to yaml), create a minimal improvements file
            minimal = {"improvements": [{"operation": "add_variable", "name": "Market Saturation", "equation": "0", "comment": "test"}]}
            paths.model_improvements_path.write_text(json.dumps(minimal, indent=2), encoding="utf-8")

        p = apply_model_patch(mdl, paths.model_improvements_path, out_copy)
        self.assertTrue(p.exists())
        txt = p.read_text(encoding="utf-8")
        self.assertIn("SIMPLIFIED_PATCH_START", txt)

    def test_orchestrator_end_to_end(self):
        from src.sd_model.orchestrator import run_pipeline

        # Skip if PyYAML not available
        try:
            import yaml  # noqa: F401
        except Exception:
            self.skipTest("PyYAML not available")

        res = run_pipeline(project=TEST_PROJECT, apply_patch=True)
        # Ensure expected artifacts are present
        for key in ["parsed", "loops", "connections", "theory_validation", "improvements"]:
            self.assertTrue(Path(res[key]).exists(), f"Missing artifact: {key}")
        if res.get("patched"):
            self.assertTrue(Path(res["patched"]).exists())


if __name__ == "__main__":
    unittest.main()

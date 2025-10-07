import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"


class OptionalProjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Project without feedback.json
        nofb = PROJECTS_DIR / "sd_test_nofb"
        (nofb / "artifacts").mkdir(parents=True, exist_ok=True)
        (nofb / "db").mkdir(parents=True, exist_ok=True)
        (nofb / "mdl").mkdir(parents=True, exist_ok=True)
        (nofb / "knowledge" / "theories").mkdir(parents=True, exist_ok=True)

        mdl = (
            "Potential Adopters = 10 - Adopters ~ ppl ~| potential\n"
            "New Adopters = Adoption Rate * Potential Adopters ~ ppl/month ~| flow\n"
            "Adopters = INTEG(New Adopters, 0) ~ ppl ~| stock\n"
            "Adoption Rate = 0.1 ~ 1/month ~| param\n"
        )
        (nofb / "mdl" / "model.mdl").write_text(mdl, encoding="utf-8")
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
        (nofb / "knowledge" / "theories" / "theory.yml").write_text(yml, encoding="utf-8")
        bib = (
            "@article{ajzen1991,\n  title={The theory of planned behavior},\n  author={Ajzen, Icek},\n  year={1991}\n}\n"
        )
        (nofb / "knowledge" / "references.bib").write_text(bib, encoding="utf-8")

        # Project without references.bib
        nobib = PROJECTS_DIR / "sd_test_nobib"
        (nobib / "artifacts").mkdir(parents=True, exist_ok=True)
        (nobib / "db").mkdir(parents=True, exist_ok=True)
        (nobib / "mdl").mkdir(parents=True, exist_ok=True)
        (nobib / "knowledge" / "theories").mkdir(parents=True, exist_ok=True)
        (nobib / "mdl" / "model.mdl").write_text(mdl, encoding="utf-8")
        (nobib / "knowledge" / "theories" / "theory.yml").write_text(yml, encoding="utf-8")
        # no references.bib on purpose

    def test_orchestrator_without_feedback(self):
        from src.sd_model.orchestrator import run_pipeline

        res = run_pipeline(project="sd_test_nofb", apply_patch=False)
        self.assertTrue(Path(res["theory_validation"]).exists())
        self.assertTrue(Path(res["improvements"]).exists())
        # Improvements should contain at least one connection derived from theory gaps
        data = json.loads(Path(res["improvements"]).read_text(encoding="utf-8"))
        self.assertTrue(any(op.get("operation") == "add_connection" for op in data.get("improvements", [])))

    def test_orchestrator_without_bibliography(self):
        from src.sd_model.orchestrator import run_pipeline

        # Pipeline should run and create artifacts; bibliography_loaded should be false
        res = run_pipeline(project="sd_test_nobib", apply_patch=False)
        tv = json.loads(Path(res["theory_validation"]).read_text(encoding="utf-8"))
        self.assertIn("bibliography_loaded", tv)
        self.assertFalse(tv["bibliography_loaded"])  # since references.bib missing


if __name__ == "__main__":
    unittest.main()

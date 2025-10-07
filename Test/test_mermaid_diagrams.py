import unittest

from pathlib import Path

from src.sd_model.ui_streamlit import load_stage1, _mermaid_diagram


PROJECTS_TO_TEST = ["sd_test", "oss_model"]


class MermaidDiagramTests(unittest.TestCase):
    def test_diagrams_do_not_raise_and_are_well_formed(self):
        for project in PROJECTS_TO_TEST:
            with self.subTest(project=project):
                data = load_stage1(project)

                connections = data["connections"]
                variables_llm = data.get("variables_llm", {"variables": []})
                var_types = {
                    v["name"]: v.get("type", "Auxiliary")
                    for v in variables_llm.get("variables", [])
                }

                # Exercise all non-flow variables to ensure diagram creation succeeds.
                for name, var_type in var_types.items():
                    if str(var_type).lower() == "flow":
                        continue
                    with self.subTest(variable=name):
                        diagram = _mermaid_diagram(connections, name, var_types)
                        self.assertIn(
                            "flowchart LR",
                            diagram,
                            msg=f"Diagram missing flowchart header for {name}",
                        )
                        self.assertNotIn(
                            '"""',
                            diagram,
                            msg=f"Diagram contains triple quotes for {name}",
                        )
                        self.assertNotIn(
                            "\r",
                            diagram,
                            msg=f"Diagram contains carriage return for {name}",
                        )


if __name__ == "__main__":
    unittest.main()


from __future__ import annotations
import json
from pathlib import Path
from sd_model.llm.client import LLMClient


IMPROVE_PROMPT = """Based on theory validation of an open-source community system dynamics model, generate specific improvements.

VALIDATION FINDINGS:
- Average theory alignment: {avg_alignment}/10
- Theories applied: {theory_names}

CONSISTENTLY MISSING CONNECTIONS:
{missing_json}

CONSISTENTLY PROBLEMATIC CONNECTIONS:
{issues_json}

CURRENT MODEL STATS:
- Total connections: {total_connections}
- Variables include: Contributors, Knowledge, PRs, Issues, Reputation

TASK: Generate concrete improvements to the model.

OUTPUT FORMAT (JSON):
{{
  "priority_additions": [{{"from": "Source", "to": "Target", "relationship": "positive/negative", "rationale": "...", "expected_impact": "..."}}],
  "recommended_removals": [{{"from": "Source", "to": "Target", "reason": "..."}}],
  "new_variables_needed": [{{"name": "Variable Name", "type": "stock/flow/auxiliary", "purpose": "...", "connects_to": ["..."]}}],
  "structural_changes": [{{"change": "...", "justification": "..."}}],
  "implementation_order": ["Step 1", "Step 2", "Step 3"],
  "expected_improvement": "Overall expected impact on model quality"
}}
"""


def create_implementation_script(improvements: dict) -> dict:
    script = {"additions": [], "removals": [], "new_variables": []}
    for addition in improvements.get("priority_additions", []):
        script["additions"].append({
            "command": f"Add connection: {addition['from']} → {addition['to']} ({addition['relationship']})",
            "mdl_fragment": f"{addition['to']} = A FUNCTION OF(..., {'-' if addition['relationship']=='negative' else ''}{addition['from']})",
            "rationale": addition.get("rationale", ""),
        })
    for new_var in improvements.get("new_variables_needed", []):
        connections_str = ", ".join(new_var.get("connects_to", []))
        script["new_variables"].append({
            "command": f"Create variable: {new_var['name']}",
            "mdl_fragment": f"{new_var['name']} = A FUNCTION OF({connections_str})",
            "type": new_var.get("type"),
            "purpose": new_var.get("purpose", ""),
        })
    return script


def generate_updated_connections(current_connections: list[dict], improvements: dict) -> list[dict]:
    updated = list(current_connections)
    for addition in improvements.get("priority_additions", []):
        updated.append({"from": addition["from"], "to": addition["to"], "relationship": addition["relationship"]})
    for removal in improvements.get("recommended_removals", []):
        for conn in updated:
            if conn["from"] == removal["from"] and conn["to"] == removal["to"]:
                conn["marked_for_review"] = True
                conn["removal_reason"] = removal.get("reason", "")
    return updated


def improve_model(validation_path: Path, connections_path: Path, out_path: Path,
                  api_key: str | None = None, model: str = "deepseek-chat") -> dict:
    validation_results = json.loads(validation_path.read_text())
    connections_data = json.loads(connections_path.read_text())
    connections = connections_data["connections"]

    prompt = IMPROVE_PROMPT.format(
        avg_alignment=validation_results.get("average_alignment", 0),
        theory_names=", ".join(v["theory"] for v in validation_results.get("theory_validations", [])),
        missing_json=json.dumps(validation_results.get("consistent_missing", []), indent=2),
        issues_json=json.dumps(validation_results.get("consistent_issues", []), indent=2),
        total_connections=len(connections),
    )

    client = LLMClient(api_key=api_key, model=model)
    content = client.chat(prompt, temperature=0.4)
    improvements = json.loads(content)

    implementation_script = create_implementation_script(improvements)
    updated_connections = generate_updated_connections(connections, improvements)

    output = {
        "improvements": improvements,
        "implementation_script": implementation_script,
        "statistics": {
            "additions_proposed": len(improvements.get("priority_additions", [])),
            "removals_suggested": len(improvements.get("recommended_removals", [])),
            "new_variables": len(improvements.get("new_variables_needed", [])),
            "total_connections_after": len(updated_connections),
        },
        "updated_connections": updated_connections,
    }

    out_path.write_text(json.dumps(output, indent=2))
    return output


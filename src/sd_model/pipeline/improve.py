from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..knowledge.loader import load_feedback


def propose_improvements(
    theory_validation_path: Path,
    feedback_path: Path,
    out_path: Path,
) -> Dict:
    """Generate actionable improvements given validation findings and optional feedback.

    Priority:
    1) Address structured user feedback items.
    2) Address gaps identified in the theory validation (missing links).

    Output conforms to model_improvements.schema.json and is deterministic when no LLM
    is configured, but the structure supports LLM integration later.
    """
    tv = json.loads(theory_validation_path.read_text(encoding="utf-8"))
    feedback_items = load_feedback(feedback_path) if feedback_path.exists() else []

    improvements: List[Dict] = []

    # 1) Encode user feedback into operations where possible
    for fb in feedback_items:
        # Simple heuristic: if action suggests adding a variable or link, produce ops
        action = fb.action.lower()
        if "add variable" in action or "new variable" in action:
            var_name = fb.comment.strip().split("\n")[0][:64] or f"var_{fb.feedback_id}"
            improvements.append(
                {
                    "operation": "add_variable",
                    "name": var_name,
                    "equation": "0",
                    "comment": f"Addresses feedback {fb.feedback_id}",
                }
            )
        elif "add connection" in action or "link" in action:
            # Attempt to parse a pattern like: from -> to (positive)
            # Preserve original variable casing; only normalize the relation token
            text = fb.comment
            if "->" in text:
                parts = [p.strip() for p in text.split("->", 1)]
                from_var = parts[0][:64] or "From"
                to_rest = parts[1]
                if "(" in to_rest and ")" in to_rest:
                    to_var = to_rest.split("(")[0].strip()[:64]
                    rel = to_rest.split("(")[1].split(")")[0].strip().lower() or "unknown"
                else:
                    to_var = to_rest.strip()[:64] or "To"
                    rel = "unknown"
                improvements.append(
                    {
                        "operation": "add_connection",
                        "from": from_var,
                        "to": to_var,
                        "relationship": rel,
                        "comment": f"Addresses feedback {fb.feedback_id}",
                    }
                )
            else:
                # Non-parsable connection request; add a placeholder variable
                improvements.append(
                    {
                        "operation": "add_variable",
                        "name": f"Feedback_{fb.feedback_id}",
                        "equation": "0",
                        "comment": f"Addresses feedback {fb.feedback_id}",
                    }
                )

    # 2) Fill gaps from theory validation: add missing expected links
    for m in tv.get("missing", []):
        improvements.append(
            {
                "operation": "add_connection",
                "from": m.get("from_var"),
                "to": m.get("to_var"),
                "relationship": m.get("relationship", "unknown"),
                "comment": f"From theory: {m.get('theory')} ({m.get('citation_key')})",
            }
        )

    result = {"improvements": improvements}
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

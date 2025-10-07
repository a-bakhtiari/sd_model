from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def derive_connections(parsed: Dict, out_path: Path) -> Dict:
    """Produce a naive connections graph from parsed equations.

    Heuristic: if an equation text mentions another variable name, create a
    connection from the mentioned variable to the target variable with
    relationship "unknown".
    """
    equations: Dict[str, str] = parsed.get("equations", {})
    vars_list: List[str] = parsed.get("variables", [])
    connections: List[Dict[str, str]] = []

    for target, expr in equations.items():
        for cand in vars_list:
            if cand == target:
                continue
            if cand in expr:
                connections.append(
                    {"from_var": cand, "to_var": target, "relationship": "unknown"}
                )

    result = {"connections": connections}
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


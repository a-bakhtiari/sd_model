from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def compute_loops(parsed: Dict, out_path: Path) -> Dict:
    """Stub loop detection. Produces an empty set or trivial hints.

    For maintainability, we keep this deterministic and minimal. Advanced loop
    detection can be integrated later without changing the artifact contract.
    """
    variables: List[str] = parsed.get("variables", [])
    loops = {"balancing": [], "reinforcing": [], "notes": []}
    if len(variables) > 5:
        loops["notes"].append("Model has more than 5 variables; loop detection TBD.")
    out_path.write_text(json.dumps(loops, indent=2), encoding="utf-8")
    return loops


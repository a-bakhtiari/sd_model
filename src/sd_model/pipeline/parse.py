from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


def parse_mdl(mdl_path: Path, out_path: Path) -> Dict:
    """Very lightweight parser extracting variables and equations from a Vensim .mdl.

    This is not a full Vensim parser. It looks for lines of the form:
        Variable = Equation ~ Units ~| Comment

    Writes a `parsed.json` artifact with fields: variables, equations.
    """
    text = mdl_path.read_text(encoding="utf-8", errors="ignore")
    variables: List[str] = []
    equations: Dict[str, str] = {}

    line_re = re.compile(r"^\s*([^=\n]+?)\s*=\s*(.+?)\s*~", re.MULTILINE | re.DOTALL)
    for m in line_re.finditer(text):
        var = m.group(1).strip()
        eq_raw = m.group(2)
        # Collapse Vensim continuation backslashes and normalize whitespace
        eq = eq_raw.replace("\\\n", " ")
        eq = " ".join(eq.split())
        variables.append(var)
        equations[var] = eq

    result = {"variables": sorted(set(variables)), "equations": equations}
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

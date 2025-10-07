from __future__ import annotations

import json
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from ..llm.client import LLMClient
from .parse import parse_mdl  # fallback heuristics


VARIABLE_PROMPT = """
You are a system dynamics model parser. Analyze the provided Vensim .mdl text and return a JSON object.

Instructions for understanding variable types:
How to Find the Variable Types
The key is in the lines that start with 10,. These lines define the variables you see on the diagram. The format is 10, ID, Name, X, Y, Width, Height, ShapeCode, ....

The eighth field in these lines is a Shape Code that helps identify the variable's type.

Flows (Rates)
This is the most straightforward type to identify.
Flow variables have a Shape Code of 40.

Let's look at some of your flows from the file:

10,11,Adoption Rate,...,46,26,40,3,0,0,...
10,16,User Churn Rate,...,46,26,40,3,0,0,...
10,76,Skill up,...,46,26,40,3,0,0,...
10,85,Joining Rate,...,46,26,40,3,0,0,...

Every variable that functions as a rate of change (a flow) has this unique 40 code.

Stocks (Levels)
This is more subtle. Stocks are variables drawn as rectangles that receive flow connections (valves). In the file, determine stocks by finding flow valves (lines starting with 11,) and their target objects from arrow records (lines starting with 1,). Any variable that is the destination of a valve-fed arrow is a Stock.

Auxiliaries
Any variable (10,) that is not a Flow (ShapeCode 40) and not identified as a Stock is an Auxiliary. Their ShapeCodes vary (e.g., 3 or 8).

Return JSON ONLY with this schema:
{
  "variables": [
    {"id": <int>, "name": "<original name>", "type": "Stock" | "Flow" | "Auxiliary"}
  ]
}

Use the exact IDs and names from the sketch section. Do not invent additional keys.

MODEL TEXT START\n```mdl\n{mdl_text}\n```\nMODEL TEXT END
"""


CONNECTION_PROMPT = """
You are a system dynamics model parser. Analyze the provided Vensim .mdl text and return a JSON object describing causal connections.

Follow these instructions:
1. Parse the equation section (before the \\---/// Sketch information block).
2. Equations appear as `Target Variable = A FUNCTION OF(Source1, -Source2, ...)`.
3. For each source variable:
   - If prefixed with `-`, polarity is `NEGATIVE` (remove the minus when recording the name).
   - If prefixed with `+`, polarity is `POSITIVE`.
   - Otherwise polarity is `UNDECLARED`.
4. Use the sketch information (lines starting with `10,`) to map names to IDs.
5. Output JSON ONLY with this schema:
{
  "connections": [
    {"from": <source_id>, "to": <target_id>, "polarity": "POSITIVE"|"NEGATIVE"|"UNDECLARED"}
  ]
}
6. Ignore sources you cannot map to an ID (e.g., constants).

MODEL TEXT START\n```mdl\n{mdl_text}\n```\nMODEL TEXT END
"""


def _call_llm_json(client: LLMClient, prompt: str, fallback) -> Dict:
    if client.enabled:
        response = client.complete(prompt, temperature=0.0)
        try:
            return json.loads(response)
        except Exception:
            pass  # fall back to heuristic implementation
    return fallback()


def _load_mdl_text(mdl_path: Path) -> str:
    return mdl_path.read_text(encoding="utf-8", errors="ignore")


def _sketch_lines(mdl_text: str) -> List[List[str]]:
    lines = mdl_text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if "---///" in line:
            start = idx + 1
            break
    if start is None:
        return []
    sketch = lines[start:]
    parsed: List[List[str]] = []
    for raw in sketch:
        stripped = raw.strip()
        if not stripped:
            continue
        reader = csv.reader([stripped])
        try:
            fields = next(reader)
            parsed.append([f.strip() for f in fields])
        except Exception:
            continue
    return parsed


def _fallback_variable_types(mdl_path: Path) -> Dict:
    mdl_text = _load_mdl_text(mdl_path)
    sketch = _sketch_lines(mdl_text)
    flows = set()
    name_by_id: Dict[int, str] = {}
    type_by_id: Dict[int, str] = {}

    for fields in sketch:
        if not fields:
            continue
        if fields[0] == "10" and len(fields) >= 8:
            try:
                var_id = int(fields[1])
            except ValueError:
                continue
            name = fields[2].strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            name_by_id[var_id] = name
            shape = fields[7].strip()
            if shape == "40":
                type_by_id[var_id] = "Flow"

    valve_ids = set()
    for fields in sketch:
        if fields and fields[0] == "11" and len(fields) >= 2:
            try:
                valve_ids.add(int(fields[1]))
            except ValueError:
                continue

    stock_ids = set()
    for fields in sketch:
        if fields and fields[0] == "1" and len(fields) >= 4:
            try:
                from_id = int(fields[2])
                to_id = int(fields[3])
            except ValueError:
                continue
            if from_id in valve_ids:
                stock_ids.add(to_id)

    variables = []
    for var_id, name in name_by_id.items():
        if var_id in type_by_id:
            var_type = type_by_id[var_id]
        elif var_id in stock_ids:
            var_type = "Stock"
        else:
            var_type = "Auxiliary"
        variables.append({"id": var_id, "name": name, "type": var_type})

    variables.sort(key=lambda v: v["id"])
    return {"variables": variables}


def _fallback_equations(mdl_path: Path) -> Dict[str, str]:
    mdl_text = _load_mdl_text(mdl_path)
    eq_pattern = re.compile(r"^\s*([^=\n]+?)\s*=\s*(.+?)\s*~", re.MULTILINE | re.DOTALL)
    equations: Dict[str, str] = {}
    for match in eq_pattern.finditer(mdl_text.split("\\\\---///")[0]):
        var = match.group(1).strip()
        eq = match.group(2).replace("\\\n", " ")
        eq = " ".join(eq.split())
        equations[var] = eq
    return equations


def _fallback_connections(mdl_path: Path, variables: Dict[int, str]) -> Dict:
    equations = _fallback_equations(mdl_path)
    name_to_id = {name: vid for vid, name in variables.items()}
    connections: List[Dict[str, object]] = []
    func_pattern = re.compile(r"A FUNCTION OF\((.*)\)")
    for target, expr in equations.items():
        match = func_pattern.search(expr)
        if not match:
            continue
        sources = [s.strip() for s in match.group(1).split(",") if s.strip()]
        target_id = name_to_id.get(target.strip('"'))
        if target_id is None:
            continue
        for src in sources:
            polarity = "UNDECLARED"
            if src.startswith("-"):
                polarity = "NEGATIVE"
                src = src[1:]
            elif src.startswith("+"):
                polarity = "POSITIVE"
                src = src[1:]
            src = src.strip()
            if src.startswith('"') and src.endswith('"'):
                src = src[1:-1]
            from_id = name_to_id.get(src)
            if from_id is None:
                continue
            connections.append({"from": from_id, "to": target_id, "polarity": polarity})
    return {"connections": connections}


def infer_variable_types(mdl_path: Path, client: LLMClient) -> Dict:
    mdl_text = _load_mdl_text(mdl_path)

    def fallback():
        return _fallback_variable_types(mdl_path)

    prompt = VARIABLE_PROMPT.replace("{mdl_text}", mdl_text)
    result = _call_llm_json(client, prompt, fallback)
    # sanitize result to expected schema
    variables = result.get("variables", [])
    cleaned = []
    for item in variables:
        try:
            var_id = int(item.get("id"))
            name = str(item.get("name", "")).strip()
            var_type = str(item.get("type", "Auxiliary")).capitalize()
            if var_type not in {"Stock", "Flow", "Auxiliary"}:
                var_type = "Auxiliary"
            cleaned.append({"id": var_id, "name": name, "type": var_type})
        except Exception:
            continue
    cleaned.sort(key=lambda v: v["id"])
    if not cleaned:
        return fallback()
    return {"variables": cleaned}


def infer_connections(mdl_path: Path, variables_data: Dict, client: LLMClient) -> Dict:
    mdl_text = _load_mdl_text(mdl_path)
    id_to_name = {int(v["id"]): v["name"] for v in variables_data.get("variables", [])}

    def fallback():
        return _fallback_connections(mdl_path, id_to_name)

    prompt = CONNECTION_PROMPT.replace("{mdl_text}", mdl_text)
    result = _call_llm_json(client, prompt, fallback)
    connections = result.get("connections", [])
    cleaned = []
    for item in connections:
        try:
            from_id = int(item.get("from"))
            to_id = int(item.get("to"))
            polarity = str(item.get("polarity", "UNDECLARED")).upper()
            if polarity not in {"POSITIVE", "NEGATIVE", "UNDECLARED"}:
                polarity = "UNDECLARED"
            if from_id not in id_to_name or to_id not in id_to_name:
                continue
            cleaned.append({"from": from_id, "to": to_id, "polarity": polarity})
        except Exception:
            continue
    if not cleaned:
        return fallback()
    return {"connections": cleaned}

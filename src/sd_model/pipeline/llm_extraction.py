from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from ..llm.client import LLMClient


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
Extract all causal connections from this Vensim model file with their polarity.

FILE STRUCTURE:
The file has two parts separated by "\\---/// Sketch information":
- EQUATIONS (before separator): Define mathematical relationships
- SKETCH (after separator): Define visual diagram with polarity markers

TASK:
1. Extract all connections from equations
2. Determine polarity for each connection using sketch data
3. Output JSON with connection list

POLARITY RULES (check in this order):
1. NEGATIVE: Source variable has "-" prefix in equation (e.g., "A FUNCTION OF(-X, Y)" means X→target is NEGATIVE)
2. POSITIVE: Sketch arrow has EXACTLY value 43 in the 7th field (field[6]=43)
3. UNDECLARED: Everything else (including field[6]=0 or any value other than 43)

IMPORTANT: Only mark as POSITIVE if you find field[6]=43 in a sketch arrow. Do NOT assume positive polarity from equations or valve presence alone.

SKETCH FORMAT:
Lines starting with "10," define variables:
  10,<id>,<name>,...
  Example: 10,93,Implicit Knowledge Transfer,...

Lines starting with "1," define arrows:
  1,arrow_id,from_id,to_id,field4,field5,field6,field7,...
  Example: 1,97,93,80,1,0,43,0,...

  This arrow goes from variable 93 to variable 80.
  The 7th field is 43, so this connection is POSITIVE.
  Split by commas and count: field1=arrow_id, field2=from_id, field3=to_id, field4=1, field5=0, field6=43, field7=0

Lines starting with "11," define valves (flow control symbols):
  11,<valve_id>,...

VALVE HANDLING:
Valves act as intermediaries for flow variables. Two cases:

Case A: Arrow from variable to valve
  1. Find all arrows FROM that valve (arrows where from_id = valve_id)
  2. These arrows point to stocks
  3. Look at each stock's equation to find which flow variable appears in it
  4. The connection is: original_source_variable → that_flow_variable
  5. Check the original arrow to the valve: if field[6]=43 then POSITIVE, else UNDECLARED (or NEGATIVE if equation has "-")

Case B: Arrow from valve to valve
  1. First valve represents a flow variable
  2. Second valve represents another flow variable
  3. Find which flow variables these valves control (by looking at stock equations)
  4. The connection is: first_flow → second_flow
  5. Check the arrow between valves: if field[6]=43 then POSITIVE, else UNDECLARED (or NEGATIVE if equation has "-")

EXAMPLE 1 - Variable to valve (generic scenario):
Equation: "Worker Productivity = A FUNCTION OF(Training Quality,...)"
Sketch arrow: 1,201,15,42,1,0,43,0,...
Sketch valve: 11,42,...
Sketch variable: 10,15,Training Quality,...
Sketch variable: 10,18,Worker Productivity,...

Step 1: Equation shows connection exists (15 → something)
Step 2: Sketch arrow 1,201,15,42 shows arrow from variable 15 to 42 with field[6]=43 (POSITIVE)
Step 3: ID 42 is a valve (found in 11,42,... line)
Step 4: Find arrows FROM valve 42, they point to stocks
Step 5: Check those stock equations to find which flow appears → find "Worker Productivity" (ID 18)
Step 6: Output connection: 15 → 18 with POSITIVE polarity
Reason: "sketch arrow 15→42 (valve) has field[6]=43, valve controls flow 18"

EXAMPLE 2 - Valve to valve (generic scenario):
Equation: "Onboarding Rate = A FUNCTION OF(Hiring Rate)"
Sketch arrow: 1,305,33,37,1,0,43,0,...
Sketch valve: 11,33,... (represents Hiring Rate, ID 52)
Sketch valve: 11,37,... (represents Onboarding Rate, ID 58)

Step 1: Equation shows connection (52 → 58)
Step 2: Sketch arrow 1,305,33,37 shows arrow from valve 33 to valve 37 with field[6]=43 (POSITIVE)
Step 3: Both 33 and 37 are valves (found in 11,33,... and 11,37,... lines)
Step 4: Check stock equations to identify: valve 33 represents flow 52, valve 37 represents flow 58
Step 5: Output connection: 52 → 58 with POSITIVE polarity
Reason: "sketch arrow from valve 33 to valve 37 has field[6]=43, representing flow 52→58"

EXAMPLE 3 - Valve with NO positive marker (generic scenario):
Equation: "Inventory Level = A FUNCTION OF(Production Rate,...)"
Sketch arrow: 1,410,25,200,4,0,0,22,...
Sketch valve: 11,25,...
Sketch variable: 10,12,Production Rate,...

Analysis: Arrow from valve 25 to stock 200 has field[6]=0 (NOT 43)
Even though valve 25 represents flow "Production Rate", the connection 12→200 is UNDECLARED
Do NOT assume positive polarity just because a valve exists - must see field[6]=43

OUTPUT FORMAT (JSON only, no markdown):
{
  "connections": [
    {"from": <id>, "to": <id>, "polarity": "POSITIVE"|"NEGATIVE"|"UNDECLARED"}
  ]
}

MODEL FILE:
{mdl_text}
"""


def _call_llm_json(client: LLMClient, prompt: str) -> Dict:
    if not client.enabled:
        raise RuntimeError(f"LLM client is NOT enabled! Check your .env file.")

    response = client.complete(prompt, temperature=0.0)

    # Strip markdown code blocks if present
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]  # Remove ```json
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]  # Remove ```
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]  # Remove trailing ```
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        print(f"JSON parsed successfully! Found {len(result.get('connections', []))} connections")
        return result
    except Exception as e:
        print(f"JSON parse error: {e}")
        print(f"Cleaned response:\n{cleaned[:500]}\n")
        raise RuntimeError(f"LLM returned invalid JSON: {e}")


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


def infer_variable_types(mdl_path: Path, client: LLMClient) -> Dict:
    mdl_text = _load_mdl_text(mdl_path)
    prompt = VARIABLE_PROMPT.replace("{mdl_text}", mdl_text)
    result = _call_llm_json(client, prompt)
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
        raise RuntimeError("LLM returned no valid variables - check the model output")
    return {"variables": cleaned}


def infer_connections(mdl_path: Path, variables_data: Dict, client: LLMClient) -> Dict:
    mdl_text = _load_mdl_text(mdl_path)
    id_to_name = {int(v["id"]): v["name"] for v in variables_data.get("variables", [])}

    prompt = CONNECTION_PROMPT.replace("{mdl_text}", mdl_text)
    result = _call_llm_json(client, prompt)
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
        raise RuntimeError("LLM returned no valid connections - check the model output")
    return {"connections": cleaned}

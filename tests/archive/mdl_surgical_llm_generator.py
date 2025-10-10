"""LLM-Based Surgical MDL Generator.

Uses LLM to generate surgical edits to MDL files.
Each operation gets a focused prompt with mdl_rules.md.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, '.')

from src.sd_model.llm.client import LLMClient


def load_mdl_rules() -> str:
    """Load MDL rules reference."""
    rules_path = Path("docs/mdl_rules.md")
    if not rules_path.exists():
        raise FileNotFoundError(f"MDL rules not found: {rules_path}")
    return rules_path.read_text(encoding="utf-8")


def llm_add_variable(
    var_spec: Dict,
    max_id: int,
    mdl_rules: str,
    llm_client: LLMClient
) -> Dict[str, str]:
    """Generate equation block and sketch lines for new variable using LLM.

    Args:
        var_spec: Variable specification with name, type, description, position, etc.
        max_id: Current maximum sketch ID
        mdl_rules: MDL format rules
        llm_client: LLM client instance

    Returns:
        Dict with 'equation_block' and 'sketch_lines' keys
    """

    var_name = var_spec["name"]
    var_type = var_spec["type"]  # Stock, Auxiliary
    description = var_spec.get("description", "")
    units = var_spec.get("units", "")
    position = var_spec.get("position", {})
    size = var_spec.get("size", {})
    color = var_spec.get("color", {}).get("border", "0-255-0")

    x = position.get("x", 1000)
    y = position.get("y", 500)
    width = size.get("width", 70 if var_type == "Stock" else 60)
    height = size.get("height", 26)

    prompt = f"""You are a Vensim MDL expert. Generate MDL code for a new variable.

# MDL Format Rules
{mdl_rules}

# Variable to Add
- Name: {var_name}
- Type: {var_type}
- Description: {description}
- Units: {units}
- Position: x={x}, y={y}
- Size: width={width}, height={height}
- Border color: {color} (green for additions)

# Context
- Next available sketch ID: {max_id + 1}
- This is a new variable being added (not modifying existing)

# Your Task
Generate TWO sections:

1. **EQUATION_BLOCK** - The 3-line equation block:
```
<VarName> = A FUNCTION OF( )
~	{units}
~	{description}|
```

2. **SKETCH_LINES** - The sketch section line(s):

**Standard variable (no green border):**
```
10,{max_id + 1},Name,x,y,width,height,type,3,0,0,-1,0,0,0,0,0,0,0,0,0
```

**Variable with green border:**
```
10,{max_id + 1},Name,x,y,width,height,type,3,0,2,-1,1,0,0,0-0-0,{color},|||0-0-0,0,0,0,0,0,0
```

Use the EXACT format above - do not add extra fields.

# Important Rules
- Quote the variable name in sketch if it contains special chars: (),-/
- Stock type code: 3, Auxiliary type code: 8
- Use exact field count (20 fields for normal, 27 for colored)
- If Stock: may need 11, and 12, lines (flow/cloud) - but not for this simple case

# Output Format
Return ONLY valid JSON:
{{
  "equation_block": "<3-line equation block>",
  "sketch_lines": [
    "<10, line>",
    "<11, line if needed>",
    "<12, line if needed>"
  ]
}}

Generate the code now.
"""

    response = llm_client.complete(prompt, temperature=0.1, max_tokens=1000)

    # Parse JSON response
    import json
    try:
        # Try to parse the entire response as JSON first
        result = json.loads(response.strip())
        return result
    except json.JSONDecodeError:
        # If that fails, try to extract JSON from response
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found in LLM response")
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Full response:\n{response}")
            raise


def llm_add_connection(
    from_var: str,
    to_var: str,
    relationship: str,
    current_equation: str,
    from_id: int,
    to_id: int,
    mdl_rules: str,
    llm_client: LLMClient
) -> Dict[str, str]:
    """Generate updated equation and connection line for new connection using LLM.

    Args:
        from_var: Source variable name
        to_var: Target variable name
        relationship: "positive" or "negative"
        current_equation: Current equation line of target variable
        from_id: Sketch ID of source variable
        to_id: Sketch ID of target variable
        mdl_rules: MDL format rules
        llm_client: LLM client instance

    Returns:
        Dict with 'equation_line' and 'sketch_line' keys
    """

    prompt = f"""You are a Vensim MDL expert. Update an equation to add a new connection.

# MDL Format Rules
{mdl_rules}

# Current Equation
```
{current_equation}
```

# Connection to Add
- From: {from_var} (ID: {from_id})
- To: {to_var} (ID: {to_id})
- Relationship: {relationship}

# Your Task
1. **Update the equation** to include the new connection:
   - Add "{from_var}" to the A FUNCTION OF(...) dependencies
   - Use "-{from_var}" if relationship is negative
   - Preserve existing dependencies
   - Quote the variable name if it has special chars

2. **Generate connection sketch line** (1,):
   - Format: 1,<new_id>,<from_id>,<to_id>,...
   - Use green color for new connection: 0-255-0
   - Use next available connection ID (you can use a high number like 999)

# Output Format
Return ONLY valid JSON:
{{
  "equation_line": "<updated equation line>",
  "sketch_line": "<1, connection line>"
}}

Generate the code now.
"""

    response = llm_client.complete(prompt, temperature=0.1, max_tokens=800)

    # Parse JSON response
    import json
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
            return result
        else:
            raise ValueError("No JSON found in LLM response")
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response: {response[:500]}")
        raise


def llm_validate_and_fix_mdl(
    mdl_content: str,
    mdl_rules: str,
    llm_client: LLMClient
) -> str:
    """Final validation and formatting fix using LLM.

    Args:
        mdl_content: Complete MDL file content
        mdl_rules: MDL format rules
        llm_client: LLM client instance

    Returns:
        Fixed MDL content (or original if valid)
    """

    prompt = f"""You are a Vensim MDL validator and formatter.

# MDL Format Rules
{mdl_rules}

# MDL File to Validate
```
{mdl_content}
```

# Your Task
Check and fix these issues:

1. **Equation ↔ Sketch sync**:
   - Every equation must have matching 10, sketch variable
   - Every 10, sketch variable must have equation

2. **Flow structure**:
   - Flow valves (11,) should be adjacent to their label variables (10,)
   - Example: 11,6,... followed by 10,7,Developer's Turnover,...

3. **Clouds (12,)**:
   - Source/sink clouds should be present for flows
   - Positioned near their flow valves

4. **Connection validity**:
   - All 1, lines must reference existing variable IDs
   - IDs in connections must match 10, variable IDs

5. **Formatting**:
   - Proper spacing between equation blocks
   - Sketch section ordering preserves visual structure
   - No duplicate IDs

# Output
If MDL is valid: Return exactly "VALID"
If fixes needed: Return the COMPLETE fixed MDL file

Do NOT add explanations, just return the result.
"""

    response = llm_client.complete(prompt, temperature=0.1, max_tokens=10000, timeout=300)

    if response.strip() == "VALID":
        return mdl_content
    else:
        # LLM returned fixed version
        return response

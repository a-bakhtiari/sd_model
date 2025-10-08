from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def discover_loops_with_llm(
    connections_data: Dict,
    variables_data: Dict,
    llm_client: LLMClient,
    domain_context: str = "open source software development"
) -> Dict:
    """
    Discover feedback loops using LLM with Meadows' system dynamics principles.

    Loops are DISCOVERED by their behavioral characteristics (reinforcing or balancing),
    not found as cycles and then classified.

    Args:
        connections_data: Connection data with from/to IDs and polarity
        variables_data: Variables data with names, types (Stock/Flow/Auxiliary)
        llm_client: LLM client for loop discovery
        domain_context: Domain context for better understanding

    Returns:
        Dict with "reinforcing" and "balancing" lists of discovered loops
    """
    # Create variable lookup
    var_lookup = {v["id"]: v for v in variables_data.get("variables", [])}

    # Convert connections to enriched format with names and types
    enriched_connections = []
    for conn in connections_data.get("connections", []):
        from_id = conn.get("from")
        to_id = conn.get("to")
        from_var = var_lookup.get(from_id, {})
        to_var = var_lookup.get(to_id, {})

        if not from_var or not to_var:
            continue

        polarity = conn.get("polarity", "UNDECLARED").upper()
        if polarity == "POSITIVE":
            relationship = "positive"
        elif polarity == "NEGATIVE":
            relationship = "negative"
        else:
            relationship = "unknown"

        enriched_connections.append({
            "from_var": from_var.get("name"),
            "from_type": from_var.get("type"),
            "to_var": to_var.get("name"),
            "to_type": to_var.get("type"),
            "relationship": relationship
        })

    # Create variable list for context
    variables_list = [
        {"name": v.get("name"), "type": v.get("type")}
        for v in variables_data.get("variables", [])
    ]

    # Create prompt for LLM to discover loops
    prompt = _create_discovery_prompt(enriched_connections, variables_list, domain_context)

    try:
        response = llm_client.complete(prompt, temperature=0.1)
        result = _parse_discovery_response(response)
        return result

    except Exception as e:
        return {
            "reinforcing": [],
            "balancing": [],
            "notes": [f"LLM loop discovery failed: {str(e)}"]
        }


def _create_discovery_prompt(
    connections: List[Dict],
    variables: List[Dict],
    domain_context: str
) -> str:
    """Create prompt for LLM to discover loops by their behavioral characteristics."""

    variables_info = "\n".join([
        f"- {var['name']} (Type: {var['type']})"
        for var in variables
    ])

    connections_info = "\n".join([
        f"- {conn['from_var']} ({conn['from_type']}) → {conn['to_var']} ({conn['to_type']}) [{conn['relationship']}]"
        for conn in connections
    ])

    return f"""You are an expert in system dynamics and feedback loop analysis. Your task is to discover feedback loops in a system using Donella Meadows' principles from "Thinking in Systems".

MEADOWS' DEFINITIONS:

**Balancing Feedback Loops**:
- Stabilizing, goal-seeking, regulating feedback loops
- They oppose whatever direction of change is imposed on the system
- They are sources of stability and resistance to change
- They keep a stock at a given value or within a range of values
- Create self-correcting behavior, negative feedback
- Examples: thermostat maintaining temperature, water level regulation

**Reinforcing Feedback Loops**:
- Self-enhancing, leading to exponential growth or runaway collapses
- They amplify whatever direction of change is imposed
- They generate more input to a stock the more that stock already exists
- Create virtuous or vicious cycles, compound growth, snowball effects
- Examples: population growth, viral spread, compound interest, "success breeds success"

DOMAIN CONTEXT: {domain_context}

SYSTEM VARIABLES:
{variables_info}

SYSTEM CONNECTIONS:
{connections_info}

TASK:
Discover feedback loops in this system by identifying patterns that exhibit REINFORCING or BALANCING behavior.

A feedback loop exists when you can trace a path through connections that returns to the starting variable, creating a closed cycle.

For EACH loop you discover, determine if it exhibits:
1. REINFORCING behavior (self-amplifying, growth/collapse)
2. BALANCING behavior (self-regulating, goal-seeking)

IMPORTANT GUIDELINES:
- Variable types matter: Stocks accumulate, Flows change stocks, Auxiliaries are derived values
- Consider the semantic meaning in the {domain_context} domain
- Focus on BEHAVIOR the loop creates, not just mathematical structure
- Only report loops that clearly exhibit reinforcing or balancing characteristics
- Provide detailed reasoning explaining WHY each loop exhibits its behavior
- Confidence should reflect how clearly the loop exhibits the behavior (0.0-1.0)

OUTPUT FORMAT (JSON):
{{
  "reinforcing": [
    {{
      "id": "R01",
      "variables": ["Var1", "Var2", "Var3"],
      "edges": [
        {{"from_var": "Var1", "to_var": "Var2", "relationship": "positive"}},
        {{"from_var": "Var2", "to_var": "Var3", "relationship": "positive"}},
        {{"from_var": "Var3", "to_var": "Var1", "relationship": "positive"}}
      ],
      "length": 3,
      "loop": "Var1 → Var2 → Var3 → Var1",
      "confidence": 0.85
    }}
  ],
  "balancing": [
    {{
      "id": "B01",
      "variables": ["VarA", "VarB"],
      "edges": [
        {{"from_var": "VarA", "to_var": "VarB", "relationship": "negative"}},
        {{"from_var": "VarB", "to_var": "VarA", "relationship": "positive"}}
      ],
      "length": 2,
      "loop": "VarA → VarB → VarA",
      "confidence": 0.9
    }}
  ]
}}

Your response (JSON only, no additional text):"""


def _parse_discovery_response(response: str) -> Dict:
    """Parse LLM response and extract discovered loops."""
    try:
        # Try to extract JSON from response
        response = response.strip()

        # Handle cases where LLM adds extra text before/after JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)

            # Ensure required structure
            if "reinforcing" not in result:
                result["reinforcing"] = []
            if "balancing" not in result:
                result["balancing"] = []
            if "notes" not in result:
                result["notes"] = []

            # Validate and clean up loops
            result["reinforcing"] = _validate_loops(result.get("reinforcing", []), "R")
            result["balancing"] = _validate_loops(result.get("balancing", []), "B")

            return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        pass

    # Fallback for failed parsing
    return {
        "reinforcing": [],
        "balancing": [],
        "notes": [f"Failed to parse LLM response: {response[:500]}..."]
    }


def _validate_loops(loops: List[Dict], id_prefix: str) -> List[Dict]:
    """Validate and clean up loop structures."""
    validated = []

    for idx, loop in enumerate(loops):
        # Ensure required fields
        if "variables" not in loop or "edges" not in loop:
            continue

        # Set default ID if missing
        if "id" not in loop:
            loop["id"] = f"{id_prefix}{idx+1:02d}"

        # Ensure ID has correct prefix
        if not loop["id"].startswith(id_prefix):
            loop["id"] = f"{id_prefix}{idx+1:02d}"

        # Set length
        loop["length"] = len(loop.get("variables", []))

        # Set defaults for optional fields
        if "loop" not in loop:
            loop["loop"] = " → ".join(loop["variables"] + [loop["variables"][0]]) if loop["variables"] else ""
        if "confidence" not in loop:
            loop["confidence"] = 0.5

        # Validate confidence range
        try:
            confidence = float(loop["confidence"])
            loop["confidence"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            loop["confidence"] = 0.5

        validated.append(loop)

    return validated

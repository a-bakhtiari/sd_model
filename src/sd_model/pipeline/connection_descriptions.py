from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ..llm.client import LLMClient


def generate_connection_descriptions(
    connections_data: Dict,
    variables_data: Dict,
    llm_client: LLMClient,
    out_path: Path,
    domain_context: str = "open source software development"
) -> Dict:
    """
    Generate brief descriptions for each connection explaining the causal relationship.

    Uses efficient output format: only connection ID + description to minimize LLM output.

    Args:
        connections_data: Connection data from connections.json with id, from_var, to_var, relationship
        variables_data: Variables data (for getting variable types if needed)
        llm_client: LLM client for generating descriptions
        out_path: Path to write connection_descriptions.json
        domain_context: Domain context for better descriptions

    Returns:
        Dict with connection descriptions
    """
    # Extract connections directly from connections.json format
    # Note: variables_data contains variable types if we need them later
    var_lookup = {v["name"]: v for v in variables_data.get("variables", [])} if variables_data else {}

    enriched_connections = []
    for conn in connections_data.get("connections", []):
        conn_id = conn.get("id", "")
        from_var_name = conn.get("from_var", "")
        to_var_name = conn.get("to_var", "")
        relationship = conn.get("relationship", "undeclared")

        if not conn_id or not from_var_name or not to_var_name:
            continue

        # Get variable types if available
        from_var_info = var_lookup.get(from_var_name, {})
        to_var_info = var_lookup.get(to_var_name, {})

        enriched_connections.append({
            "id": conn_id,
            "from_var": from_var_name,
            "from_type": from_var_info.get("type", "Unknown"),
            "to_var": to_var_name,
            "to_type": to_var_info.get("type", "Unknown"),
            "relationship": relationship
        })

    if not enriched_connections:
        result = {"descriptions": [], "notes": ["No connections to describe"]}
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # Create prompt for LLM
    prompt = _create_description_prompt(enriched_connections, domain_context)

    try:
        response = llm_client.complete(prompt, temperature=0.1)
        result = _parse_description_response(response, enriched_connections)
    except Exception as e:
        result = {
            "descriptions": [],
            "notes": [f"LLM description generation failed: {str(e)}"]
        }

    # Write to file
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _create_description_prompt(connections: list, domain_context: str) -> str:
    """Create prompt for LLM to generate connection descriptions."""

    connections_info = "\n".join([
        f"  {conn['id']}: {conn['from_var']} ({conn['from_type']}) → {conn['to_var']} ({conn['to_type']}) [{conn['relationship']}]"
        for conn in connections
    ])

    return f"""You are an expert in system dynamics and {domain_context}. Your task is to provide brief descriptions for causal connections in a system dynamics model.

DOMAIN CONTEXT: {domain_context}

CONNECTIONS TO DESCRIBE:
{connections_info}

TASK:
For each connection, provide a brief 1-sentence description explaining the causal relationship between the variables. Focus on WHY and HOW the source variable affects the target variable in the context of {domain_context}.

GUIDELINES:
- Keep descriptions concise (1 sentence, ~10-20 words)
- Explain the causal mechanism
- Consider variable types: Stocks accumulate, Flows change stocks, Auxiliaries are derived
- Use domain-appropriate language
- For positive relationships: explain how increases in source lead to increases in target
- For negative relationships: explain how increases in source lead to decreases in target

OUTPUT FORMAT (JSON only, no additional text):
{{
  "descriptions": [
    {{"id": "C01", "description": "More core developers increase mentorship capacity and knowledge transfer opportunities"}},
    {{"id": "C02", "description": "Higher mentorship quality accelerates skill development for new contributors"}},
    ...
  ]
}}

IMPORTANT: Output ONLY the IDs and descriptions. Do not repeat the full connection details.

Your response (JSON only):"""


def _parse_description_response(response: str, connections: list) -> Dict:
    """Parse LLM response and extract descriptions."""
    try:
        # Try to extract JSON from response
        response = response.strip()

        # Handle cases where LLM adds extra text before/after JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)

            if "descriptions" not in result:
                result["descriptions"] = []

            # Validate that all connection IDs have descriptions
            described_ids = {desc.get("id") for desc in result["descriptions"]}
            missing_ids = []

            for conn in connections:
                if conn["id"] not in described_ids:
                    missing_ids.append(conn["id"])
                    # Add placeholder description
                    result["descriptions"].append({
                        "id": conn["id"],
                        "description": f"Connection from {conn['from_var']} to {conn['to_var']}"
                    })

            if missing_ids:
                if "notes" not in result:
                    result["notes"] = []
                result["notes"].append(f"Missing descriptions for IDs: {', '.join(missing_ids)}")

            return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        pass

    # Fallback: create placeholder descriptions
    return {
        "descriptions": [
            {
                "id": conn["id"],
                "description": f"Connection from {conn['from_var']} to {conn['to_var']}"
            }
            for conn in connections
        ],
        "notes": [f"Failed to parse LLM response, using placeholder descriptions: {response[:200]}..."]
    }

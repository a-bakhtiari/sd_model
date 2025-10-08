"""Generate descriptions for feedback loops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ..llm.client import LLMClient


def generate_loop_descriptions(
    loops_data: Dict,
    llm_client: LLMClient,
    out_path: Path,
    domain_context: str = "open source software development"
) -> Dict:
    """
    Generate brief descriptions for each feedback loop.

    Args:
        loops_data: Loop data from loops.json
        llm_client: LLM client for generating descriptions
        out_path: Path to write loop_descriptions.json
        domain_context: Domain context for better descriptions

    Returns:
        Dict with loop descriptions
    """
    # Collect all loops (reinforcing and balancing)
    all_loops = []

    for loop in loops_data.get("reinforcing", []):
        all_loops.append({
            "id": loop.get("id", ""),
            "loop_type": "reinforcing",
            "variables": " → ".join(loop.get("variables", [])),
            "existing_description": loop.get("description", "")
        })

    for loop in loops_data.get("balancing", []):
        all_loops.append({
            "id": loop.get("id", ""),
            "loop_type": "balancing",
            "variables": " → ".join(loop.get("variables", [])),
            "existing_description": loop.get("description", "")
        })

    if not all_loops:
        result = {"descriptions": [], "notes": ["No loops to describe"]}
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # Create prompt for LLM
    prompt = _create_description_prompt(all_loops, domain_context)

    try:
        response = llm_client.complete(prompt, temperature=0.1)
        result = _parse_description_response(response, all_loops)
    except Exception as e:
        result = {
            "descriptions": [],
            "notes": [f"LLM description generation failed: {str(e)}"]
        }

    # Write to file
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _create_description_prompt(loops: list, domain_context: str) -> str:
    """Create prompt for LLM to generate loop descriptions."""

    loops_info = "\n".join([
        f"  {loop['id']} ({loop['loop_type']}): {loop['variables']}"
        for loop in loops
    ])

    return f"""You are an expert in system dynamics and {domain_context}. Your task is to provide brief descriptions for feedback loops in a system dynamics model.

DOMAIN CONTEXT: {domain_context}

LOOPS TO DESCRIBE:
{loops_info}

TASK:
For each loop, provide a brief 1-2 sentence description explaining the feedback mechanism. Focus on WHY this creates reinforcing/balancing behavior and HOW it impacts the system.

GUIDELINES:
- Keep descriptions concise (1-2 sentences, ~20-40 words)
- Explain the feedback mechanism and system behavior
- For reinforcing loops: explain how changes amplify over time
- For balancing loops: explain how the system seeks equilibrium
- Use domain-appropriate language for {domain_context}

OUTPUT FORMAT (JSON only, no additional text):
{{
  "descriptions": [
    {{"id": "R01", "description": "This virtuous cycle amplifies project success as reputation attracts contributors who improve quality, further enhancing reputation"}},
    {{"id": "B01", "description": "This balancing loop prevents unbounded issue accumulation by creating pressure to resolve issues as they build up"}},
    ...
  ]
}}

IMPORTANT: Output ONLY the IDs and descriptions. Do not repeat the full loop details.

Your response (JSON only):"""


def _parse_description_response(response: str, loops: list) -> Dict:
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

            return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        pass

    # Fallback: create placeholder descriptions
    return {
        "descriptions": [
            {
                "id": loop["id"],
                "description": f"{loop['loop_type'].capitalize()} loop: {loop['variables']}"
            }
            for loop in loops
        ],
        "notes": [f"Failed to parse LLM response, using placeholder descriptions: {response[:200]}..."]
    }

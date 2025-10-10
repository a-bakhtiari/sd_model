"""
Module 2: Theory Enhancement Suggester

Takes core model analysis and generates specific SD implementation suggestions
for missing theory elements and model improvements.
"""
from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def create_enhancement_prompt(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> str:
    """Create prompt for theory enhancement suggestions."""

    # Calculate basic stats
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Get sample variables
    sample_vars = variables.get("variables", [])[:8]
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in sample_vars
    ])

    # Get sample connections
    sample_conns = connections.get("connections", [])[:8]
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in sample_conns
    ])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in theories
    ])

    prompt = f"""You are a system dynamics modeling expert specializing in Communities of Practice and Knowledge Management theories for open-source software development.

# Current System Dynamics Model

## Model Summary
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

## Sample Variables
{vars_text}

## Sample Connections
{conns_text}

# Theories Being Used
{theories_text}

# Your Task

Analyze the model and identify what needs to be added, modified, or removed based on each theory.

For each theory, provide specific model operations:

1. **Additions** - New variables and connections to add
2. **Modifications** - Existing variables to update (optional, leave empty if none)
3. **Removals** - Variables to deprecate or remove (optional, leave empty if none)

Return JSON in this structure:

{{
  "theories": [
    {{
      "name": "Theory Name",
      "additions": {{
        "variables": [
          {{
            "name": "Variable Name",
            "type": "Stock|Flow|Auxiliary",
            "description": "what it represents"
          }}
        ],
        "connections": [
          {{
            "from": "Variable A",
            "to": "Variable B",
            "relationship": "positive|negative"
          }}
        ]
      }},
      "modifications": {{
        "variables": []
      }},
      "removals": {{
        "variables": []
      }}
    }}
  ]
}}

IMPORTANT:
- Focus on practical, implementable operations
- Be specific about variable names and types
- Only include modifications/removals if truly needed
- For additions.connections, you can reference both existing variables and newly added variables

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_theory_enhancement(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> Dict:
    """Generate theory enhancement suggestions.

    Args:
        theories: List of theory dictionaries from theories.csv
        variables: Variables data from variables_llm.json
        connections: Connections data from connections.json
        loops: Loops data from loops.json

    Returns:
        Dictionary with theory enhancement suggestions
    """

    # Create prompt
    prompt = create_enhancement_prompt(theories, variables, connections, loops)

    # Call LLM
    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.2, max_tokens=4000)

    # Parse response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        return {"error": str(e), "raw_response": response}

    return result

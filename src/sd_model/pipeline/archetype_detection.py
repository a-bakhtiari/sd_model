"""
System Archetype Detection Module

Analyzes SD models to detect common system dynamics archetypes and suggests
missing variables/connections to complete archetype patterns.
"""
from __future__ import annotations

import json
from typing import Dict

from ..llm.client import LLMClient


def create_archetype_prompt(variables: Dict, connections: Dict) -> str:
    """Create prompt for archetype detection."""

    # Get all variables
    all_vars = variables.get("variables", [])
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in all_vars
    ])

    # Get all connections and convert to name-based format if needed
    all_conns = connections.get("connections", [])

    # Check if connections are ID-based or name-based
    if all_conns and 'from' in all_conns[0]:
        # ID-based connections - convert to names
        vars_by_id = {v['id']: v for v in all_vars}
        name_based_conns = []
        for conn in all_conns:
            from_id = conn.get('from')
            to_id = conn.get('to')
            if from_id in vars_by_id and to_id in vars_by_id:
                from_var = vars_by_id[from_id]['name']
                to_var = vars_by_id[to_id]['name']
                polarity = conn.get('polarity', 'UNDECLARED').lower()
                relationship = 'positive' if polarity == 'positive' else 'negative' if polarity == 'negative' else 'undeclared'
                name_based_conns.append({
                    'from_var': from_var,
                    'to_var': to_var,
                    'relationship': relationship
                })
        all_conns = name_based_conns

    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in all_conns
    ])

    prompt = f"""You are a system dynamics modeling expert.

# Current System Dynamics Model

## Current Variables
{vars_text}

## Current Connections
{conns_text}

# Your Task

Analyze this model and identify which **System Archetypes** from Senge and Meadows match the current system structure and could improve the model by making implicit archetype patterns explicit.

## System Archetypes to Consider

**Senge's 10 Classic Archetypes:**
1. Balancing Process with Delay
2. Limits to Growth (Limits to Success)
3. Shifting the Burden
4. Shifting the Burden to the Intervenor
5. Eroding Goals (Drifting Goals)
6. Escalation
7. Success to the Successful
8. Tragedy of the Commons
9. Fixes that Fail (Fixes that Backfire)
10. Growth and Underinvestment

**Meadows' System Traps:**
1. Policy Resistance
2. Tragedy of the Commons
3. Drift to Low Performance (Eroding Goals)
4. Escalation
5. Success to the Successful (Competitive Exclusion)
6. Shifting the Burden (Addiction/Dependence)
7. Rule Beating
8. Seeking the Wrong Goal

# Analysis Process

For each applicable archetype:

1. **Identify existing structure**: Which variables and connections represent parts of this archetype?
2. **Explain the match**: Why does this archetype pattern fit the current system?
3. **Identify gaps**: What variables/connections are missing to complete the archetype?
4. **Suggest additions**: Specific variables and connections to add

## Variable Naming Conventions

✅ **Good**: Specific and descriptive
- "Growth Pressure"
- "Constraint Awareness"
- "Resource Depletion Rate"

❌ **Avoid**: Vague or generic
- "Pressure" (pressure for what?)
- "Awareness" (awareness of what?)
- "Rate" (rate of what?)

## Connection Design Rules

For each connection:
- **from**: Source variable (can be existing OR newly added)
- **to**: Target variable (can be existing OR newly added)
- **relationship**:
  - "positive": Increase in FROM → Increase in TO
  - "negative": Increase in FROM → Decrease in TO
- **rationale**: Brief explanation of why this connection completes the archetype

## Quality Criteria

Your suggestions must be:
✓ Based on well-established system archetypes from SD literature
✓ Implementable in Vensim system dynamics software
✓ Connected to existing model elements (not isolated additions)
✓ Using specific, descriptive variable names

## Output Format

Return JSON in this structure:

{{
  "archetypes": [
    {{
      "name": "Archetype Name",
      "rationale": "Explain which elements of this archetype are present in the model and why this pattern matches (2-4 sentences).",
      "additions": {{
        "variables": [
          {{
            "name": "Variable Name",
            "type": "Stock|Flow|Auxiliary",
            "description": "what it represents",
            "rationale": "why needed to complete archetype"
          }}
        ],
        "connections": [
          {{
            "from": "Variable A",
            "to": "Variable B",
            "relationship": "positive|negative",
            "rationale": "why this connection completes the archetype"
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
- Only include the MOST APPLICABLE archetypes - typically 2-3, but could be fewer or more depending on what you actually find in the model
- Do NOT force weak matches - better to include 1 strong archetype than 5 weak ones
- Only include additions if truly needed to complete the archetype pattern
- Be specific about variable names, types, and rationales
- Modifications and removals are usually empty for archetype detection

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def detect_archetypes(
    variables: Dict,
    connections: Dict
) -> Dict:
    """Detect system archetypes in the model.

    Args:
        variables: Variables data from variables.json
        connections: Connections data from connections.json

    Returns:
        Dictionary with archetype detection results
    """

    # Create prompt
    prompt = create_archetype_prompt(variables, connections)

    # Call LLM (use config to determine provider/model)
    from ..config import should_use_gpt
    from ..llm.client import LLMClient

    provider, model = should_use_gpt("archetype_detection")
    client = LLMClient(provider=provider, model=model)
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
        return {
            "error": str(e),
            "raw_response": response,
            "archetypes": []
        }

    return result

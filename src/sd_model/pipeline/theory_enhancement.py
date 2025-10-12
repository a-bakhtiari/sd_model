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

    # Get all variables
    all_vars = variables.get("variables", [])
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in all_vars
    ])

    # Get all connections
    all_conns = connections.get("connections", [])
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in all_conns
    ])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in theories
    ])

    prompt = f"""You are a system dynamics modeling expert, specialized in system design and modeling.

# Current System Dynamics Model

## Current Variables
{vars_text}

## Current Connections
{conns_text}

# Theories Being Used
{theories_text}

# Your Task

For each theory, follow this structured process:

1. **Map theory to model**: Identify which core concepts from the theory are already modeled
2. **Identify gaps**: Find theory concepts that are missing or underutilized
3. **Design SD implementation**: Specify variables and connections to add
4. **Provide operations**: Additions, modifications, or removals

---

## Important Context

**Model Format**: We are using the Stock, Flow, Auxiliary format for this model. All standard system dynamics modeling conventions apply.

**Theory Applicability**: Some of the theories are new and I have not included them in the current model. I am trying to find ways to add them if applicable. For this reason, they may or may not apply to our context, but I put them there to see if you can apply them or not. If a theory does not apply, explain why in the rationale and do not suggest any changes from it. But if the theory does apply, then suggest changes, additions, etc.

**Model Design Goals**: The purpose of including new theories or modifications is to improve model's accuracy, completeness, and logical consistency. These new theories may also help me make a more robust model. This is a conceptualization step, but a model that can later work better in the simulation step as well.

**Modularity Principle**: I am going to prepare a visual version of this model, so when providing new connections, my preference is modularity. Design modular sub-processes (2-5 interconnected variables) that integrate with existing model elements through 1-3 clear connection points. By keeping this design principle, I can later visualize the model better and it is easier to understand and keep track of everything.

---

## SD Variable Type Guidelines

When designing new variables, use these decision rules:

- **Stock**: Accumulations that persist over time (people, knowledge, reputation, technical debt, etc.)
- **Flow**: Rates of change that modify stocks (hiring rate, learning rate, knowledge decay rate, etc.)
- **Auxiliary**: Calculated values, multipliers, ratios, effectiveness measures, etc.

---

## Variable Naming Conventions

✅ **Good**: Specific and descriptive
- "Project's Explicit Knowledge"
- "Core Developer Mentoring Capacity"
- "Newcomer Onboarding Rate"

❌ **Avoid**: Vague or generic
- "Knowledge" (knowledge of what?)
- "Capacity" (capacity for what?)
- "Rate" (rate of what?)

Be specific and use domain-appropriate language.

---

## Connection Design Rules

For each connection, specify:
- **from**: Source variable (can be existing OR newly added)
- **to**: Target variable (can be existing OR newly added)
- **relationship**:
  - "positive": Increase in FROM → Increase in TO
  - "negative": Increase in FROM → Decrease in TO

---

## Output Format

For each theory, include:
- **rationale**: A short paragraph (2-4 sentences) explaining the logic for why these suggestions are good or necessary for this specific theory

Return JSON in this structure:

{{
  "theories": [
    {{
      "name": "Theory Name",
      "rationale": "Short paragraph (2-4 sentences) explaining why these suggestions are necessary and how they strengthen the model's alignment with this theory.",
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
- Only include additions/modifications/removals if truly needed (all are optional)
- Focus on practical, implementable operations
- Be specific about variable names and types

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
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        loops: Loops data from loops.json

    Returns:
        Dictionary with theory enhancement suggestions
    """

    # Create prompt
    prompt = create_enhancement_prompt(theories, variables, connections, loops)

    # Call LLM (use config to determine provider/model)
    from ..config import should_use_gpt
    provider, model = should_use_gpt("theory_enhancement")
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
        return {"error": str(e), "raw_response": response}

    return result

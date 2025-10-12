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

    # Example clustering template (not f-string to avoid nested brace issues)
    clustering_example = """
### Example Clustering:

```json
"clustering_scheme": {
  "rationale": "The theories emphasize knowledge flows and community learning, suggesting three modules: knowledge management (creation/storage), contributor development (learning/progression), and community dynamics (engagement/mentoring).",
  "clusters": [
    {
      "name": "Knowledge Management",
      "theme": "Creation, storage, and transfer of explicit and tacit knowledge",
      "variables": ["Project Documentation", "Doc Creation Rate", "Explicit Knowledge Transfer", "Ba (Shared Context)"],
      "connections_to_other_clusters": {
        "Contributor Development": 8,
        "Community Dynamics": 5
      }
    },
    {
      "name": "Contributor Development",
      "theme": "Progression from newcomers through skill development to core roles",
      "variables": ["New Contributors", "Skill Up", "Experienced Contributors", "Core Developer", "Promotion Rate"],
      "connections_to_other_clusters": {
        "Knowledge Management": 8,
        "Community Dynamics": 12
      }
    },
    {
      "name": "Community Dynamics",
      "theme": "Social interactions, mentoring, and engagement mechanisms",
      "variables": ["Mentoring", "Engagement Level", "Community Capacity", "Turnover"],
      "connections_to_other_clusters": {
        "Knowledge Management": 5,
        "Contributor Development": 12
      }
    }
  ],
  "layout_hints": [
    "Place Contributor Development centrally - it has most connections (20 total)",
    "Position Knowledge Management on left, Community Dynamics on right",
    "This arrangement minimizes crossing lines between Knowledge and Community",
    "Keep clusters 400-600px apart for visual separation"
  ]
}
```
"""

    # JSON schema template (not f-string to avoid nested brace issues)
    json_schema = """
---

## Output Format

For each theory, include:
- **rationale**: A short paragraph (2-4 sentences) explaining the logic for why these suggestions are good or necessary for this specific theory

Return JSON in this structure:

{
  "clustering_scheme": {
    "rationale": "1-2 sentences explaining the clustering logic",
    "clusters": [
      {
        "name": "Cluster Name",
        "theme": "What this cluster represents",
        "variables": ["All variable names in this cluster"],
        "connections_to_other_clusters": {"Other Cluster": count}
      }
    ],
    "layout_hints": ["hint 1", "hint 2", ...]
  },
  "theories": [
    {
      "name": "Theory Name",
      "rationale": "Short paragraph (2-4 sentences) explaining why these suggestions are necessary and how they strengthen the model's alignment with this theory.",
      "additions": {
        "variables": [
          {
            "name": "Variable Name",
            "type": "Stock|Flow|Auxiliary",
            "description": "what it represents"
          }
        ],
        "connections": [
          {
            "from": "Variable A",
            "to": "Variable B",
            "relationship": "positive|negative"
          }
        ]
      },
      "modifications": {
        "variables": []
      },
      "removals": {
        "variables": []
      }
    }
  ]
}

IMPORTANT:
- **clustering_scheme is REQUIRED** - must analyze and group ALL variables
- Only include additions/modifications/removals if truly needed (all are optional)
- Focus on practical, implementable operations
- Be specific about variable names and types
- Clustering should consider connection topology to minimize crossing lines

Return ONLY the JSON structure, no additional text.
"""

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

## CRITICAL: Propose Complete Clustering Scheme

After suggesting additions, you MUST propose how to organize ALL variables (existing + new) into conceptual clusters.

### Why Clustering Matters:
- Enables visual grouping in the diagram
- Minimizes crossing connection lines
- Makes the model easier to understand
- Respects modular design principles

### Clustering Task:

1. **Analyze ALL variables** through the lens of the theories you're applying
2. **Group into 3-5 conceptual clusters** based on:
   - Semantic similarity (what theme/process they represent)
   - Connection topology (tightly connected variables should cluster together)
   - Theory-driven organization (how theories conceptualize the system)

3. **Count inter-cluster connections** to inform spatial layout

4. **Provide layout hints** for positioning clusters to minimize line crossings

### Clustering Output Requirements:

For each cluster, provide:
- **name**: Short cluster name (e.g., "Knowledge Creation", "Contributor Pipeline")
- **theme**: 1-2 sentence description of what this cluster represents
- **variables**: List of ALL variable names in this cluster (existing + new)
- **connections_to_other_clusters**: Dict mapping other cluster names to connection count

Then provide:
- **layout_hints**: 2-4 strategic hints for spatial arrangement (e.g., "Place Knowledge cluster centrally since it connects to all others", "Position Team and Community clusters adjacent to minimize crossing lines")
"""

    # Combine all parts (avoid nested braces in f-string)
    return prompt + clustering_example + json_schema


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

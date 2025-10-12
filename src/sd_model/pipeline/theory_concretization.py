"""
Step 2: Concrete SD Element Generation

Takes strategic plan from Step 1 and generates specific variables/connections
with proper naming, types, and cluster assignments.
"""
from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def create_concretization_prompt(
    planning_result: Dict,
    variables: Dict,
    connections: Dict
) -> str:
    """Create prompt for concrete SD element generation (Step 2)."""

    # Extract strategic plan from Step 1
    theory_decisions = planning_result.get('theory_decisions', [])
    clustering_strategy = planning_result.get('clustering_strategy', {})

    # Filter to only included/adapted theories
    active_theories = [
        t for t in theory_decisions
        if t.get('decision') in ['include', 'adapt']
    ]

    # Format current model
    all_vars = variables.get("variables", [])
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in all_vars
    ])

    all_conns = connections.get("connections", [])
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in all_conns
    ])

    # Format strategic plan
    theories_plan_text = "\n".join([
        f"**{t['theory_name']}** ({t['decision']})\n"
        f"  Rationale: {t['rationale']}\n"
        f"  Conceptual additions: {', '.join(t.get('conceptual_additions', []))}"
        for t in active_theories
    ])

    # Format clustering strategy
    clusters_text = "\n".join([
        f"**{c['name']}**: {c['theme']}\n"
        f"  Existing: {', '.join(c.get('should_contain_existing', []))}\n"
        f"  New concepts: {', '.join(c.get('should_contain_new', []))}\n"
        f"  Spatial: {c.get('spatial_recommendation', 'N/A')}"
        for c in clustering_strategy.get('clusters', [])
    ])

    prompt = f"""You are a system dynamics modeling expert. Your task is to generate CONCRETE variables and connections based on the strategic plan from Step 1.

# Current Model

## Variables ({len(all_vars)} total)
{vars_text}

## Connections ({len(all_conns)} total)
{conns_text}

---

# Strategic Plan from Step 1

## Active Theories (include/adapt)
{theories_plan_text}

## Clustering Strategy
{clusters_text}

---

# Your Task: Generate Concrete SD Elements

For EACH conceptual addition from the strategic plan, create specific variables and connections.

## Variable Design Guidelines

**Naming Conventions:**
✅ **Good**: Specific and descriptive
  - "Project's Explicit Knowledge"
  - "Core Developer Mentoring Capacity"
  - "Newcomer Onboarding Rate"

❌ **Avoid**: Vague or generic
  - "Knowledge" (knowledge of what?)
  - "Capacity" (capacity for what?)
  - "Rate" (rate of what?)

**Type Selection:**
- **Stock**: Accumulations that persist (people, knowledge, reputation, technical debt)
- **Flow**: Rates of change modifying stocks (learning rate, knowledge decay rate)
- **Auxiliary**: Calculated values, multipliers, ratios, effectiveness measures

## Connection Design Rules

For each connection:
- **from**: Source variable (existing OR newly added)
- **to**: Target variable (existing OR newly added)
- **relationship**:
  - "positive": Increase in FROM → Increase in TO
  - "negative": Increase in FROM → Decrease in TO
- **rationale**: Brief explanation (1 sentence)

## Cluster Assignment

EVERY new variable MUST be assigned to one of the clusters from Step 1:
{', '.join([c['name'] for c in clustering_strategy.get('clusters', [])])}

The cluster assignment guides spatial positioning in Step 3.

---

## Critical Instructions

✓ **DO generate specific variable names** (this is where you name them properly)
✓ **DO specify connections** (both to existing vars and between new vars)
✓ **DO assign every variable to a cluster** from Step 1
✓ **DO ensure connections integrate new elements with existing model**
⚠️ **DO NOT generate isolated variables** - must connect to existing or other new vars
⚠️ **DO NOT duplicate existing variable names** - check current model first

---

## Output Format

Return ONLY valid JSON in this structure (no markdown, no explanation):

{{
  "theories": [
    {{
      "theory_name": "Theory Name",
      "rationale": "2-3 sentences explaining how these specific additions strengthen model alignment with this theory",
      "additions": {{
        "variables": [
          {{
            "name": "Specific Variable Name",
            "type": "Stock|Flow|Auxiliary",
            "description": "What it represents",
            "cluster": "Cluster Name from Step 1",
            "source_theory": "Theory Name",
            "rationale": "Why needed for this theory"
          }}
        ],
        "connections": [
          {{
            "from": "Variable A (existing or new)",
            "to": "Variable B (existing or new)",
            "relationship": "positive|negative",
            "rationale": "Brief explanation"
          }}
        ]
      }}
    }}
  ],
  "organized_by_cluster": {{
    "Cluster Name": {{
      "new_variables": ["list of new variable names in this cluster"],
      "new_connections_internal": 5,
      "new_connections_external": 8,
      "integration_note": "How this cluster integrates with existing model"
    }}
  }},
  "summary": {{
    "total_variables_added": 12,
    "total_connections_added": 18,
    "theories_applied": 3,
    "clusters_affected": ["Cluster A", "Cluster B"]
  }}
}}

**Remember**: Use the strategic plan from Step 1 as your guide. Transform conceptual additions into concrete, well-named SD elements that integrate seamlessly with the existing model.
"""

    return prompt


def run_theory_concretization(
    planning_result: Dict,
    variables: Dict,
    connections: Dict,
    llm_client: LLMClient = None
) -> Dict:
    """Execute Step 2: Concrete SD Element Generation.

    Args:
        planning_result: Output from Step 1 (theory_planning)
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        llm_client: Optional LLM client (creates new if None)

    Returns:
        Dict with concrete variables and connections:
        {
            "theories": [{
                "theory_name": "...",
                "additions": {"variables": [...], "connections": [...]}
            }],
            "organized_by_cluster": {...},
            "summary": {...}
        }
    """

    # Check if Step 1 had errors
    if "error" in planning_result:
        return {
            "error": "Step 1 (planning) failed, cannot proceed to Step 2",
            "planning_error": planning_result.get("error"),
            "theories": []
        }

    # Create prompt
    prompt = create_concretization_prompt(planning_result, variables, connections)

    # Call LLM
    if llm_client is None:
        from ..config import should_use_gpt
        provider, model = should_use_gpt("theory_concretization")
        llm_client = LLMClient(provider=provider, model=model)

    response = llm_client.complete(prompt, temperature=0.2, max_tokens=4500)

    # Parse response
    try:
        # Extract JSON from response (handle markdown code blocks)
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")

        # Attach clustering strategy from Step 1 for Step 3
        result['clustering_strategy'] = planning_result.get('clustering_strategy', {})

        return result

    except Exception as e:
        return {
            "error": str(e),
            "raw_response": response,
            "theories": []
        }


def convert_to_legacy_format(concretization_result: Dict) -> Dict:
    """Convert Step 2 output to legacy theory_enhancement format.

    This allows the existing MDL enhancement code to consume decomposed output
    without modification.

    Args:
        concretization_result: Output from Step 2

    Returns:
        Dict in legacy theory_enhancement.py format
    """

    # Extract theories from Step 2 output
    theories = concretization_result.get('theories', [])
    clustering_strategy = concretization_result.get('clustering_strategy', {})

    # Legacy format wraps everything
    legacy_output = {
        'clustering_scheme': clustering_strategy,  # Already in correct format
        'theories': []
    }

    # Convert each theory to legacy format
    for theory in theories:
        legacy_theory = {
            'name': theory.get('theory_name'),
            'rationale': theory.get('rationale'),
            'additions': theory.get('additions', {}),
            'modifications': {'variables': []},  # Decomposed approach doesn't modify
            'removals': {'variables': []}  # Decomposed approach doesn't remove
        }
        legacy_output['theories'].append(legacy_theory)

    return legacy_output

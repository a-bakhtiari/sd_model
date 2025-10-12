"""
Step 1: Strategic Theory Planning

Evaluates theory applicability and creates high-level clustering strategy
with spatial awareness. Does NOT generate concrete variables yet.
"""
from __future__ import annotations

import json
from typing import Dict, List
from pathlib import Path

from ..llm.client import LLMClient
from .spatial_analysis import analyze_spatial_layout


def create_planning_prompt(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    spatial_context: Dict
) -> str:
    """Create prompt for strategic theory planning (Step 1)."""

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

    # Format theories
    theories_text = "\n".join([
        f"{i+1}. **{t['name']}**: {t['description']}"
        for i, t in enumerate(theories)
    ])

    # Format spatial context
    spatial_summary = spatial_context.get('spatial_summary', 'No spatial analysis available')

    prompt = f"""You are a system dynamics modeling expert. Your task is to strategically plan theory enhancements WITHOUT generating concrete variables yet. This is Step 1 of 2.

# Current System Dynamics Model

## Variables ({len(all_vars)} total)
{vars_text}

## Connections ({len(all_conns)} total)
{conns_text}

# Current Spatial Layout

{spatial_summary}

# Theories to Evaluate ({len(theories)} total)

{theories_text}

---

# Your Task: Strategic Planning ONLY

You must perform THREE distinct analyses:

## 1. Theory Evaluation

For EACH theory, decide:
- **include**: Theory clearly applies, will enhance model
- **exclude**: Theory doesn't fit this context
- **adapt**: Theory partially applies, needs modification

For each theory, provide:
- Decision (include/exclude/adapt)
- Rationale (2-3 sentences explaining why)
- Conceptual additions (high-level concepts, NOT variable names yet)
  - Example: "concept: tacit knowledge accumulation process"
  - Example: "concept: mentor-mentee interaction dynamics"

## 2. Clustering Strategy

Based on included theories, design 3-5 conceptual clusters to organize ALL variables (existing + new):

For each cluster:
- **name**: Short cluster name (e.g., "Knowledge Creation")
- **theme**: What this cluster represents conceptually
- **should_contain_existing**: List existing variable names that belong here
- **should_contain_new**: List NEW concepts (from theory evaluation) that belong here
- **rationale**: Why these elements cluster together

Consider:
- Semantic similarity (related processes/themes)
- Connection topology (tightly connected elements cluster together)
- Theory-driven organization (how theories conceptualize the system)

## 3. Spatial Strategy

Based on current layout and clustering:

For each cluster:
- **spatial_recommendation**: Where to position (refer to spatial analysis above)
  - Example: "Place centrally near (1000, 500) - available space and high connectivity"
  - Example: "Position in top-left (400, 300) - currently empty region"
  - Example: "Keep near existing Knowledge variables (600-800, 200-400)"

Also provide:
- **layout_hints**: 2-3 strategic hints for minimizing line crossings
  - Example: "Place Knowledge cluster centrally since it connects to all others"
  - Example: "Position Contributor and Community clusters adjacent (they have 15 connections)"

---

## Critical Instructions

⚠️ **DO NOT generate variable names** - use conceptual descriptions only
⚠️ **DO NOT specify connections yet** - focus on clustering strategy
✓ **DO leverage spatial analysis** - recommend specific regions based on crowding/availability
✓ **DO consider theory conflicts** - if theories overlap, note this in rationale
✓ **DO think holistically** - evaluate all theories together, not in isolation

---

## Output Format

Return ONLY valid JSON in this structure (no markdown, no explanation):

{{
  "theory_decisions": [
    {{
      "theory_name": "Theory Name",
      "decision": "include|exclude|adapt",
      "rationale": "2-3 sentence explanation of why this decision was made",
      "conceptual_additions": [
        "concept: high-level description of what to add (NO variable names)",
        "concept: another conceptual addition"
      ]
    }}
  ],
  "clustering_strategy": {{
    "rationale": "1-2 sentences explaining the overall clustering logic",
    "clusters": [
      {{
        "name": "Cluster Name",
        "theme": "What this cluster represents",
        "should_contain_existing": ["Existing Var 1", "Existing Var 2"],
        "should_contain_new": ["concept: new concept 1", "concept: new concept 2"],
        "rationale": "Why these elements cluster together",
        "spatial_recommendation": "Where to position this cluster (reference spatial analysis)"
      }}
    ],
    "layout_hints": [
      "Strategic hint for positioning clusters to minimize crossings",
      "Another positioning strategy"
    ]
  }},
  "inter_cluster_connections": [
    {{
      "from_cluster": "Cluster A",
      "to_cluster": "Cluster B",
      "estimated_connection_count": 8,
      "note": "Brief note about the nature of these connections"
    }}
  ]
}}

**Remember**: This is strategic planning ONLY. No concrete variable names or connections yet. Focus on concepts, clustering logic, and spatial strategy.
"""

    return prompt


def run_theory_planning(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    mdl_path: Path,
    llm_client: LLMClient = None
) -> Dict:
    """Execute Step 1: Strategic Theory Planning.

    Args:
        theories: List of theory dictionaries
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        mdl_path: Path to current MDL file (for spatial analysis)
        llm_client: Optional LLM client (creates new if None)

    Returns:
        Dict with strategic planning results:
        {
            "theory_decisions": [...],
            "clustering_strategy": {...},
            "inter_cluster_connections": [...]
        }
    """

    # Analyze current spatial layout
    spatial_context = analyze_spatial_layout(mdl_path)

    # Create prompt
    prompt = create_planning_prompt(theories, variables, connections, spatial_context)

    # Call LLM
    if llm_client is None:
        from ..config import should_use_gpt
        provider, model = should_use_gpt("theory_planning")
        llm_client = LLMClient(provider=provider, model=model)

    response = llm_client.complete(prompt, temperature=0.2, max_tokens=3500)

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

        # Add spatial context to result for reference in Step 2
        result['spatial_context'] = spatial_context

        return result

    except Exception as e:
        return {
            "error": str(e),
            "raw_response": response,
            "theory_decisions": [],
            "clustering_strategy": {}
        }

"""
Step 2: Theory Concretization - Condensed Version

Transforms process narratives from Step 1 into concrete SD variables and connections.
Much more concise than the verbose version while maintaining quality.
"""
from __future__ import annotations

import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from ..llm.client import LLMClient


def create_concretization_prompt(
    planning_result: Dict,
    variables: Dict,
    connections: Dict,
    plumbing: Dict = None,
    recreate_mode: bool = False
) -> str:
    """Create prompt for theory concretization (Step 2) - CONDENSED VERSION.

    Args:
        planning_result: Output from Step 1 (strategic planning)
        variables: Current model variables (may be empty in recreate mode)
        connections: Current model connections (may be empty in recreate mode)
        plumbing: Optional plumbing data for boundary flows
        recreate_mode: If True, building complete model from scratch

    Returns:
        Prompt string for LLM
    """

    # Extract clustering strategy from planning result
    clustering_strategy = planning_result.get('clustering_strategy', {})
    clusters = clustering_strategy.get('clusters', [])
    overall_narrative = clustering_strategy.get('overall_narrative', '')

    # Build process narratives text
    processes_text = "\n\n".join([
        f"### {cluster['name']}\n{cluster['narrative']}\n\nConnections: {cluster.get('connections_to_other_clusters', [])}"
        for cluster in clusters
    ])

    # Build inter-cluster connections text
    inter_cluster_text = "\n".join([
        f"- {cluster['name']} → {conn['target_cluster']}: {conn['description']}"
        for cluster in clusters
        for conn in cluster.get('connections_to_other_clusters', [])
    ])

    # Mode-specific components
    if recreate_mode:
        mode_task = "**Your task**: Create a complete SD model from these narratives using SISO architecture."
        mode_io = "**Input**: Process narratives\n**Output**: Complete SD structure with all variables and connections"
        model_section = ""  # No current model in recreation mode
    else:
        # Format current model structure for enhancement mode
        model_structure = f"Current model has {len(variables.get('variables', []))} variables and {len(connections.get('connections', []))} connections."
        mode_task = "**Your task**: Enhance the existing model by adding theory-based elements."
        mode_io = "**Input**: Process narratives + existing model\n**Output**: New variables and connections to add"
        model_section = f"# Current Model\n{model_structure}\n---\n"

    prompt = f"""# Context

You are a system dynamics expert converting narratives into concrete SD elements.

{mode_task}

{mode_io}

---

{model_section}

# Process Narratives

## Overall Flow
{overall_narrative}

## Individual Processes
{processes_text}

## Inter-Cluster Connections
{inter_cluster_text}

---

# SD Design Principles

## 1. SISO Architecture (REQUIRED)
Each process must have EXACTLY ONE input and EXACTLY ONE output:
- Linear pipeline: Process A → Process B → Process C
- No hub-and-spoke, no many-to-one connections
- Each process transforms one input stream into one output stream

## 2. Canonical SD Patterns
Match narratives to these patterns:

**Aging Chain**: Progression through stages (Stock1 → Flow → Stock2 → Flow → Stock3)
**Stock Management**: Goal-seeking with balancing feedback (Gap → Adjustment → Stock → Gap)
**Diffusion**: S-curve growth with reinforcing feedback (adopter fraction drives adoption rate)
**Resource Cycles**: Depletion and regeneration flows
**Co-flow**: Bidirectional transfer between stock pairs

## 3. Variable Types

**STOCK**: Accumulations that persist (can count "how many now?")
- Units: people, documents, knowledge units, trust levels
- Test: Does it accumulate/deplete over time?

**FLOW**: Rates between stocks ONLY (never standalone)
- Units: things/time (people/month, documents/week)
- Must connect: Stock→Stock or Stock→Boundary

**AUXILIARY**: Calculated values, factors, multipliers
- Effectiveness (0-1), gaps, time constants, thresholds
- Enable feedback: Stock → Auxiliary → Flow → Stock

## 4. Requirements Per Process - SCALE WITH THEORY COMPLEXITY

Generate variables proportional to the richness of theories informing each process:

**For processes informed by 1-2 theories:**
• 4-6 Stocks
• 3-4 Flows
• 4-6 Auxiliaries

**For processes informed by 3-4 theories:**
• 6-8 Stocks
• 4-6 Flows
• 6-8 Auxiliaries

**For processes informed by 5+ theories:**
• 8-12 Stocks
• 6-8 Flows
• 8-12 Auxiliaries

Include SD elements that capture the essential mechanisms from theories informing this process.
✓ At least 1 feedback loop (reinforcing or balancing)
✓ SISO connections to other processes

## 5. Naming Convention
Be specific and descriptive:
- ✅ "Novice Contributors" not ❌ "Novices"
- ✅ "Documentation Creation Rate" not ❌ "Rate"
- ✅ "Mentoring Effectiveness" not ❌ "Effectiveness"

---

# Output Format

Return ONLY valid JSON:

{{
  "processes": [
    {{
      "process_name": "Process Name from Step 1",
      "variables": [
        {{"name": "Variable Name", "type": "Stock|Flow|Auxiliary"}}
      ],
      "connections": [
        {{
          "from": "Source Variable",
          "to": "Target Variable",
          "relationship": "positive|negative"
        }}
      ],
      "boundary_flows": [
        {{
          "name": "Flow Name",
          "type": "source|sink",
          "connects_to": "Stock Name"
        }}
      ]
    }}
  ],
  "cluster_positions": {{
    "Process Name": [row, column]
  }}
}}

CRITICAL: Include cluster_positions for spatial layout (2D grid positions).
"""

    return prompt


def run_theory_concretization(
    planning_result: Dict,
    variables: Dict,
    connections: Dict,
    plumbing: Dict = None,
    llm_client: LLMClient = None,
    recreate_mode: bool = False
) -> Dict:
    """Execute Step 2: Theory Concretization with condensed prompt.

    Args:
        planning_result: Output from Step 1 strategic planning
        variables: Current model variables
        connections: Current model connections
        plumbing: Optional plumbing data
        llm_client: Optional LLM client
        recreate_mode: If True, creating complete model from scratch

    Returns:
        Dict with concrete SD elements
    """

    # Create prompt
    prompt = create_concretization_prompt(
        planning_result,
        variables,
        connections,
        plumbing,
        recreate_mode=recreate_mode
    )

    # Call LLM
    if llm_client is None:
        from ..config import should_use_gpt
        import logging
        logger = logging.getLogger(__name__)
        provider, model = should_use_gpt("theory_concretization")
        logger.info(f"  → Step 2 using: {provider.upper()} ({model})")
        llm_client = LLMClient(provider=provider, model=model)

    response = llm_client.complete(prompt, temperature=0.3, max_tokens=16000)

    # Parse response
    try:
        # Extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")

        # Add clustering_strategy from Step 1 if not present
        if 'clustering_strategy' not in result:
            result['clustering_strategy'] = planning_result.get('clustering_strategy', {})

        return result

    except Exception as e:
        # Return error with whatever we got
        return {
            "error": str(e),
            "raw_response": response,
            "processes": [],
            "cluster_positions": {},
            "clustering_strategy": planning_result.get('clustering_strategy', {})
        }


def convert_to_legacy_format(concretization_result: Dict) -> Dict:
    """Convert Step 2 output to legacy theory_enhancement format.

    This allows the existing MDL enhancement code to consume decomposed output
    without modification.

    Args:
        concretization_result: Output from Step 2 with process-based structure

    Returns:
        Dict in legacy theory_enhancement.py format
    """

    # Extract processes from Step 2 output
    processes = concretization_result.get('processes', [])
    clustering_strategy = concretization_result.get('clustering_strategy', {})

    # Flatten all variables, connections, and boundary flows from all processes
    all_variables = []
    all_connections = []
    all_boundary_flows = []
    process_variable_map = {}  # process_name -> list of variable names

    for process in processes:
        process_name = process.get('process_name')
        process_vars = process.get('variables', [])
        process_conns = process.get('connections', [])
        process_boundaries = process.get('boundary_flows', [])

        # Collect variables
        all_variables.extend(process_vars)

        # Track which variables belong to which process
        var_names = [v.get('name') for v in process_vars]
        if process_name:
            process_variable_map[process_name] = var_names

        # Collect connections
        all_connections.extend(process_conns)

        # Collect boundary flows
        all_boundary_flows.extend(process_boundaries)

    # Build clustering_scheme with flat variable lists
    updated_clusters = []
    for cluster in clustering_strategy.get('clusters', []):
        cluster_name = cluster.get('name')

        # Get variables for this cluster from process mapping
        cluster_vars = process_variable_map.get(cluster_name, [])

        updated_cluster = cluster.copy()
        updated_cluster['variables'] = cluster_vars
        updated_clusters.append(updated_cluster)

    updated_clustering = clustering_strategy.copy()
    updated_clustering['clusters'] = updated_clusters

    # Create single theory entry with all additions (theory-agnostic)
    legacy_theory = {
        'name': 'Process-Based Enhancement',
        'rationale': 'Variables and connections generated from process narratives',
        'additions': {
            'variables': all_variables,
            'connections': all_connections,
            'boundary_flows': all_boundary_flows
        },
        'modifications': {'variables': []},  # Decomposed approach doesn't modify
        'removals': {'variables': []}  # Decomposed approach doesn't remove
    }

    # Legacy format wraps everything
    legacy_output = {
        'clustering_scheme': updated_clustering,
        'theories': [legacy_theory]
    }

    return legacy_output
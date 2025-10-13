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
    connections: Dict,
    plumbing: Dict = None,
    recreate_mode: bool = False
) -> str:
    """Create prompt for concrete SD element generation (Step 2).

    Args:
        recreate_mode: If True, prompts for generating a complete, self-contained model.
                      If False (default), prompts for enhancing existing model.
    """

    # Extract process narratives from Step 1
    clustering_strategy = planning_result.get('clustering_strategy', {})

    # Format model structure - skip entirely in recreation mode
    if recreate_mode:
        model_structure = None  # Will not show model in recreation mode
    else:
        from .theory_planning import format_model_structure
        model_structure = format_model_structure(variables, connections, plumbing)

    # Format process narratives from Step 1
    overall_narrative = clustering_strategy.get('overall_narrative', 'N/A')
    processes_text = "\n\n".join([
        f"**{c['name']}**:\n"
        f"  Narrative: {c.get('narrative', c.get('theme', 'N/A'))}\n"
        f"  Inputs: {c.get('inputs', 'N/A')}\n"
        f"  Outputs: {c.get('outputs', 'N/A')}"
        for c in clustering_strategy.get('clusters', [])
    ])

    # Mode-specific context
    if recreate_mode:
        mode_task = """**Your task**: Transform process narratives into specific variables, connections, and feedback loops **for a complete, self-contained model**. Generate ALL necessary variables - do not rely on existing model variables as they will not be present.

⚠️ **RECREATION MODE**: You are building a NEW model from scratch. Do not reference existing variables in connections unless you are also generating them. Ensure the model is complete and self-sufficient."""
        mode_io = """**Input**: Process narratives + overall system narrative
**Output**: Complete, self-contained modular processes with ALL necessary variables and connections"""
        model_section = ""  # No model shown in recreation mode
    else:
        mode_task = """**Your task**: Transform process narratives into specific variables, connections, and feedback loops **to enhance the existing model**. Each process is a self-contained mini-model with outputs that act as connection hubs between processes."""
        mode_io = """**Input**: Process narratives with inputs/outputs + overall system narrative + existing model
**Output**: Modular processes with concrete variables and connections"""
        model_section = f"""---

# Current Model

{model_structure}

---

"""

    prompt = f"""# Context

You are a system dynamics modeling expert converting process narratives into concrete SD elements.

{mode_task}

{mode_io}

---

{model_section}

# Process Narratives from Strategic Planning

## Overall System Flow
{overall_narrative}

## Individual Processes
{processes_text}

---

# Your Task: Convert Narratives to SD Elements

**Read the overall system narrative** to understand how processes connect as a cohesive whole.

Then **for EACH process narrative**, create:
1. **Stocks** - Accumulations described in the narrative
2. **Flows** - Rates of change connecting stocks
3. **Auxiliaries** - Calculated values, ratios, multipliers
4. **Connections** - Causal relationships implementing the narrative logic
5. **Hub outputs** - Key variables that connect this process to others

**Key Principle**: Each process is a modular mini-model. Process outputs become connection points (hubs) linking multiple processes together.

## Design Guidelines

**Variable Naming:**
✅ **Good**: Specific and descriptive
  - "Approved Materials Inventory"
  - "Production Line Capacity"
  - "Quality Inspection Rate"

❌ **Avoid**: Vague or generic
  - "Inventory" (inventory of what?)
  - "Capacity" (capacity for what?)
  - "Rate" (rate of what?)

**Type Selection:**
- **Stock**: Accumulations (inventory, people, knowledge, capacity)
  - Represented as rectangles in SD diagrams
  - Hold values that accumulate over time

- **Flow**: Rates connecting stocks (production rate, hiring rate)
  - Represented as pipes with valves
  - **CRITICAL**: Flows only exist between two Stocks OR between Stock and model boundary
  - Stock ↔ Stock: Internal flow (both stocks in model)
  - Stock ↔ Boundary: External flow (use `boundary_flows` array below)
  - If no Stock connection, use Auxiliary instead

- **Auxiliary**: Calculated values, multipliers, effectiveness measures
  - Support intermediate calculations
  - Plain text variables in SD diagrams

**Connection Design:**
- **from**: Source variable (existing OR new)
- **to**: Target variable (existing OR new)
- **relationship**: "positive" or "negative"
  - positive: Increase in FROM → Increase in TO
  - negative: Increase in FROM → Decrease in TO

---

## Critical Instructions

✓ **DO create modular processes** - each is self-contained with clear boundaries
✓ **DO identify hub outputs** - key variables connecting multiple processes
✓ **DO use the overall narrative** for coherence between processes
✓ **DO integrate with existing model** - connect new elements to existing variables
✓ **DO generate specific variable names** - descriptive and unambiguous
✓ **DO use Flow type ONLY between Stocks** - fundamental SD rule
⚠️ **DO NOT create isolated variables** - must connect to other variables
⚠️ **DO NOT duplicate existing variable names** - check current model first
⚠️ **DO NOT create Flows without Stock-to-Stock connections** - use Auxiliary instead

---

## Output Format

Return ONLY valid JSON in this structure (no markdown, no explanation):

{{
  "processes": [
    {{
      "process_name": "Process Name from Step 1",
      "variables": [
        {{
          "name": "Specific Variable Name",
          "type": "Stock|Flow|Auxiliary"
        }}
      ],
      "connections": [
        {{
          "from": "Variable A (existing or new)",
          "to": "Variable B (existing or new)",
          "relationship": "positive|negative"
        }}
      ],
      "boundary_flows": [
        {{
          "flow_name": "Flow Variable Name",
          "stock_name": "Stock Variable Name",
          "boundary_type": "source|sink",
          "description": "What the boundary represents (external labor market, environment, etc.)"
        }}
      ]
    }}
  ]
}}

**Notes**:
- Process names must match the cluster names from Step 1
- Variables in each process automatically belong to that process's cluster
- `boundary_flows` is OPTIONAL - only use when a Flow connects a Stock to external environment (not another stock in model)
  - `source`: External entity feeding INTO the model (e.g., labor market hiring into "Active Contributors")
  - `sink`: External entity draining FROM the model (e.g., contributors leaving to job market)
  - If both ends of a Flow are Stocks in the model, use `connections` instead, not `boundary_flows`

**Remember**: Transform each process narrative into a modular mini-model with concrete SD elements. Use the overall narrative to ensure processes connect coherently.
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
    """Execute Step 2: Concrete SD Element Generation.

    Args:
        planning_result: Output from Step 1 (theory_planning)
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        llm_client: Optional LLM client (creates new if None)
        recreate_mode: If True, prompts for generating complete, self-contained model

    Returns:
        Dict with concrete variables and connections organized by process:
        {
            "processes": [{
                "process_name": "...",
                "variables": [...],
                "connections": [...]
            }],
            "clustering_strategy": {...}  # Passed through from Step 1
        }
    """

    # Check if Step 1 had errors
    if "error" in planning_result:
        return {
            "error": "Step 1 (planning) failed, cannot proceed to Step 2",
            "planning_error": planning_result.get("error"),
            "processes": []
        }

    # Create prompt
    prompt = create_concretization_prompt(planning_result, variables, connections, plumbing, recreate_mode=recreate_mode)

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
            "processes": []
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

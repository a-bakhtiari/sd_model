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
    user_instructions_path: str = None,
    project_path: Path = None,
    recreate_mode: bool = False
) -> str:
    """Create prompt for theory concretization (Step 2) - CONDENSED VERSION.

    Args:
        planning_result: Output from Step 1 (strategic planning)
        variables: Current model variables (may be empty in recreate mode)
        connections: Current model connections (may be empty in recreate mode)
        plumbing: Optional plumbing data for boundary flows
        user_instructions_path: Optional path to user instructions file
        project_path: Optional project path for finding user instructions
        recreate_mode: If True, building complete model from scratch

    Returns:
        Prompt string for LLM
    """

    # Read user instructions if provided
    user_instructions = ""
    if user_instructions_path is None:
        # Default path: Look for project-specific step 2 instructions
        if project_path:
            user_instructions_path = project_path / "knowledge" / "user_instructions_step2.txt"

    if user_instructions_path and Path(user_instructions_path).exists():
        try:
            with open(user_instructions_path, 'r') as f:
                content = f.read().strip()
                # Filter out comment lines starting with #
                lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
                user_content = '\n'.join(lines).strip()
                if user_content:
                    user_instructions = f"\n## User-Specific Instructions\n\n{user_content}\n"
        except Exception as e:
            # Silently ignore if can't read file
            pass

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

Think step by step. Consider the task carefully: you need to identify SD elements (stocks, flows, auxiliaries) and their connections that are described in the narratives and create a complete and robust research grade system dynamics model in its entirety. You have the expertise to recognize accumulations, rates, and causal relationships when they appear in prose. Be precise.

This stage creates the causal diagram structure for now, but design it to be simulation-ready: proper stock-flow relationships and clear causal connections that will support future quantification and testing.

{mode_task}

{mode_io}

## Step 1 Design Decisions

Step 1 has planned a hierarchical system:
- **Process level**: Each process is its own mini-system with internal dynamics
- **Overall system level**: Processes connect to form the larger system
- **Connectivity**: Every process must connect to others (no isolated processes)

Your task: Implement these design decisions by identifying concrete SD elements.
{user_instructions}
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

## 1. SISO Architecture: Process Connections

SISO (Single Input Single Output) means each process is a modular unit with clear boundaries:

**Within each process:**
- Can have MULTIPLE stocks internally (2, 3, 4, or more stocks for internal dynamics)
- Can have MULTIPLE flows internally (connecting internal stocks)
- Can have ANY number of auxiliaries
- ALL internal connections stay within the process

**Between processes (SISO boundaries):**
- EXACTLY ONE designated input stock (receives flow from previous process)
- EXACTLY ONE designated output stock (sends flow to next process)
- NO other cross-process connections allowed (no auxiliaries or flows connecting across processes)

**Connection rules:**
- Output stock of Process A → Flow → Input stock of Process B
- Example: Process A's "Active Contributors" (output) → "Promotion Flow" → Process B's "Active Contributors" (input)
- The input stock of Process B may have the same name as output stock of Process A (they're the same accumulation)
- All other variables must ONLY connect within their own process

Implement the sequential pipeline specified in Step 1's `connections_to_other_clusters` (feeds_into connections).

## 2. Your Task: Identify SD Elements in Narratives

**CRITICAL**: The narratives from Step 1 already contain all the SD structure. Your job is pure extraction—identify what's already described, don't add elements not mentioned. If the narrative describes an accumulation, extract it as a stock. If it describes a rate, extract it as a flow. Be faithful to what's written.

**Identify Stocks** - Look for what accumulates or depletes over time:
- "A pool of X builds up..." → Stock: X Pool
- "Trust accumulates through..." → Stock: Trust Level
- "Knowledge depreciates when..." → Stock: Knowledge Base
- "The number of Y grows/shrinks..." → Stock: Y Count
- etc.

**Identify Flows** - Look for rates that change stocks:
- "Members transition at a rate of..." → Flow connecting two stocks
- "Creation occurs at a pace limited by..." → Flow into a stock
- "Depletion/exit happens when..." → Flow out of a stock
- Flows always connect Stock→Stock or Stock→Boundary or Boundary→Stock
- etc.

**Identify Auxiliaries** - Look for calculated values that aren't stocks or flows:
- "Rate is limited by available mentors..." → Auxiliary: Available Mentors
- "Effectiveness of 0.8 means..." → Auxiliary: Effectiveness Factor
- "Gap between target and actual..." → Auxiliary: Gap
- "Time constant of 3 months..." → Auxiliary: Time Constant

**Identify Clouds** - Look for system boundaries (sources/sinks):
- "Contributors enter from external job market..." → Cloud: External Job Market (source)
- "Contributors exit the system through attrition..." → Cloud: Attrition Sink (sink)
- Clouds represent the edge of your system boundary

**Connectivity requirement**: Every variable must connect to other variables WITHIN THE SAME PROCESS. No isolated variables—each stock, flow, and auxiliary should have causal relationships with other elements in its process. CRITICAL: Do not create connections to variables in other processes (except the designated input/output stock connections).

**Variable-Connection Consistency**: Every variable referenced in connections must first be extracted in the variables list. Extract all stocks/flows mentioned in narratives BEFORE creating connections to them. No dangling references.

**How many stocks per process?** Let the narrative guide you. Rich, multi-theory narratives naturally describe more accumulations. Simple narratives describe fewer. Don't force counts—extract what's actually described.

## 2.5 Common SD Patterns from the System Zoo

Step 1 used these patterns when crafting narratives. Recognizing them helps you extract the right SD elements:

### A. One-Stock with Competing Balancing Loops (Thermostat)
**Structure**: Two balancing loops pulling stock toward different goals | **Example**: Room temp (furnace heating vs. insulation loss)
**Behavior**: Stock settles where loops balance; equilibrium shifts if one loop strengthens
**Use when**: Goal-seeking with competing forces (quality vs. onboarding speed, documentation vs. velocity, debt vs. features)

### B. Reinforcing + Balancing Loop (Population/Capital Growth)
**Structure**: Reinforcing (growth) vs. balancing (constraint) | **Example**: Population (births vs. deaths), capital (investment vs. depreciation)
**Behavior**: Exponential growth if reinforcing dominates, decay if balancing dominates, equilibrium if equal; dominance shifts over time
**Use when**: Accumulation with growth and decline (contributor pools, knowledge bases, reputation, trust, capabilities, etc)

### C. System with Delays (Business Inventory)
**Structure**: Perception + response + delivery delays in balancing loops | **Example**: Car dealer ordering on delayed sales (averages trend, responds gradually, waits for delivery)
**Behavior**: Oscillations! Overshooting/undershooting target. Counterintuitively, acting faster worsens oscillations. Delays strongly determine behavior.
**Use when**: Information or physical responses take time (onboarding learning, code review queues, knowledge absorption, reputation building)

### D. Renewable Constrained by Nonrenewable (Oil Economy)
**Structure**: Capital grows (reinforcing), depletes finite resource | **Example**: Oil extraction (profit enables investment, but oil depletes until unprofitable)
**Behavior**: Exponential growth → peak → collapse as resource depletes. Doubling resource only slightly delays peak.
**Use when**: Consuming finite stocks (attention spans, legacy expertise, one-time adoption windows, initial enthusiasm, founding knowledge)

### E. Renewable Constrained by Renewable (Fishery)
**Structure**: Capital constrained by regenerating resource (regeneration can be damaged) | **Example**: Fishing fleet vs. fish population (regenerates fastest at moderate density)
**Behavior** (3 outcomes): (1) Sustainable equilibrium if feedback quick, (2) Oscillation if delayed, (3) Collapse if extraction exceeds regeneration threshold
**Critical**: High extraction efficiency can turn renewable into nonrenewable by allowing profitable harvest at dangerously low levels
**Use when**: Depending on regenerating resources (contributor pools, updating knowledge, evolving practices, mentor capacity)

### Pattern Combinations
Real processes often (not always) combine multiple patterns: aging chain + resource constraints, population growth + delays → oscillation, stock management + resource depletion. These show how accumulations, rates, feedback, delays, and nonlinearities create recognizable dynamics.

## 3. SD Elements Fundamentals

**Stock**: Accumulations that persist over time
- Examples: people, documents, knowledge units, trust levels, inventory

**Flow**: Rates of change between stocks or between stocks and boundaries (units: things/time)
- Examples: hiring rate, creation rate, depletion rate (people/month, documents/week)

**Cloud**: System boundary representing sources or sinks
- Type: Use type "Cloud" for boundary variables
- Source: External supply entering (e.g., Cloud "External Market" → hiring flow → employees stock)
- Sink: Outflow leaving (e.g., employees stock → attrition flow → Cloud "Attrition Sink")
- Clouds connect via flows just like stocks, but represent the edge of your system

**Auxiliary**: Calculated variables (not stocks or flows) computed from other model elements
- Used to clarify causal relationships and represent factors that influence system behavior
- Examples: effectiveness factors (0-1), gaps, time constants, capacity limits, ratios

**Reinforcing Loop**: Amplifies change (more leads to more, or less leads to less)
- Creates exponential growth or runaway collapse
- Example: More contributors create more visibility, attracting more contributors

**Balancing Loop**: Counteracts change, seeks equilibrium or goal
- Stabilizes system toward target or constraint
- Example: Gap between goal and actual triggers corrective action that closes the gap

## 4. Naming Convention
Be specific and descriptive:
- ✅ "Novice Contributors" not ❌ "Novices"
- ✅ "Documentation Creation Rate" not ❌ "Rate"
- ✅ "Mentoring Effectiveness" not ❌ "Effectiveness"

---

# Validation Checklist

Before finalizing:
- ✓ All variables in connections exist in the SAME process's variables list (except input/output stocks)
- ✓ No undefined references
- ✓ No cross-process connections (except output stock → input stock of next process)
- ✓ Each process has multiple internal stocks with rich dynamics
- ✓ Exactly 1 input stock and 1 output stock designated per process

---

# Output Format

Return ONLY valid JSON:

{{
  "processes": [
    {{
      "process_name": "Process Name from Step 1",
      "input_stock": "Name of designated input stock (receives from previous process)",
      "output_stock": "Name of designated output stock (sends to next process)",
      "variables": [
        {{"name": "Variable Name", "type": "Stock|Flow|Auxiliary|Cloud"}}
      ],
      "connections": [
        {{
          "from": "Source Variable",
          "to": "Target Variable",
          "relationship": "positive|negative"
        }}
      ]
    }}
  ]
}}

IMPORTANT: Ensure all JSON is syntactically correct:
- Close all objects with }} not )
- Match all opening braces {{ with closing braces }}
- Match all opening brackets [ with closing brackets ]
- All strings must be properly quoted
- Use commas between array/object elements
"""

    return prompt


def run_theory_concretization(
    planning_result: Dict,
    variables: Dict,
    connections: Dict,
    plumbing: Dict = None,
    mdl_path: Path = None,
    llm_client: LLMClient = None,
    user_instructions_path: str = None,
    recreate_mode: bool = False
) -> Dict:
    """Execute Step 2: Theory Concretization with condensed prompt.

    Args:
        planning_result: Output from Step 1 strategic planning
        variables: Current model variables
        connections: Current model connections
        plumbing: Optional plumbing data
        mdl_path: Optional MDL path to derive project path
        llm_client: Optional LLM client
        user_instructions_path: Optional path to user instructions file
        recreate_mode: If True, creating complete model from scratch

    Returns:
        Dict with concrete SD elements
    """

    # Derive project path from mdl_path if not explicitly provided
    project_path = None
    if mdl_path:
        # mdl_path is like: /path/to/projects/oss_model/mdl/file.mdl
        # project_path should be: /path/to/projects/oss_model
        project_path = mdl_path.parent.parent

    # Create prompt
    prompt = create_concretization_prompt(
        planning_result,
        variables,
        connections,
        plumbing,
        user_instructions_path=user_instructions_path,
        project_path=project_path,
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

    response = llm_client.complete(prompt, temperature=0.3, max_tokens=64000)

    # Save raw response for debugging
    from pathlib import Path as PathLib
    debug_path = PathLib("/tmp/step2_raw_response.txt")
    debug_path.write_text(response)
    print(f"[DEBUG] Raw Step 2 response saved to: {debug_path}")

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
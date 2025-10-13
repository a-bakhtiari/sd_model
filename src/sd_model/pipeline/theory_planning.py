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


def format_model_structure(variables: Dict, connections: Dict, plumbing: Dict = None) -> str:
    """Format model as causal chains showing Stock-Flow relationships and feedback loops.

    Args:
        variables: Variables dict with 'variables' list
        connections: Connections dict with 'connections' list (can be ID-based or name-based)
        plumbing: Optional plumbing dict with clouds, valves, flows

    Returns:
        Formatted string showing model structure as causal chains
    """
    all_vars = variables.get("variables", [])
    all_conns = connections.get("connections", [])

    # Convert ID-based connections to name-based if needed
    if all_conns and 'from' in all_conns[0]:  # ID-based format
        id_to_name = {int(v["id"]): v["name"] for v in all_vars}
        name_based_conns = []
        for conn in all_conns:
            from_name = id_to_name.get(int(conn.get("from", -1)))
            to_name = id_to_name.get(int(conn.get("to", -1)))
            if not from_name or not to_name:
                continue
            polarity = str(conn.get("polarity", "UNDECLARED")).upper()
            if polarity == "POSITIVE":
                relationship = "positive"
            elif polarity == "NEGATIVE":
                relationship = "negative"
            else:
                relationship = "unknown"
            name_based_conns.append({
                "from_var": from_name,
                "to_var": to_name,
                "relationship": relationship
            })
        all_conns = name_based_conns

    # Build lookup dicts
    vars_by_name = {v['name']: v for v in all_vars}

    # Organize variables by type
    stocks = [v for v in all_vars if v.get('type') == 'Stock']
    flows = [v for v in all_vars if v.get('type') == 'Flow']
    auxiliaries = [v for v in all_vars if v.get('type') == 'Auxiliary']

    # Build outgoing connections map
    outgoing = {}
    for conn in all_conns:
        from_var = conn.get('from_var')
        to_var = conn.get('to_var')
        relationship = conn.get('relationship', 'unknown')

        if from_var not in outgoing:
            outgoing[from_var] = []
        outgoing[from_var].append((to_var, relationship))

    # Check for model boundaries (clouds) and map flow connections
    cloud_count = 0
    cloud_flow_connections = []  # List of (flow_name, from_entity, to_entity, direction)

    if plumbing:
        clouds = plumbing.get('clouds', [])
        cloud_count = len(clouds)
        flows_data = plumbing.get('flows', [])
        valves = plumbing.get('valves', [])

        # Build valve_id -> flow_variable mapping
        valve_to_flow = {}
        for valve in valves:
            valve_id = valve.get('id')
            valve_name = valve.get('name', '')
            # Try to find matching flow variable by name
            for var in all_vars:
                if var.get('type') == 'Flow' and var.get('name') == valve_name:
                    valve_to_flow[valve_id] = var.get('name')
                    break

        # Build id -> name mapping for variables
        id_to_name = {int(v['id']): v['name'] for v in all_vars}

        # Find cloud-connected flows
        for flow_data in flows_data:
            from_ref = flow_data.get('from', {})
            to_ref = flow_data.get('to', {})
            valve_id = flow_data.get('valve_id')

            # Get flow variable name
            flow_name = valve_to_flow.get(valve_id, f'Flow_{valve_id}')

            # Check if cloud is involved
            from_is_cloud = from_ref.get('kind') == 'cloud'
            to_is_cloud = to_ref.get('kind') == 'cloud'

            if from_is_cloud or to_is_cloud:
                from_entity = f"[EXTERNAL: Cloud {from_ref.get('ref')}]" if from_is_cloud else id_to_name.get(from_ref.get('ref'), 'Unknown')
                to_entity = f"[EXTERNAL: Cloud {to_ref.get('ref')}]" if to_is_cloud else id_to_name.get(to_ref.get('ref'), 'Unknown')

                cloud_flow_connections.append((flow_name, from_entity, to_entity))

    # Format Stock-Flow relationships
    stock_flow_text = []
    for stock in stocks:
        stock_name = stock['name']
        # Find flows affecting this stock
        affecting_flows = []
        for flow in flows:
            flow_name = flow['name']
            # Check if this flow connects to the stock
            for conn in all_conns:
                if conn.get('to_var') == stock_name and conn.get('from_var') == flow_name:
                    affecting_flows.append((flow_name, 'inflow'))
                elif conn.get('from_var') == stock_name and conn.get('to_var') == flow_name:
                    affecting_flows.append((flow_name, 'outflow'))

        if affecting_flows:
            for flow_name, direction in affecting_flows:
                # Find what influences this flow
                influences = []
                for var_name, targets in outgoing.items():
                    for target_name, rel in targets:
                        if target_name == flow_name:
                            var_type = vars_by_name.get(var_name, {}).get('type', 'Unknown')
                            influences.append(f"{var_name} ({var_type}) --[{rel}]-->")

                if influences:
                    influences_str = " ".join(influences)
                    stock_flow_text.append(f"{influences_str} {flow_name} (Flow) --[{direction}]--> {stock_name} (Stock)")
                else:
                    stock_flow_text.append(f"{flow_name} (Flow) --[{direction}]--> {stock_name} (Stock)")

    # Format auxiliary relationships
    aux_text = []
    for aux in auxiliaries:
        aux_name = aux['name']
        if aux_name in outgoing:
            for target, rel in outgoing[aux_name]:
                target_type = vars_by_name.get(target, {}).get('type', 'Unknown')
                aux_text.append(f"{aux_name} (Auxiliary) --[{rel}]--> {target} ({target_type})")

    # Build output
    output = "## Model Structure\n\n"

    if stock_flow_text:
        output += "**Stock-Flow Processes**:\n"
        for line in stock_flow_text[:15]:  # Limit to avoid overwhelming
            output += f"- {line}\n"
        if len(stock_flow_text) > 15:
            output += f"... and {len(stock_flow_text) - 15} more stock-flow relationships\n"
        output += "\n"

    if aux_text:
        output += "**Auxiliary Influences** (sample):\n"
        for line in aux_text[:10]:  # Show sample
            output += f"- {line}\n"
        if len(aux_text) > 10:
            output += f"... and {len(aux_text) - 10} more auxiliary relationships\n"
        output += "\n"

    # Add cloud boundary flows
    if cloud_flow_connections:
        output += f"\n**Model Boundaries** ({len(cloud_flow_connections)} boundary flows to/from external environment):\n"
        for flow_name, from_entity, to_entity in cloud_flow_connections[:10]:  # Limit to 10
            output += f"- {from_entity} → {flow_name} (Flow) → {to_entity}\n"
        if len(cloud_flow_connections) > 10:
            output += f"... and {len(cloud_flow_connections) - 10} more boundary flows\n"
        output += "\n"
    elif cloud_count > 0:
        output += f"\n**Model Boundaries**: {cloud_count} clouds representing external sources/sinks (entities outside model scope)\n"
        output += "- Note: Cloud connections not yet mapped in plumbing data\n\n"

    # Add summary
    boundary_note = f", {cloud_count} External Boundaries" if cloud_count > 0 else ""
    output += f"**Summary**: {len(stocks)} Stocks, {len(flows)} Flows, {len(auxiliaries)} Auxiliaries, {len(all_conns)} connections{boundary_note}\n"

    return output


def format_minimal_model_summary(variables: Dict, connections: Dict, plumbing: Dict = None) -> str:
    """Format minimal model summary for recreation mode context.

    Shows only high-level statistics without detailed structure.
    """
    all_vars = variables.get("variables", [])
    all_conns = connections.get("connections", [])

    # Count by type
    stocks = [v for v in all_vars if v.get('type') == 'Stock']
    flows = [v for v in all_vars if v.get('type') == 'Flow']
    auxiliaries = [v for v in all_vars if v.get('type') == 'Auxiliary']

    # Count clouds (model boundaries)
    cloud_count = 0
    if plumbing:
        cloud_count = len(plumbing.get('clouds', []))

    output = "## Domain Context (Existing Model Summary - For Reference Only)\n\n"
    output += f"- **{len(all_vars)} total variables** ({len(stocks)} Stocks, {len(flows)} Flows, {len(auxiliaries)} Auxiliaries)\n"
    output += f"- **{len(all_conns)} connections** between variables\n"

    if cloud_count > 0:
        output += f"- **{cloud_count} model boundaries** (external sources/sinks)\n"

    output += "\n**Note**: This summary provides domain context only. You are building a NEW model from scratch based on theories. "
    output += "The existing model structure is not shown - your output will define a complete new model.\n"

    return output


def create_planning_prompt(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    plumbing: Dict = None,
    spatial_context: Dict = None,  # Kept for backwards compatibility but not used
    recreate_mode: bool = False
) -> str:
    """Create prompt for strategic theory planning (Step 1).

    Args:
        recreate_mode: If True, prompts for building a complete model from scratch.
                      If False (default), prompts for enhancing existing model.
    """

    # Format model structure - use minimal summary in recreation mode
    if recreate_mode:
        model_structure = format_minimal_model_summary(variables, connections, plumbing)
    else:
        model_structure = format_model_structure(variables, connections, plumbing)

    # Format theories
    theories_text = "\n".join([
        f"{i+1}. **{t['name']}**: {t['description']}"
        for i, t in enumerate(theories)
    ])

    # Mode-specific context
    if recreate_mode:
        mode_context = "You will evaluate theories and design process-based narratives for **building a complete SD model from scratch**. The summary below provides domain context only - your output will define an entirely new model based purely on theoretical foundations."
        model_section_title = "# Domain Context"
    else:
        mode_context = "You will evaluate theories and design process-based narratives for **enhancing an existing SD model**."
        model_section_title = "# Current System Dynamics Model"

    prompt = """# Context

You are a system dynamics modeling expert. """ + mode_context + """

**Your task**: Generate conceptual narratives describing system processes (NOT concrete variables). Another step will later convert your narratives into specific SD model elements.

**Output format**: JSON with theory evaluations and process narratives.

""" + model_section_title + """

""" + model_structure + """

# Theories to Evaluate (""" + str(len(theories)) + """ total)

""" + theories_text + """

# System Archetypes (Optional Reference)

**Note**: These archetypes are provided for awareness and may help inform your process narratives. You are NOT required to explicitly identify or apply them. If a process naturally reflects archetype dynamics, that's valuable, but don't force archetype patterns.

**Common System Archetypes:**
- **Balancing Process with Delay**: Adjustment processes with time delays that can cause oscillation
- **Limits to Growth**: Growth that encounters constraining factors
- **Shifting the Burden**: Short-term fixes that undermine long-term solutions
- **Eroding Goals**: Performance standards that drift downward under pressure
- **Escalation**: Competitive dynamics where parties intensify their actions
- **Success to the Successful**: Resource allocation that reinforces existing winners
- **Tragedy of the Commons**: Individual actions that deplete shared resources
- **Fixes that Fail**: Solutions that initially work but create worse problems later
- **Growth and Underinvestment**: Growth constrained by delayed capacity building
- **Policy Resistance**: Multiple actors working at cross-purposes

These patterns may naturally emerge in your process narratives when describing system dynamics.

---

# Your Task: Strategic Planning ONLY

You must perform THREE distinct analyses:

---

## CRITICAL: Writing SD-Ready Process Narratives

Your narratives must be **mechanistically explicit** to enable concrete SD translation. Include these elements:

### Required Mechanistic Elements:

**1. Stocks (Accumulations)**
Explicitly mention collections that build up or deplete:
- ✅ "There is a **pool of peripheral members** who are learning..."
- ✅ "The **knowledge base** accumulates documentation over time..."
- ✅ "The community has a **capacity** for mentoring measured in mentor-hours..."
- ❌ "Members learn through observation" (too vague)

**2. Flows (Rates of Change)**
Describe rates, speeds, and transitions per unit time:
- ✅ "Members transition to core status at a **rate** determined by mentoring availability..."
- ✅ "Documentation is created at a **pace** proportional to active contributors..."
- ✅ "The **speed of integration** depends on community openness..."
- ❌ "Members become more integrated" (no rate specified)

**3. Feedback Loops (Self-Reinforcing or Self-Correcting)**
Explicitly state circular causal chains:
- ✅ "**Reinforcing**: More core members → more mentoring capacity → faster newcomer progression → more future core members"
- ✅ "**Balancing**: As workload increases → burnout rises → attrition increases → workload increases further (vicious cycle)"
- ✅ "**Goal-seeking**: Capacity gap → increased recruitment → more contributors → reduced gap"
- ❌ "Members help each other" (no feedback mechanism)

**4. Delays (Time Lags)**
Mention time constants and delayed effects:
- ✅ "It takes **6-12 months on average** for a newcomer to become proficient..."
- ✅ "The benefits of documentation appear with a **delay** as it gets refined..."
- ✅ "Trust builds **slowly over time** through repeated interactions..."
- ❌ "Members eventually gain expertise" (no time dimension)

**5. Nonlinearities (Thresholds, Saturation, Tipping Points)**
Describe non-proportional relationships:
- ✅ "Below a **threshold** of 5 core members, mentoring becomes insufficient..."
- ✅ "Adoption **accelerates rapidly** once 20% of community has adopted (tipping point)..."
- ✅ "Mentoring effectiveness **saturates** as mentor-to-newcomer ratio exceeds 1:10..."
- ❌ "More mentors help more" (assumes linearity)

**6. Causal Drivers (What Affects What)**
State explicit cause-effect relationships:
- ✅ "Documentation quality **increases** as more experts contribute..."
- ✅ "Engagement **drops** when response time exceeds 48 hours..."
- ✅ "The rate of knowledge transfer is **limited by** available mentors..."
- ❌ "Quality improves over time" (no causal mechanism)

### Example: Before vs After

**❌ Too Abstract (Current Style):**
> "New members enter the community through observation and shared experiences. They learn by observing workflows and absorbing tacit knowledge through interactions. The rate of engagement depends on motivation and community openness."

**✅ SD-Ready (Target Style):**
> "There is a **pool of peripheral members** (Stock) who enter the community at an **arrival rate** (Flow) influenced by project visibility. These newcomers **progress toward core membership** at a **transition rate** (Flow) determined by: (1) available **mentoring capacity** (Stock × time), (2) **average socialization time** (~6 months), and (3) **community openness factor** (0-1 multiplier). **Feedback loop (Reinforcing)**: As more members reach core status (Stock increases) → mentoring capacity grows → transition rate increases → more future core members. **Balancing pressure**: If peripheral member pool grows too large, mentoring capacity becomes saturated, slowing transition rate."

### Narrative Checklist (Use for Each Process)

Before finalizing each narrative, verify:
- [ ] **2-4 Stocks mentioned** (what accumulates?)
- [ ] **2-4 Flows mentioned** (what rates drive change?)
- [ ] **At least 1 feedback loop** explicitly stated (reinforcing or balancing)
- [ ] **Time constants/delays** mentioned (how long do things take?)
- [ ] **Causal drivers** stated (what increases/decreases what?)
- [ ] **Constraints or nonlinearities** (limits, thresholds, saturation)

---

## 1. Theory Evaluation

For EACH theory, decide:
- **include**: Theory clearly applies, will enhance model
- **exclude**: Theory doesn't fit this context
- **adapt**: Theory partially applies, needs modification


## 2. Process-Flow Clustering Strategy

Design **process stages** to organize ALL variables (existing + new) as smaller processes that add up to a whole.

**Step-by-step approach**:

First, design each individual process stage:

For each process stage:
- **name**: Short process name (e.g., "Material Intake", "Production Assembly")
- **narrative**: Full prose description with **SD-mechanistic detail** (write in actual sentences)
  - Describe the process flow and its role in the overall system
  - **REQUIRED**: Include stocks (accumulations), flows (rates), feedback loops, delays, and causal mechanisms
  - See "CRITICAL: Writing SD-Ready Process Narratives" section above for detailed guidance
  - **IMPORTANT**: Build complete, theoretically sound narratives. If you need a theory beyond the provided list to complete the narrative coherently, USE IT. You will report which additional theories you used.
  - Example: "There is a **material inventory** (Stock) that receives raw materials at an **arrival rate** (Flow) from suppliers. Materials undergo quality inspection at a **processing rate** (Flow) limited by inspector capacity. The **inspection pass rate** (Auxiliary: 0-1) adjusts based on **downstream defect feedback** with a **2-week delay**. **Feedback loop (Balancing)**: Higher defects → stricter standards → lower pass rate → fewer defects. Approved materials accumulate in **staging inventory** (Stock) for production."
- **theories_used**: List of theory names from the provided list that informed this cluster's narrative
  - Only include theories you marked as "include" or "adapt" that were actually applied here
  - Example: ["Communities of Practice", "SECI Model"]
- **additional_theories_used**: List of theories NOT in the provided list that you needed to complete this narrative
  - Include theory name and brief rationale for why it was needed
  - This allows you to build complete narratives even when important theories are missing from the provided list
  - Example: [{"theory_name": "Resource Dependency Theory", "rationale": "Needed to explain how external resource constraints affect process capacity"}]
  - Can be empty array if no additional theories were needed
- **connections_to_other_clusters**: Explicit connections showing how this cluster relates to other clusters
  - List each connection with target cluster, type, and description
  - Connection types: "feeds_into" (output), "receives_from" (input), "feedback_loop" (bidirectional)
  - This field replaces the need for separate "inputs" and "outputs" fields by explicitly mapping all connections
  - Example: [{"target_cluster": "Production Assembly", "connection_type": "feeds_into", "description": "Approved materials flow into production"}]

Then, AFTER designing all individual processes, write an **overall_narrative**:
- Synthesize how all processes connect into one cohesive pipeline
- Highlight where processes overlap (where outputs of one become inputs of another)
- Describe the complete flow from start to finish
- Show feedback loops if they exist

Design Principles:
- **Small, focused processes** - Each cluster describes one coherent part of the system with its own dynamics
- **Clear I/O boundaries** - Be explicit about what flows into and out of each process
- **System thinking** - Processes can connect to multiple other processes (not just sequential)
- **Allow feedback loops** - Later processes can feed back to earlier ones
- **Modularity** - Each process should be independently understandable as a mini-model

Example (manufacturing context - for illustration only):

**Note**: This is a simplified example to demonstrate narrative structure and how to describe connections between processes. Your actual model will likely have:
- More processes (not limited to 3)
- More complex interconnections
- Multiple feedback loops within and between processes
- Non-linear dynamics

Do not copy this example's structure or complexity - design based on the theories and model context.

**Individual Process Narratives** (write these first):
1. "Material Intake":
   - Narrative: There is a **supplier pipeline** (Stock) that provides raw materials at an **arrival rate** (Flow) driven by **purchase orders** (Auxiliary). Materials enter a **quality inspection queue** (Stock) where they are processed at an **inspection rate** (Flow) limited by **inspector capacity** (Auxiliary). The **inspection pass rate** (Auxiliary: 0-1) is adjusted based on **downstream defect feedback** (Auxiliary) with a **2-week response delay**. **Feedback loop (Balancing)**: Higher defect rates → stricter inspection standards → lower pass rate → fewer defects (goal-seeking behavior). Approved materials accumulate in **staging inventory** (Stock) ready for production. **Customer demand signal** (Auxiliary) influences the arrival rate, but with a **procurement delay** of 4-6 weeks.
   - Theories Used: ["Quality Management Theory", "Feedback Control Systems"]
   - Additional Theories Used: [{"theory_name": "Supply Chain Coordination Theory", "rationale": "Needed to explain supplier-buyer signaling dynamics"}]
   - Connections to Other Clusters: [
       {"target_cluster": "Production Assembly", "connection_type": "feeds_into", "description": "Approved materials inventory flows into production"},
       {"target_cluster": "Production Assembly", "connection_type": "receives_from", "description": "Quality standards feedback from production issues"}
     ]

2. "Production Assembly":
   - Narrative: **Staging inventory** (Stock) feeds **production lines** (Stock: work-in-progress) at an **allocation rate** (Flow) determined by **available capacity** (Auxiliary: machine-hours/week). The **production completion rate** (Flow) transforms materials into **finished goods** (Stock) at a pace limited by **workforce capacity** (Auxiliary) and **equipment utilization** (Auxiliary: 0-1). **Quality defect rate** (Auxiliary: defects/unit) feeds back to Material Intake with a **1-week delay**. **Feedback loop (Balancing)**: When **distribution capacity** (Auxiliary) becomes constrained → **production rate adjustment signal** (Auxiliary) slows the allocation rate → prevents overflow. Assembly time averages **3-5 days per unit**. **Nonlinearity**: Production efficiency **drops sharply** when utilization exceeds 90% due to bottlenecks.
   - Theories Used: ["Constraint Theory", "Production System Theory"]
   - Additional Theories Used: []
   - Connections to Other Clusters: [
       {"target_cluster": "Material Intake", "connection_type": "receives_from", "description": "Receives approved materials"},
       {"target_cluster": "Material Intake", "connection_type": "feedback_loop", "description": "Quality issue reports feed back to adjust inspection standards"},
       {"target_cluster": "Distribution Preparation", "connection_type": "feeds_into", "description": "Finished goods flow to distribution"},
       {"target_cluster": "Distribution Preparation", "connection_type": "receives_from", "description": "Capacity constraint signals adjust production rate"}
     ]

3. "Distribution Preparation":
   - Narrative: **Finished goods** (Stock) flow into a **distribution warehouse** (Stock) at the **incoming rate** (Flow) from production. Products undergo **final inspection** at a **processing rate** (Flow) limited by **inspection capacity** (Auxiliary: units/day). **Warehouse capacity** (Auxiliary: max units) creates a **capacity gap** (Auxiliary: available - occupied). **Feedback loop (Balancing)**: As gap narrows → **capacity constraint signal** (Auxiliary: 0-1) increases → production slows → gap widens (goal-seeking toward target capacity). **Customer orders** (Stock) accumulate at an **order arrival rate** (Flow) that varies with **market demand** (Auxiliary). **Shipping rate** (Flow) depletes warehouse inventory. **Delay**: Demand signals take **2-3 weeks** to propagate back to Material Intake. **Threshold**: When warehouse exceeds 80% capacity, constraint signal activates sharply.
   - Theories Used: ["Capacity Planning Theory", "Demand Management"]
   - Additional Theories Used: []
   - Connections to Other Clusters: [
       {"target_cluster": "Production Assembly", "connection_type": "receives_from", "description": "Receives finished goods"},
       {"target_cluster": "Production Assembly", "connection_type": "feedback_loop", "description": "Capacity constraints signal to slow production"},
       {"target_cluster": "Material Intake", "connection_type": "feedback_loop", "description": "Customer demand signals propagate to material intake"}
     ]

**Overall System Narrative** (write this AFTER all individual processes):
"Raw materials flow into the facility where quality inspection [Process 1] determines which materials enter active inventory. Approved inventory [overlap: Process 1→2] feeds the production assembly lines where transformation occurs. Quality issues discovered during assembly [feedback: Process 2→1] trigger stricter inspection standards. As assembly progresses [Process 2], finished goods accumulate [overlap: Process 2→3] and move to distribution preparation where they are packaged. Distribution capacity constraints [connection: Process 3→2] can slow production rates to prevent overflow. Customer demand signals [feedback loop: Process 3→1] influence material intake rates. This creates an interconnected system where each process affects multiple others."

---

## Critical Instructions

✓ **DO write SD-mechanistic narratives** - include stocks, flows, feedback loops, delays, and causal drivers (see "CRITICAL: Writing SD-Ready Process Narratives" section above)
✓ **DO write process narratives in full prose** - describe what happens conceptually with explicit mechanisms
✓ **DO design focused processes** - each describes one coherent part of the system
✓ **DO highlight overlap points in overall_narrative** - show where processes connect
✓ **DO include feedback loops** - describe how later processes feed back to earlier ones with explicit causal chains
✓ **DO mention time constants and delays** - specify how long processes take or how long feedback takes to propagate
✓ **DO use additional theories when needed** - if the provided theories are insufficient to build a complete narrative, use relevant theories from your knowledge and report them in `additional_theories_used`
✓ **DO specify theories_used for each cluster** - list which provided theories informed each cluster
✓ **DO specify connections_to_other_clusters** - explicitly map how each cluster connects to others (this replaces separate inputs/outputs fields)

---

## Output Format

Return ONLY valid JSON in this structure (no markdown, no explanation):

{{
  "theory_decisions": [
    {{
      "theory_name": "Theory Name",
      "decision": "include|exclude|adapt"
    }}
  ],
  "clustering_strategy": {{
    "clusters": [
      {{
        "name": "Process Stage Name",
        "narrative": "Full prose description of what happens in this process. Write in actual sentences describing the conceptual flow and its role in the overall system.",
        "theories_used": ["Theory Name 1", "Theory Name 2"],
        "additional_theories_used": [
          {{
            "theory_name": "Theory Not In Provided List",
            "rationale": "Brief explanation of why this theory was needed"
          }}
        ],
        "connections_to_other_clusters": [
          {{
            "target_cluster": "Name of Another Cluster",
            "connection_type": "feeds_into|receives_from|feedback_loop",
            "description": "How these clusters connect"
          }}
        ]
      }}
    ],
    "overall_narrative": "Full prose description of how the entire pipeline flows. Describe how all processes connect and where they overlap. Highlight the integration points where outputs of one process become inputs of another."
  }}
}}

"""

    return prompt


def run_theory_planning(
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    plumbing: Dict = None,
    mdl_path: Path = None,  # Kept for backwards compatibility but not used
    llm_client: LLMClient = None,
    recreate_mode: bool = False
) -> Dict:
    """Execute Step 1: Strategic Theory Planning.

    Args:
        theories: List of theory dictionaries
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        plumbing: Plumbing data from plumbing.json (optional)
        mdl_path: Path to current MDL file (unused, kept for backwards compatibility)
        llm_client: Optional LLM client (creates new if None)
        recreate_mode: If True, prompts for building complete model from scratch

    Returns:
        Dict with strategic planning results:
        {
            "theory_decisions": [...],
            "clustering_strategy": {...}
        }
    """

    # Create prompt
    prompt = create_planning_prompt(theories, variables, connections, plumbing, recreate_mode=recreate_mode)

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

        return result

    except Exception as e:
        return {
            "error": str(e),
            "raw_response": response,
            "theory_decisions": [],
            "clustering_strategy": {}
        }

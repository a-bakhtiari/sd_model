"""
Step 1: Theory Planning - Condensed Version

Strategic planning phase for decomposed theory enhancement.
Focuses on theory selection and process clustering with mechanistic narratives.
"""
from __future__ import annotations

import json
from typing import Dict, List
from pathlib import Path

from ..llm.client import LLMClient


def create_planning_prompt(
    theories: List[Dict],
    current_model_summary: Dict,
    model_name: str = None,
    user_instructions_path: str = None,
    project_path: Path = None,
    recreate_mode: bool = False
) -> str:
    """Create prompt for Step 1: Strategic Theory Planning - CONDENSED.

    Args:
        theories: List of available theories
        current_model_summary: Summary of the current model structure
        model_name: Optional name of the model being enhanced
        user_instructions_path: Optional path to user instructions file
        project_path: Optional project path for finding RQ.txt
        recreate_mode: If True, creating model from scratch; if False, enhancing existing model

    Returns:
        Prompt string for LLM
    """

    # Read user instructions if provided
    user_instructions = ""
    if user_instructions_path is None:
        # Default path
        user_instructions_path = Path(__file__).parent.parent.parent.parent / "user_instructions.txt"

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

    # Read research questions from project-specific location
    research_questions = ""
    if project_path:
        rq_path = project_path / "knowledge" / "RQ.txt"
    else:
        # Fallback to global location
        rq_path = Path(__file__).parent.parent.parent.parent / "research_questions.txt"

    if rq_path.exists():
        try:
            with open(rq_path, 'r') as f:
                content = f.read().strip()
                # Filter out comment lines starting with #
                lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
                rq_content = '\n'.join(lines).strip()
                if rq_content:
                    research_questions = f"\n## Research Questions\n\nThe model should address these research questions:\n\n{rq_content}\n"
        except Exception as e:
            # Silently ignore if can't read file
            pass

    # Format theories list
    theories_text = "\n".join([
        f"{i+1}. **{t['name']}**\n   {t.get('core_concept', '')[:200]}"
        for i, t in enumerate(theories)
    ])

    # Model context and task description based on mode
    if recreate_mode:
        task_description = "You are planning how to create a new SD model from scratch using theories through process-based decomposition."
        model_context = f"**Model**: {model_name or 'System Dynamics Model'}\n**Starting from**: Empty model (0 variables, 0 connections)"
        prompt_title = "# Strategic Theory Planning for SD Model Creation"
    else:
        task_description = "You are planning how theories can enhance an existing SD model through process-based decomposition."
        model_context = f"**Model**: {model_name or 'System Dynamics Model'}\n**Current Structure**: {current_model_summary.get('variables', 0)} variables, {current_model_summary.get('connections', 0)} connections"
        prompt_title = "# Strategic Theory Planning for SD Enhancement"

    prompt = f"""{prompt_title}

Think step by step. You are a system dynamics expert researcher with deep knowledge of SD patterns, and theory-based modeling. Be thorough and precise in crafting research-grade mechanistically rich narratives that capture dynamic behavior.

This stage creates the causal diagram structure for now, but design it to be simulation-ready: proper stock-flow relationships and clear causal connections that will support future quantification and testing.

## Context

{task_description}

{model_context}
{research_questions}{user_instructions}
## Available Theories ({len(theories)} total)

{theories_text}

---

# Your Task: Strategic Planning

## 1. Theory Evaluation

For each theory, decide:
- **include**: Theory applies well to this model context
- **exclude**: Theory doesn't fit this context

## 2. Process-Based Clustering

Design process clusters that COMPREHENSIVELY cover the theories provided. Only include theories that genuinely apply to the model context.

**Using Additional Theories**: Primarily use theories from the provided list. However, if you need additional theories beyond this list to build complete, coherent narratives, you may use them. Report any such theories in `additional_theories_used` with a brief rationale.

SCALING GUIDANCE (rough guidance): Generate proportionally to theory count:
- 2-4 theories → 2-3 processes | 5-8 theories → 4-6 processes | 9-12 theories → 6-8 processes | 13+ theories → 8-10 processes

**What is a Process Cluster?**
Each cluster is a **mini-model**—a focused, independently understandable part of the system with its own dynamics:
- Has a clear primary input stock (what accumulates as input) and primary output stock (what accumulates as output)
- Contains its own stocks, flows, and feedback loops internally

**SISO Architecture (Single Input Single Output):**
- Each process has EXACTLY ONE input stock (what enters/accumulates at the start)
- Each process has EXACTLY ONE output stock (what exits/accumulates at the end)
- Processes connect via flows: Output stock of Process A → Flow → Input stock of Process B
- The overall pipeline MAY form a loop (e.g., last process feeds back to first process for circular dynamics)
- SISO means single I/O per process, NOT that the overall system must be linear—system-level feedback is allowed
- This creates clean process boundaries while allowing rich system-level dynamics

## SD Elements Fundamentals

**Stock**: Accumulations that persist over time (can ask "how many now?")
- Examples: people, documents, knowledge units, trust levels, inventory
- Test: Does it accumulate/deplete over time?

**Flow**: Rates of change between stocks (units: things/time)
- Examples: hiring rate, creation rate, depletion rate (people/month, documents/week)
- Must connect: Stock→Stock or Stock→Boundary

**Boundary (Cloud)**: System edge - sources that fill stocks or sinks that drain stocks
- Source: External supply entering the system (e.g., job market → hiring flow → employees stock)
- Sink: Outflow leaving the system (e.g., employees stock → attrition flow → outside world)

**Auxiliary**: Calculated variables (not stocks or flows) computed from other model elements
- Used to clarify causal relationships and represent factors that influence system behavior
- Examples: effectiveness factors (0-1), gaps, time constants, capacity limits, ratios

**Reinforcing Loop**: Amplifies change (more leads to more, or less leads to less)
- Creates exponential growth or runaway collapse
- Example: More contributors create more visibility, attracting more contributors

**Balancing Loop**: Counteracts change, seeks equilibrium or goal
- Stabilizes system toward target or constraint
- Example: Gap between goal and actual triggers corrective action that closes the gap

## Writing Mechanistic Narratives

### What is a Narrative?

A narrative is a mechanistic story describing how a process unfolds over time. Write in natural language (not variables or equations) to capture the dynamic behavior—what accumulates, what drives rates, how feedback operates.

**Expected Length** (not a rule but rough numbers): 200-400 words per process narrative
- For models with 8+ processes: aim for ~200-300 words each
- For models with fewer processes: aim for ~300-400 words each

This ensures sufficient mechanistic detail for Step 2 to identify concrete SD elements.

### Required Elements to Include:

1. **Accumulations**: What builds up/depletes — "Pool of members grows when..." or "Trust accumulates through..."
2. **Rates and Speeds**: How fast things change — "Transition at rate determined by..." or "Adoption pace depends on..."
3. **Feedback Loops**: Reinforcing or balancing — "More X → more Y → more X" or "Gap increases → adjustment closes gap"
4. **Time Delays**: How long processes take — "Takes 6-12 months for..." or "Benefits appear after 3-month delay..."
5. **Nonlinearities**: Thresholds, saturation, tipping points — "Accelerates after 10+ interactions" or "Saturates when ratio exceeds 1:8"
6. **Causal Relationships**: What drives what — "Rate limited by available mentors" or "Quality increases with expert contributions"

**Example Contrast** (Good ✅ vs Insufficient ❌):

❌ **Insufficient**: "New members join the community and learn by observing workflows. They gain experience through interactions and eventually become contributors who help other members."

✅ **Mechanistically Rich**: "A **pool of newcomers accumulates** as they discover the project at a **rate** influenced by community visibility (5-10 per month). They **build tacit knowledge** through observation, with the **pace** limited by interaction frequency (typically 3-5 meaningful exchanges per week). Members **transition to active contributor status** after a **socialization period of 6-9 months**, at a **rate** determined by available mentoring capacity (2-3 mentor-hours per week currently available). As the contributor base grows, more experienced members become available to mentor, which increases the capacity to support newcomers and **accelerates their progression rate**. However, when the newcomer pool exceeds 20 people, the mentor-to-newcomer ratio becomes unfavorable, and mentoring quality **begins to deteriorate**, slowing transition rates. Individual progress shows a **nonlinear pattern**—newcomers who complete fewer than 10 meaningful interactions show minimal advancement, but those surpassing this threshold experience **sharply accelerated** skill development."

*Note the feedback loops: (1) **Reinforcing** - as contributors grow, mentoring capacity increases, accelerating newcomer progression, creating more contributors; (2) **Balancing** - when newcomers exceed capacity, mentoring quality degrades, slowing progression until the imbalance corrects.*

Systems typically have BOTH (not always) types competing. These may emerge in the overall system or in some of the processes.

## Common SD Patterns from the System Zoo

These canonical patterns appear frequently in well-designed SD models. Consider whether your process resembles any of these, but feel free to combine or adapt them as needed, or come up with your own if needed. These are examples to learn from, not strict templates.

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

## System Archetypes (Classic Patterns)

These are common behavioral patterns identified by Senge and Meadows. Use as optional reference—if a process naturally reflects archetype dynamics, that's valuable, but don't force them.

**Limits to Growth**: Growth encounters constraint | Reinforcing growth + balancing limit
**Shifting the Burden**: Short-term fix undermines long-term solution | Quick fix becomes addictive
**Tragedy of the Commons**: Individual actions deplete shared resource | Self-interest erodes collective good
**Success to the Successful**: Resource allocation reinforces winners | Rich get richer dynamic
**Fixes that Fail**: Solution works initially but creates worse problems | Unintended consequences
**Escalation**: Competitive intensification | Arms race, each party responds to other's actions
**Growth and Underinvestment**: Growth constrained by delayed capacity building | Demand outpaces supply
**Eroding Goals**: Performance standards drift downward under pressure | Lowering the bar
**Balancing with Delay**: Adjustment with time delays causes oscillation | Overshooting target
**Policy Resistance**: Multiple actors working at cross-purposes | Everyone pushing, nothing moves

## Example Process Narrative

This manufacturing example shows how to include all mechanistic elements in ~250 words:

**Process: Material Intake**
"The **supplier pipeline accumulates** raw materials arriving at a **rate** driven by purchase orders (100 units/day baseline). Materials **build up in inspection queue** where they're processed at a **pace** limited by inspector capacity (50 units/day/inspector). The **inspection pass rate** adjusts based on downstream defect feedback with a **2-week delay**—when defects rise above 5%, standards tighten within 3 days. **Balancing feedback**: When defects increase, this triggers stricter inspection standards, which lowers the pass rate, ultimately bringing defects back down in a goal-seeking pattern. Approved materials **accumulate in staging inventory** at the pass rate minus the production allocation rate. Customer demand signals influence material arrival **rate**, but with a **4-6 week procurement delay**. **Reinforcing loop**: As staging inventory builds up, production confidence increases, leading to higher allocation rates that deplete inventory faster, which then signals for more orders to replenish stock. **Nonlinearity**: Inspection effectiveness **drops sharply** when queue exceeds 500 units due to inspector fatigue—pass rate falls from 95% to 70%. **Threshold**: When staging inventory falls below 200 units (critical minimum), production halts within 24 hours. The process **transforms** raw supplier output into quality-verified inventory ready for production, with **constraint** from inspection capacity and **driver** from customer demand propagating backward through the supply chain."

## Process Design Requirements

Each process must have:
- **Name**: Clear, descriptive process name
- **Narrative**: Mechanistically rich (300-500 words, per guidelines above)
- **Theories Used**: Which theories inform this process
- **Connections** (`connections_to_other_clusters`): Specify how this process connects to others:
  - **connection_type**: One of: `feeds_into`, `receives_from`, or `feedback_loop`
  - **target_cluster**: Name of the connected process
  - **description**: Brief explanation of what flows between them
  - Most processes will primarily use `feeds_into` for the main pipeline flow
  - Use `feedback_loop` when the last process feeds back to an earlier one for circular system dynamics

Additional Design Principles:
- **Small, focused processes** - Each cluster describes one coherent part of the system with its own dynamics
- **Clear I/O boundaries** - Each process has exactly one input stock and one output stock (SISO)
- **Pipeline with optional loops** - Primary flow through processes, with optional system-level feedback
- **Modularity** - Each process should be independently understandable as a mini-model

## Output Format

Return ONLY valid JSON:

{{
  "theory_decisions": [
    {{"theory_name": "Theory Name", "decision": "include|exclude"}}
  ],
  "clustering_strategy": {{
    "clusters": [
      {{
        "name": "Process Name",
        "narrative": "Mechanistic narrative with accumulations, rates, feedback...",
        "theories_used": ["Theory Names"],
        "additional_theories_used": [
          {{"theory_name": "Additional Theory", "rationale": "Why needed"}}
        ],
        "connections_to_other_clusters": [
          {{
            "target_cluster": "Other Process Name",
            "connection_type": "feeds_into|receives_from|feedback_loop",
            "description": "What flows between them"
          }}
        ]
      }}
    ],
    "overall_narrative": "How processes connect as integrated system..."
  }}
}}

## Critical Instructions

✓ Write mechanistic narratives WITHOUT type labels
✓ Design process clusters scaled to theory count
✓ Each narrative should be comprehensive (see word count guidance in narrative section)
✓ Ensure processes connect (no isolated clusters)
✓ Use additional theories if needed for completeness
"""

    return prompt


def run_theory_planning(
    theories: List[Dict],
    variables: Dict = None,
    connections: Dict = None,
    plumbing: Dict = None,
    mdl_path: Path = None,
    llm_client: LLMClient = None,
    user_instructions_path: str = None,
    recreate_mode: bool = False
) -> Dict:
    """Execute Step 1: Strategic Theory Planning - CONDENSED.

    Args:
        theories: List of available theories
        variables: Variables dict (for current_model_summary)
        connections: Connections dict (for current_model_summary)
        plumbing: Optional plumbing data (unused but kept for compatibility)
        mdl_path: Optional MDL path to derive project path
        llm_client: Optional LLM client
        user_instructions_path: Optional path to user instructions file
        recreate_mode: If True, recreating model from scratch

    Returns:
        Dict with theory decisions and clustering strategy
    """

    # Build current model summary from variables and connections
    current_model_summary = {
        'variables': len(variables.get('variables', [])) if variables else 0,
        'connections': len(connections.get('connections', [])) if connections else 0
    }

    # Derive project path from mdl_path
    project_path = None
    if mdl_path:
        # mdl_path is like: /path/to/projects/oss_model/mdl/untitled.mdl
        # We want: /path/to/projects/oss_model
        project_path = Path(mdl_path).parent.parent

    # Create prompt
    prompt = create_planning_prompt(
        theories,
        current_model_summary,
        model_name=None,
        user_instructions_path=user_instructions_path,
        project_path=project_path,
        recreate_mode=recreate_mode
    )

    # Call LLM
    if llm_client is None:
        from ..config import should_use_gpt
        import logging
        logger = logging.getLogger(__name__)
        provider, model = should_use_gpt("theory_planning")
        logger.info(f"  → Step 1 using: {provider.upper()} ({model})")
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

        return result

    except Exception as e:
        # Return error with defaults
        return {
            "error": str(e),
            "raw_response": response,
            "theory_decisions": [],
            "clustering_strategy": {
                "clusters": [],
                "overall_narrative": ""
            }
        }
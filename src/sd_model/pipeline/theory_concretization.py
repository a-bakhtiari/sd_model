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

    # Format inter-cluster connections from Step 1
    inter_cluster_text = "\n\n".join([
        f"**{c['name']}** connects to:\n" +
        "\n".join([
            f"  → {conn['target_cluster']} ({conn['connection_type']}): \"{conn['description']}\""
            for conn in c.get('connections_to_other_clusters', [])
        ])
        for c in clustering_strategy.get('clusters', [])
        if c.get('connections_to_other_clusters')
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

# Inter-Cluster Connections (CRITICAL!)

The following connections MUST exist between processes to create a cohesive, connected model:

{inter_cluster_text}

---

# Canonical SD Patterns (USE THESE!)

When translating theoretical mechanisms to SD elements, match your theory to these proven patterns. These patterns come from SD literature (Sterman, 2000) and ensure robust dynamic structure.

## Pattern 1: Aging Chain (Progression Through Stages)

**Use when**: Theory describes progression through levels/stages (novice→expert, peripheral→core)

```
Stock 1 → (Flow Rate 1) → Stock 2 → (Flow Rate 2) → Stock 3

Variables:
  Stock: Level_1, Level_2, Level_3 (entities at each stage)
  Flow: Progression_Rate_1_to_2 = Level_1 * Effectiveness_1 * Time_Constant_1
  Flow: Progression_Rate_2_to_3 = Level_2 * Effectiveness_2 * Time_Constant_2
  Auxiliary: Effectiveness (factors affecting progression)

Example (Learning):
  Stock: Novices, Intermediates, Experts
  Flow: Learning_Rate = Novices * Mentoring_Effectiveness / Learning_Time
  Flow: Mastery_Rate = Intermediates * Practice_Quality / Mastery_Time
```

## Pattern 2: Stock Management with Feedback

**Use when**: Theory describes resource/capacity management with desired levels

```
  Desired_Level
       ↓
  Gap → Adjustment_Rate → Stock
       ↑                    ↓
       └────────────────────┘

Variables:
  Stock: Actual_Level (resource, capacity, knowledge)
  Auxiliary: Desired_Level, Gap = Desired - Actual
  Flow: Adjustment_Rate = Gap / Adjustment_Time
  Feedback: Stock → Gap → Adjustment Rate (balancing loop - goal seeking)

Example (Knowledge):
  Stock: Knowledge_Base
  Auxiliary: Desired_Knowledge = f(requirements)
  Auxiliary: Knowledge_Gap = Desired_Knowledge - Knowledge_Base
  Flow: Learning_Rate = Knowledge_Gap / Learning_Time
```

## Pattern 3: Diffusion/Adoption (S-Curve Growth)

**Use when**: Theory describes spreading/adoption with word-of-mouth effects

```
Potential_Adopters ← Adoption_Flow → Adopters
                          ↑              ↓
                          └──────────────┘

Variables:
  Stock: Potential_Adopters, Adopters
  Flow: Adoption_Flow = Potential * Contact_Rate * Adoption_Fraction
  Auxiliary: Contact_Rate = Adopters * Contacts_Per_Adopter / Total_Population
  Feedback: More Adopters → More Contacts → Faster Adoption (reinforcing S-curve)

Example (Knowledge Spread):
  Stock: Unknowing_Members, Knowing_Members
  Flow: Knowledge_Transfer_Rate = Unknowing * (Knowing/Total) * Transfer_Effectiveness
  Feedback: Knowing → Transfer Rate → More Knowing (S-curve diffusion)
```

## Pattern 4: Resource with Regeneration

**Use when**: Theory involves renewable resources (trust, capacity, knowledge that regenerates)

```
Resource_Stock ← Regeneration_Flow
      ↓
   Usage_Flow

Variables:
  Stock: Resource_Level
  Flow: Usage_Flow = Resource * Usage_Fraction
  Flow: Regeneration_Flow = (Max_Resource - Resource) / Regeneration_Time
  Feedback: Resource → Usage (reinforcing depletion)
  Feedback: Resource → Regeneration (balancing restoration)

Example (Trust):
  Stock: Trust_Level
  Flow: Trust_Erosion = Trust * Erosion_Rate
  Flow: Trust_Building = (Max_Trust - Trust) * Positive_Interactions / Building_Time
```

## Pattern 5: Co-flow (Bidirectional Transfer)

**Use when**: Theory describes mutual exchange between groups

```
Stock_A ↔ Transfer_Flows ↔ Stock_B

Variables:
  Stock: Group_A_Knowledge, Group_B_Knowledge
  Flow: A_to_B_Transfer = Group_A_Knowledge * Transfer_Rate_AB * Willingness_B
  Flow: B_to_A_Transfer = Group_B_Knowledge * Transfer_Rate_BA * Willingness_A
  Feedback: Reciprocal knowledge sharing

Example (Communities):
  Stock: Core_Member_Knowledge, Peripheral_Member_Knowledge
  Flow: Mentoring_Flow = Core_Knowledge * Mentoring_Rate * Peripheral_Receptiveness
  Flow: Contribution_Flow = Peripheral_Knowledge * Contribution_Rate * Core_Openness
```

## How to Use Patterns

1. **Read your process narrative**
2. **Identify which pattern(s) match the mechanism**
   - Progression through stages? → Aging Chain
   - Goal-seeking behavior? → Stock Management
   - Spreading with network effects? → Diffusion
   - Renewable resource? → Regeneration
   - Mutual exchange? → Co-flow
3. **Adapt the pattern** to your theory's specific variables
4. **Keep the mathematical structure** (stocks, flows, feedbacks)
5. **Combine patterns** if theory involves multiple mechanisms

---

# Your Task: Convert Narratives to SD Elements

**Read the overall system narrative** to understand how processes connect as a cohesive whole.

Then **for EACH process narrative**, create:
1. **Stocks** - Accumulations described in the narrative
2. **Flows** - Rates of change connecting stocks
3. **Auxiliaries** - Calculated values, ratios, multipliers
4. **Connections** - Causal relationships implementing the narrative logic (BOTH internal AND inter-cluster)
5. **Hub outputs** - Key variables that connect this process to others

**Key Principle**: Each process is a modular mini-model with canonical SD structure. Use the patterns above to ensure robust dynamics with proper feedback loops.

## ⚠️ CRITICAL: Creating Inter-Cluster Connections

You MUST create concrete variable-to-variable connections between processes based on the inter-cluster relationships shown above.

**STRICT SISO (Single-Input, Single-Output) Pattern (REQUIRED):**

Each process module MUST follow the SISO principle:
- **EXACTLY ONE input** (receives from ONE upstream process)
- **EXACTLY ONE output** (sends to ONE downstream process)

This creates the cleanest possible pipeline architecture where each process transforms one input into one output.

**Pattern:**
```
Process A:
  - Input: (from external or previous process)
  - Internal: Stocks, Flows, Auxiliaries for processing
  - Output Hub: "Process A Output" → connects to EXACTLY ONE next process

Process B:
  - Input: "Process A Output" → "Process B Input Rate"
  - Internal: Processing logic
  - Output Hub: "Process B Output" → connects to EXACTLY ONE next process

Process C:
  - Input: "Process B Output" → "Process C Input Rate"
  - Internal: Processing logic
  - Output Hub: "Process C Output" → connects to next process or loops back
```

**How to implement SISO inter-cluster connections:**

For EACH process:

1. **Identify EXACTLY ONE input**
   - Look at `receives_from` relationships - this is your ONE input source
   - Create an input variable (Flow or Auxiliary) that receives from ONE upstream hub
   - If no `receives_from`, this is a source process (external input)

2. **Create EXACTLY ONE output hub**
   - The main Stock or key Auxiliary representing what this process produces
   - This hub connects to EXACTLY ONE downstream process

3. **Add EXACTLY ONE outgoing connection**
   - From: Your output hub
   - To: ONE downstream process's input variable
   - Look at `feeds_into` relationships to identify the ONE primary downstream

**Example (SECI Pipeline):**
```
Step 1 shows:
  Socialization → feeds_into → Externalization
  Externalization → feeds_into → Combination
  Combination → feeds_into → Internalization
  Internalization → feedback_loop → Socialization (cycle back)

Step 2 implementation:

Process: Knowledge Socialization
  - Input: (external newcomers joining)
  - Output Hub: "Tacit Knowledge Base" (Stock)
  - ONE outgoing connection:
    {{"from": "Tacit Knowledge Base", "to": "Knowledge Articulation Rate", "relationship": "positive"}}
  - Sends to: Externalization ONLY

Process: Knowledge Externalization
  - Input: "Tacit Knowledge Base" → "Knowledge Articulation Rate" (Flow)
  - Output Hub: "Articulated Knowledge" (Stock)
  - ONE outgoing connection:
    {{"from": "Articulated Knowledge", "to": "Knowledge Integration Rate", "relationship": "positive"}}
  - Sends to: Combination ONLY

Process: Knowledge Combination
  - Input: "Articulated Knowledge" → "Knowledge Integration Rate" (Flow)
  - Output Hub: "Integrated Knowledge Systems" (Stock)
  - ONE outgoing connection:
    {{"from": "Integrated Knowledge Systems", "to": "Knowledge Application Rate", "relationship": "positive"}}
  - Sends to: Internalization ONLY

Process: Knowledge Internalization
  - Input: "Integrated Knowledge Systems" → "Knowledge Application Rate" (Flow)
  - Output Hub: "Internalized Expertise" (Stock)
  - ONE outgoing connection:
    {{"from": "Internalized Expertise", "to": "Shared Experience Rate", "relationship": "positive"}}
  - Sends to: Socialization (feedback loop closes the cycle)

Result: Clean linear pipeline A→B→C→D→A
```

**Connection Types Guide:**
- **feeds_into** → Your output hub connects to target's input (ONE connection)
- **receives_from** → You receive from source's output hub (create input variable)
- **feedback_loop** → Bidirectional between TWO processes (each has ONE input, ONE output pointing to each other)

**STRICT SISO Rules:**
- ✅ Each process has EXACTLY ONE output hub
- ✅ Each process receives from EXACTLY ONE upstream process (or is source process)
- ✅ Each output hub connects to EXACTLY ONE downstream process
- ✅ Linear pipeline preferred: A → B → C → D
- ✅ Feedback loops allowed: Last process loops back to first
- ✅ If Step 1 shows multiple `feeds_into`, choose the PRIMARY one (main flow)
- ❌ DO NOT create one-to-many (one output to multiple downstream)
- ❌ DO NOT create many-to-one (multiple inputs from different upstream)
- ❌ DO NOT create isolated processes
- ❌ DO NOT skip inter-cluster connections

**Exception:** If Step 1 explicitly designates one process as a "coordinating hub" (e.g., "Community Core Development" that provides context to all others), it MAY have multiple outputs. But default to SISO unless clearly indicated.

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

**Type Selection - Use This Decision Tree:**

### Step 1: Is this a COLLECTION of entities that accumulates/depletes over time?
**→ STOCK**

**Test Questions:**
- Can you ask "How much/many is there RIGHT NOW?"
- Does it have units of "things" (people, documents, units of knowledge)?
- Does it persist even if inflows/outflows stop?

**Examples from Knowledge Management Theory:**
- ✅ "Novice Contributors" (people)
- ✅ "Documented Knowledge Base" (documents/artifacts)
- ✅ "Core Developers" (people)
- ✅ "Tacit Knowledge Pool" (units of tacit knowledge)
- ✅ "Organizational Memory" (accumulated experience)

**Units Check:** People, documents, knowledge units, capacity units

---

### Step 2: Is this a RATE that changes a Stock over time?
**→ FLOW**

**Test Questions:**
- Can you ask "How fast is it changing PER UNIT TIME?"
- Does it have units of "things PER TIME" (people/month, documents/week)?
- Does it connect TWO Stocks OR a Stock to model boundary?

**CRITICAL RULE:** Flows ONLY exist between Stocks. If there's no Stock-to-Stock connection, use Auxiliary instead.

**Valid Flow Patterns:**
- Stock A → [Flow] → Stock B (internal transfer)
- Stock A → [Flow] → Boundary (outflow to external)
- Boundary → [Flow] → Stock A (inflow from external)

**Examples from Knowledge Management Theory:**
- ✅ "Learning Rate" (Novices → Intermediates: people/month)
- ✅ "Documentation Creation Rate" (→ Knowledge Base: documents/month)
- ✅ "Attrition Rate" (Core Developers → Boundary: people/month)
- ✅ "Knowledge Transfer Rate" (Tacit Pool → Explicit Docs: knowledge units/month)
- ❌ "Mentoring Effectiveness" → NOT a Flow (no Stock-to-Stock connection) → Use Auxiliary

**Units Check:** [Stock units] / [Time unit] (people/month, documents/week, etc.)

---

### Step 3: Is this a CALCULATED VALUE, multiplier, or intermediate factor?
**→ AUXILIARY**

**Test Questions:**
- Is it calculated from other variables (no direct accumulation)?
- Does it affect rates (Flows) but isn't itself a rate between Stocks?
- Does it represent effectiveness, ratio, probability, or dimensionless factor?

**Examples from Knowledge Management Theory:**
- ✅ "Mentoring Effectiveness" (dimensionless: 0-1 multiplier)
- ✅ "Documentation Quality Index" (dimensionless ratio)
- ✅ "Community Engagement Level" (calculated from multiple factors)
- ✅ "Knowledge Gap" (Desired - Actual: knowledge units, but not a rate)
- ✅ "Time to Competency" (months, derived from skill level)

**Common Use Cases:**
- Multipliers/effectiveness factors (0-1 range)
- Ratios and fractions (dimensionless)
- Gaps (Desired - Actual)
- Time constants (adjustment time, delay time)
- Thresholds and conditions

**Units Check:** Often dimensionless, or composite units (not [things/time])

---

## Theory-to-Type Mapping Guide

When translating theoretical concepts, use this mapping:

| Theoretical Concept | SD Type | Example Variable |
|---------------------|---------|------------------|
| **Actors/Agents** (people, entities) | Stock | "Novice Contributors", "Core Developers" |
| **Resources/Assets** (knowledge, capacity) | Stock | "Knowledge Base", "Development Capacity" |
| **State/Level** (maturity, trust) | Stock | "Organizational Maturity Level", "Trust Level" |
| **Movement/Transfer** (people moving, knowledge flow) | Flow | "Promotion Rate", "Knowledge Transfer Rate" |
| **Change Rate** (any "per time" concept) | Flow | "Learning Rate", "Attrition Rate" |
| **Effectiveness/Quality** (how well something works) | Auxiliary | "Mentoring Effectiveness", "Code Quality" |
| **Multipliers** (amplifying/dampening factors) | Auxiliary | "Network Effect Multiplier", "Fatigue Factor" |
| **Gaps** (desired vs actual) | Auxiliary | "Skill Gap", "Capacity Gap" |
| **Time Constants** (how long processes take) | Auxiliary | "Time to Learn", "Onboarding Duration" |
| **Conditions/Thresholds** (when things happen) | Auxiliary | "Burnout Threshold", "Promotion Readiness" |

---

## Quick Validation Checklist

Before finalizing your variable list:

- [ ] **Every Stock has at least ONE Flow** (inflow or outflow)
- [ ] **Every Flow connects TWO Stocks** (or Stock-to-Boundary)
- [ ] **Auxiliaries are used for calculated values**, not direct accumulations
- [ ] **Units are consistent**: Stocks (things), Flows (things/time), Auxiliaries (various)
- [ ] **Feedback loops exist**: At least one Stock → Auxiliary → Flow → Stock cycle
- [ ] **Names are specific**: "Novice Contributors" not just "Novices"

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

## Worked Examples: Theory Narrative → SD Translation

These examples demonstrate how to translate theoretical mechanisms into concrete SD structure with proper feedback loops and canonical patterns.

---

### Example 1: Knowledge Transfer via Mentorship (Aging Chain Pattern)

**Theory Narrative (from Step 1):**
"Nonaka's SECI model describes knowledge conversion through socialization (tacit-to-tacit), externalization (tacit-to-explicit), combination (explicit-to-explicit), and internalization (explicit-to-tacit). In open source, newcomers gain tacit knowledge through mentorship from core developers, then document this knowledge, which gets integrated into guides, and finally internalized by future newcomers."

**SD Translation:**

**Step 1: Identify Stocks** (collections that accumulate)
- "Newcomers with Tacit Knowledge" (people)
- "Contributors with Documented Knowledge" (people)
- "Core Developers" (people)

**Step 2: Identify Flows** (rates connecting stocks)
- "Mentorship Completion Rate" (Newcomers → Contributors: people/month)
- "Documentation Mastery Rate" (Contributors → Core Developers: people/month)

**Step 3: Identify Auxiliaries** (calculated values, multipliers)
- "Mentoring Effectiveness" (dimensionless: 0-1, depends on Core Developer availability)
- "Documentation Quality" (dimensionless: 0-1, affects mastery rate)
- "Average Mentoring Time" (months, time constant)

**Step 4: Create Feedback Loop**
- Core Developers → Mentoring Effectiveness (more mentors = better effectiveness)
- Mentoring Effectiveness → Mentorship Completion Rate (effectiveness speeds progression)
- Mentorship Completion Rate → Core Developers (eventually) (creates reinforcing loop)

**Result:** Aging Chain pattern with reinforcing feedback (more core devs → better mentorship → more future core devs)

**Variables:**
```json
[
  {{"name": "Newcomers with Tacit Knowledge", "type": "Stock"}},
  {{"name": "Contributors with Documented Knowledge", "type": "Stock"}},
  {{"name": "Core Developers", "type": "Stock"}},
  {{"name": "Mentorship Completion Rate", "type": "Flow"}},
  {{"name": "Documentation Mastery Rate", "type": "Flow"}},
  {{"name": "Mentoring Effectiveness", "type": "Auxiliary"}},
  {{"name": "Documentation Quality", "type": "Auxiliary"}},
  {{"name": "Average Mentoring Time", "type": "Auxiliary"}}
]
```

**Connections (including feedback):**
```json
[
  {{"from": "Mentorship Completion Rate", "to": "Contributors with Documented Knowledge", "relationship": "positive"}},
  {{"from": "Newcomers with Tacit Knowledge", "to": "Mentorship Completion Rate", "relationship": "positive"}},
  {{"from": "Mentoring Effectiveness", "to": "Mentorship Completion Rate", "relationship": "positive"}},
  {{"from": "Core Developers", "to": "Mentoring Effectiveness", "relationship": "positive"}},
  {{"from": "Documentation Mastery Rate", "to": "Core Developers", "relationship": "positive"}},
  {{"from": "Contributors with Documented Knowledge", "to": "Documentation Mastery Rate", "relationship": "positive"}},
  {{"from": "Documentation Quality", "to": "Documentation Mastery Rate", "relationship": "positive"}}
]
```

---

### Example 2: Community Capacity Management (Stock Management with Feedback Pattern)

**Theory Narrative (from Step 1):**
"Social Capital Theory emphasizes network ties and trust. In OSS, contribution capacity depends on active contributors, but burnout and turnover reduce capacity. Projects adjust onboarding efforts based on capacity gaps."

**SD Translation:**

**Step 1: Identify Stocks** (collections that accumulate)
- "Active Contributors" (people)
- "Contribution Capacity" (person-hours/month) — derived stock representing available effort

**Step 2: Identify Flows** (rates connecting stocks)
- "Onboarding Rate" (→ Active Contributors: people/month)
- "Attrition Rate" (Active Contributors →: people/month)

**Step 3: Identify Auxiliaries** (calculated values, multipliers)
- "Desired Capacity" (person-hours/month, target level)
- "Capacity Gap" (Desired - Actual: person-hours/month)
- "Onboarding Adjustment" (dimensionless multiplier based on gap)
- "Burnout Factor" (dimensionless: 0-1, increases with overwork)

**Step 4: Create Feedback Loop**
- Capacity Gap → Onboarding Adjustment (larger gap → more recruiting)
- Onboarding Adjustment → Onboarding Rate (adjustment speeds onboarding)
- Onboarding Rate → Active Contributors → Contribution Capacity (closes gap)
- **Balancing Loop:** Gap-seeking behavior (classic goal-seeking pattern)

**Result:** Stock Management pattern with balancing feedback (capacity gap drives corrective action)

**Variables:**
```json
[
  {{"name": "Active Contributors", "type": "Stock"}},
  {{"name": "Contribution Capacity", "type": "Stock"}},
  {{"name": "Onboarding Rate", "type": "Flow"}},
  {{"name": "Attrition Rate", "type": "Flow"}},
  {{"name": "Desired Capacity", "type": "Auxiliary"}},
  {{"name": "Capacity Gap", "type": "Auxiliary"}},
  {{"name": "Onboarding Adjustment", "type": "Auxiliary"}},
  {{"name": "Burnout Factor", "type": "Auxiliary"}}
]
```

**Connections (including feedback):**
```json
[
  {{"from": "Onboarding Rate", "to": "Active Contributors", "relationship": "positive"}},
  {{"from": "Active Contributors", "to": "Attrition Rate", "relationship": "positive"}},
  {{"from": "Attrition Rate", "to": "Active Contributors", "relationship": "negative"}},
  {{"from": "Active Contributors", "to": "Contribution Capacity", "relationship": "positive"}},
  {{"from": "Capacity Gap", "to": "Onboarding Adjustment", "relationship": "positive"}},
  {{"from": "Onboarding Adjustment", "to": "Onboarding Rate", "relationship": "positive"}},
  {{"from": "Desired Capacity", "to": "Capacity Gap", "relationship": "positive"}},
  {{"from": "Contribution Capacity", "to": "Capacity Gap", "relationship": "negative"}},
  {{"from": "Burnout Factor", "to": "Attrition Rate", "relationship": "positive"}}
]
```

---

### Example 3: Knowledge Diffusion with Network Effects (Diffusion/Adoption Pattern)

**Theory Narrative (from Step 1):**
"Rogers' Diffusion of Innovation theory suggests adoption follows an S-curve driven by social exposure. In OSS, best practices spread as more developers adopt them, with network effects accelerating adoption among the non-adopter population."

**SD Translation:**

**Step 1: Identify Stocks** (collections that accumulate)
- "Non-Adopters" (people who haven't adopted the practice)
- "Adopters" (people who have adopted the practice)

**Step 2: Identify Flows** (rates connecting stocks)
- "Adoption Rate" (Non-Adopters → Adopters: people/month)

**Step 3: Identify Auxiliaries** (calculated values, multipliers)
- "Contact Rate" (contacts/person/month, how often people interact)
- "Adoption Probability" (dimensionless: 0-1, probability per contact)
- "Network Effect Multiplier" (dimensionless, increases with adopter fraction)
- "Total Population" (people, constant)

**Step 4: Create Feedback Loop**
- Adopters → Network Effect Multiplier (more adopters → stronger network effect)
- Network Effect Multiplier → Adoption Probability (network effect increases adoption)
- Adoption Probability → Adoption Rate (higher probability → faster adoption)
- Adoption Rate → Adopters (creates reinforcing loop)
- **Reinforcing Loop with Limits:** S-curve growth (fast in middle, slow at extremes)

**Result:** Diffusion pattern with reinforcing feedback and natural saturation

**Variables:**
```json
[
  {{"name": "Non-Adopters", "type": "Stock"}},
  {{"name": "Adopters", "type": "Stock"}},
  {{"name": "Adoption Rate", "type": "Flow"}},
  {{"name": "Contact Rate", "type": "Auxiliary"}},
  {{"name": "Adoption Probability", "type": "Auxiliary"}},
  {{"name": "Network Effect Multiplier", "type": "Auxiliary"}},
  {{"name": "Total Population", "type": "Auxiliary"}}
]
```

**Connections (including feedback):**
```json
[
  {{"from": "Adoption Rate", "to": "Adopters", "relationship": "positive"}},
  {{"from": "Non-Adopters", "to": "Adoption Rate", "relationship": "positive"}},
  {{"from": "Adoption Rate", "to": "Non-Adopters", "relationship": "negative"}},
  {{"from": "Adoption Probability", "to": "Adoption Rate", "relationship": "positive"}},
  {{"from": "Contact Rate", "to": "Adoption Rate", "relationship": "positive"}},
  {{"from": "Adopters", "to": "Network Effect Multiplier", "relationship": "positive"}},
  {{"from": "Network Effect Multiplier", "to": "Adoption Probability", "relationship": "positive"}}
]
```

---

## Key Takeaways from Examples

1. **Every process needs 3-5 Stocks minimum** (not just 1-2) to capture progression/stages
2. **Feedback loops are REQUIRED** - no isolated linear chains
3. **Match theory to canonical patterns** - use the pattern library above
4. **Auxiliaries enable feedback** - they connect stocks back to flows
5. **Names must be specific** - "Newcomers with Tacit Knowledge" not just "Newcomers"
6. **Units guide types** - people = Stock, people/month = Flow, dimensionless = Auxiliary

---

## Output Format

Return ONLY valid JSON in this structure (no markdown, no explanation):

{{
  "processes": [
    {{
      "process_name": "Knowledge Socialization",
      "variables": [
        {{
          "name": "Tacit Knowledge Base",
          "type": "Stock"
        }},
        {{
          "name": "Socialization Rate",
          "type": "Flow"
        }}
      ],
      "connections": [
        {{
          "from": "Socialization Rate",
          "to": "Tacit Knowledge Base",
          "relationship": "positive"
        }},
        {{
          "from": "Tacit Knowledge Base",
          "to": "Knowledge Articulation Rate",
          "relationship": "positive",
          "note": "INTER-CLUSTER connection to Knowledge Externalization"
        }}
      ],
      "boundary_flows": []
    }},
    {{
      "process_name": "Knowledge Externalization",
      "variables": [
        {{
          "name": "Articulated Knowledge",
          "type": "Stock"
        }},
        {{
          "name": "Knowledge Articulation Rate",
          "type": "Flow"
        }}
      ],
      "connections": [
        {{
          "from": "Knowledge Articulation Rate",
          "to": "Articulated Knowledge",
          "relationship": "positive"
        }}
      ],
      "boundary_flows": []
    }}
  ],
  "cluster_positions": {{
    "Knowledge Socialization": [0, 0],
    "Knowledge Externalization": [0, 1]
  }}
}}

**Example showing inter-cluster connection:** "Tacit Knowledge Base" (in Socialization) connects to "Knowledge Articulation Rate" (in Externalization). This connection appears in the Socialization process's connections array.

**Notes**:
- Process names must match the cluster names from Step 1
- Variables in each process automatically belong to that process's cluster
- `boundary_flows` is OPTIONAL - only use when a Flow connects a Stock to external environment (not another stock in model)
  - `source`: External entity feeding INTO the model (e.g., labor market hiring into "Active Contributors")
  - `sink`: External entity draining FROM the model (e.g., contributors leaving to job market)
  - If both ends of a Flow are Stocks in the model, use `connections` instead, not `boundary_flows`
- `cluster_positions` is REQUIRED - high-level spatial layout for diagram:
  - Format: `{{"Process Name": [row, col]}}` where row and col are 0-indexed grid coordinates
  - Place connected processes near each other (same row or adjacent rows/cols) for shorter arrows
  - Use 2-3 columns, multiple rows as needed
  - Example: If Process A feeds into Process B, put them adjacent like `A: [0,0], B: [0,1]` or `B: [1,0]`

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

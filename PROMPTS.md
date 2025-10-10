# LLM Prompts Documentation

This document contains the actual prompt text for all LLM API calls in the SD Model pipeline.

---

## 1. Model Extraction & Parsing

### VARIABLE_PROMPT
**Location:** `src/sd_model/pipeline/llm_extraction.py:11-105`

```text
You are an expert Vensim .mdl file parser. Analyze the provided model text and generate a JSON object containing all variables with their positions and types.

## 1. Variable Extraction
Focus on lines starting with `10,` in the sketch section. These define variables.
Format: `10, ID, Name, X, Y, Width, Height, ShapeCode, Field9, Field10, ..., ColorFields`

Extract:
- **id**: 2nd field (integer)
- **name**: 3rd field (exact string, keep quotes if present)
- **x**: 4th field (integer position)
- **y**: 5th field (integer position)
- **width**: 6th field (integer, variable box width)
- **height**: 7th field (integer, variable box height)
- **type**: Determined by rules below
- **colors**: Fields 16-18 if present (RGB format like `0-0-0`), otherwise omit

## 2. Variable Type Classification (apply in this order)

### Flows (Rates)
- **Rule**: Shape Code (8th field) equals `40`
- Most straightforward to identify
- Examples from typical models:
  ```
  10,11,Adoption Rate,...,46,26,40,3,0,0,...
  10,16,User Churn Rate,...,46,26,40,3,0,0,...
  10,76,Skill up,...,46,26,40,3,0,0,...
  ```

### Stocks (Levels)
- **Rule**: Variable is the destination of a flow valve
- Detection process:
  1. Find all valve definitions (lines starting with `11,`)
  2. Find arrows (lines starting with `1,` or `2,`) that connect FROM these valves
  3. Any variable that receives an arrow from a valve is a Stock
- Stocks are drawn as rectangles and accumulate flows

### Auxiliaries
- **Rule**: Everything else
- If not a Flow (ShapeCode ≠ 40) AND not a Stock, then it's an Auxiliary
- Shape codes typically 3 or 8

## 3. Example

**Input sketch data:**
```
10,1,Population,1257,581,66,26,3,3,0,0,-1,0,0,0,0,0,0,0,0,0
10,2,Birth Rate,1100,600,46,26,40,3,0,0,-1,0,0,0,0,0,0,0,0,0
10,3,Birth Fraction,950,580,50,25,8,3,0,0,-1,0,0,0,0,0,0,0,0,0
10,4,Custom Var,800,400,60,30,3,3,0,2,-1,1,0,0,0-0-0,0-0-255,|||192-192-192,0,0,0,0,0,0
11,5,0,1180,590,6,8,34,3,0,0,1,0,0,0,0,0,0,0,0,0
1,6,5,1,100,0,0,22,0,192,0,-1--1--1,,1|(1257,581)|
```

**Output JSON:**
```json
{
  "variables": [
    {"id": 1, "name": "Population", "type": "Stock", "x": 1257, "y": 581, "width": 66, "height": 26},
    {"id": 2, "name": "Birth Rate", "type": "Flow", "x": 1100, "y": 600, "width": 46, "height": 26},
    {"id": 3, "name": "Birth Fraction", "type": "Auxiliary", "x": 950, "y": 580, "width": 50, "height": 25},
    {"id": 4, "name": "Custom Var", "type": "Auxiliary", "x": 800, "y": 400, "width": 60, "height": 30, "colors": {"text": "0-0-0", "border": "0-0-255", "fill": "192-192-192"}}
  ]
}
```

## 4. Output Requirements
- Return ONLY valid JSON, no explanations or markdown code blocks
- Use exact IDs and names from the sketch section
- Include width and height for all variables
- Include colors object ONLY if custom colors are present (fields 16-18 have RGB values)
- Schema:
```json
{
  "variables": [
    {
      "id": <int>,
      "name": "<string>",
      "type": "Stock" | "Flow" | "Auxiliary",
      "x": <int>,
      "y": <int>,
      "width": <int>,
      "height": <int>,
      "colors": {"text": "<rgb>", "border": "<rgb>", "fill": "<rgb>"}  // optional
    }
  ]
}
```

MODEL TEXT START
```mdl
{mdl_text}
```
MODEL TEXT END
```

**Template Variables:** `{mdl_text}` - Full Vensim model file content

---

### CONNECTION_PROMPT
**Location:** `src/sd_model/pipeline/llm_extraction.py:52-152`

```text
Extract all causal connections from this Vensim model file with their polarity.

FILE STRUCTURE:
The file has two parts separated by "\---/// Sketch information":
- EQUATIONS (before separator): Define mathematical relationships
- SKETCH (after separator): Define visual diagram with polarity markers

TASK:
1. Extract all connections from equations
2. Determine polarity for each connection using sketch data
3. Output JSON with connection list

POLARITY RULES (check in this order):
1. NEGATIVE: Source variable has "-" prefix in equation (e.g., "A FUNCTION OF(-X, Y)" means X→target is NEGATIVE)
2. POSITIVE: Sketch arrow has EXACTLY value 43 in the 7th field (field[6]=43)
3. UNDECLARED: Everything else (including field[6]=0 or any value other than 43)

IMPORTANT: Only mark as POSITIVE if you find field[6]=43 in a sketch arrow. Do NOT assume positive polarity from equations or valve presence alone.

SKETCH FORMAT:
Lines starting with "10," define variables:
  10,<id>,<name>,...
  Example: 10,93,Implicit Knowledge Transfer,...

Lines starting with "1," define arrows:
  1,arrow_id,from_id,to_id,field4,field5,field6,field7,...
  Example: 1,97,93,80,1,0,43,0,...

  This arrow goes from variable 93 to variable 80.
  The 7th field is 43, so this connection is POSITIVE.
  Split by commas and count: field1=arrow_id, field2=from_id, field3=to_id, field4=1, field5=0, field6=43, field7=0

Lines starting with "11," define valves (flow control symbols):
  11,<valve_id>,...

VALVE HANDLING:
Valves act as intermediaries for flow variables. Two cases:

Case A: Arrow from variable to valve
  1. Find all arrows FROM that valve (arrows where from_id = valve_id)
  2. These arrows point to stocks
  3. Look at each stock's equation to find which flow variable appears in it
  4. The connection is: original_source_variable → that_flow_variable
  5. Check the original arrow to the valve: if field[6]=43 then POSITIVE, else UNDECLARED (or NEGATIVE if equation has "-")

Case B: Arrow from valve to valve
  1. First valve represents a flow variable
  2. Second valve represents another flow variable
  3. Find which flow variables these valves control (by looking at stock equations)
  4. The connection is: first_flow → second_flow
  5. Check the arrow between valves: if field[6]=43 then POSITIVE, else UNDECLARED (or NEGATIVE if equation has "-")

EXAMPLE 1 - Variable to valve (generic scenario):
Equation: "Worker Productivity = A FUNCTION OF(Training Quality,...)"
Sketch arrow: 1,201,15,42,1,0,43,0,...
Sketch valve: 11,42,...
Sketch variable: 10,15,Training Quality,...
Sketch variable: 10,18,Worker Productivity,...

Step 1: Equation shows connection exists (15 → something)
Step 2: Sketch arrow 1,201,15,42 shows arrow from variable 15 to 42 with field[6]=43 (POSITIVE)
Step 3: ID 42 is a valve (found in 11,42,... line)
Step 4: Find arrows FROM valve 42, they point to stocks
Step 5: Check those stock equations to find which flow appears → find "Worker Productivity" (ID 18)
Step 6: Output connection: 15 → 18 with POSITIVE polarity
Reason: "sketch arrow 15→42 (valve) has field[6]=43, valve controls flow 18"

EXAMPLE 2 - Valve to valve (generic scenario):
Equation: "Onboarding Rate = A FUNCTION OF(Hiring Rate)"
Sketch arrow: 1,305,33,37,1,0,43,0,...
Sketch valve: 11,33,... (represents Hiring Rate, ID 52)
Sketch valve: 11,37,... (represents Onboarding Rate, ID 58)

Step 1: Equation shows connection (52 → 58)
Step 2: Sketch arrow 1,305,33,37 shows arrow from valve 33 to valve 37 with field[6]=43 (POSITIVE)
Step 3: Both 33 and 37 are valves (found in 11,33,... and 11,37,... lines)
Step 4: Check stock equations to identify: valve 33 represents flow 52, valve 37 represents flow 58
Step 5: Output connection: 52 → 58 with POSITIVE polarity
Reason: "sketch arrow from valve 33 to valve 37 has field[6]=43, representing flow 52→58"

EXAMPLE 3 - Valve with NO positive marker (generic scenario):
Equation: "Inventory Level = A FUNCTION OF(Production Rate,...)"
Sketch arrow: 1,410,25,200,4,0,0,22,...
Sketch valve: 11,25,...
Sketch variable: 10,12,Production Rate,...

Analysis: Arrow from valve 25 to stock 200 has field[6]=0 (NOT 43)
Even though valve 25 represents flow "Production Rate", the connection 12→200 is UNDECLARED
Do NOT assume positive polarity just because a valve exists - must see field[6]=43

OUTPUT FORMAT (JSON only, no markdown):
```

**Expected JSON Output:**
```json
{
  "connections": [
    {"from": 1, "to": 2, "polarity": "POSITIVE"|"NEGATIVE"|"UNDECLARED"}
  ]
}
```

**Prompt continues:**
```text
MODEL FILE:
{mdl_text}
```

**Template Variables:** `{mdl_text}` - Full Vensim model file content

---

## 2. Feedback Loop Discovery

### Loop Discovery Prompt
**Location:** `src/sd_model/pipeline/llm_loop_classification.py:82-174`

```text
You are an expert in system dynamics and feedback loop analysis. Your task is to discover feedback loops in a system using Donella Meadows' principles from "Thinking in Systems".

MEADOWS' DEFINITIONS:

**Balancing Feedback Loops**:
- Stabilizing, goal-seeking, regulating feedback loops
- They oppose whatever direction of change is imposed on the system
- They are sources of stability and resistance to change
- They keep a stock at a given value or within a range of values
- Create self-correcting behavior, negative feedback
- Examples: thermostat maintaining temperature, water level regulation

**Reinforcing Feedback Loops**:
- Self-enhancing, leading to exponential growth or runaway collapses
- They amplify whatever direction of change is imposed
- They generate more input to a stock the more that stock already exists
- Create virtuous or vicious cycles, compound growth, snowball effects
- Examples: population growth, viral spread, compound interest, "success breeds success"

DOMAIN CONTEXT: {domain_context}

SYSTEM VARIABLES:
{variables_info}

SYSTEM CONNECTIONS:
{connections_info}

TASK:
Discover feedback loops in this system by identifying patterns that exhibit REINFORCING or BALANCING behavior.

A feedback loop exists when you can trace a path through connections that returns to the starting variable, creating a closed cycle.

For EACH loop you discover, determine if it exhibits:
1. REINFORCING behavior (self-amplifying, growth/collapse)
2. BALANCING behavior (self-regulating, goal-seeking)

IMPORTANT GUIDELINES:
- Variable types matter: Stocks accumulate, Flows change stocks, Auxiliaries are derived values
- Consider the semantic meaning in the {domain_context} domain
- Focus on BEHAVIOR the loop creates, not just mathematical structure
- Only report loops that clearly exhibit reinforcing or balancing characteristics
- Provide detailed reasoning explaining WHY each loop exhibits its behavior
- Confidence should reflect how clearly the loop exhibits the behavior (0.0-1.0)

OUTPUT FORMAT (JSON):
```

**Expected JSON Output:**
```json
{
  "reinforcing": [
    {
      "id": "R01",
      "variables": ["Var1", "Var2", "Var3"],
      "edges": [
        {"from_var": "Var1", "to_var": "Var2", "relationship": "positive"},
        {"from_var": "Var2", "to_var": "Var3", "relationship": "positive"},
        {"from_var": "Var3", "to_var": "Var1", "relationship": "positive"}
      ],
      "length": 3,
      "loop": "Var1 → Var2 → Var3 → Var1",
      "confidence": 0.85
    }
  ],
  "balancing": [
    {
      "id": "B01",
      "variables": ["VarA", "VarB"],
      "edges": [
        {"from_var": "VarA", "to_var": "VarB", "relationship": "negative"},
        {"from_var": "VarB", "to_var": "VarA", "relationship": "positive"}
      ],
      "length": 2,
      "loop": "VarA → VarB → VarA",
      "confidence": 0.9
    }
  ]
}
```

**Prompt ends:**
```text
Your response (JSON only, no additional text):
```

**Template Variables:**
- `{domain_context}` - Domain description (e.g., "open source software development")
- `{variables_info}` - List of variables with types
- `{connections_info}` - List of connections with relationships

---

## 3. Descriptions Generation

### Connection Description Prompt
**Location:** `src/sd_model/pipeline/connection_descriptions.py:81-118`

```text
You are an expert in system dynamics and {domain_context}. Your task is to provide brief descriptions for causal connections in a system dynamics model.

DOMAIN CONTEXT: {domain_context}

CONNECTIONS TO DESCRIBE:
{connections_info}

TASK:
For each connection, provide a brief 1-sentence description explaining the causal relationship between the variables. Focus on WHY and HOW the source variable affects the target variable in the context of {domain_context}.

GUIDELINES:
- Keep descriptions concise (1 sentence, ~10-20 words)
- Explain the causal mechanism
- Consider variable types: Stocks accumulate, Flows change stocks, Auxiliaries are derived
- Use domain-appropriate language
- For positive relationships: explain how increases in source lead to increases in target
- For negative relationships: explain how increases in source lead to decreases in target

OUTPUT FORMAT (JSON only, no additional text):
```

**Expected JSON Output:**
```json
{
  "descriptions": [
    {"id": "C01", "description": "More core developers increase mentorship capacity and knowledge transfer opportunities"},
    {"id": "C02", "description": "Higher mentorship quality accelerates skill development for new contributors"}
  ]
}
```

**Prompt ends:**
```text
IMPORTANT: Output ONLY the IDs and descriptions. Do not repeat the full connection details.

Your response (JSON only):
```

**Template Variables:**
- `{domain_context}` - Domain description
- `{connections_info}` - Formatted list of connections with IDs, from/to vars, types, relationships

---

### Loop Description Prompt
**Location:** `src/sd_model/pipeline/loop_descriptions.py:71-107`

```text
You are an expert in system dynamics and {domain_context}. Your task is to provide brief descriptions for feedback loops in a system dynamics model.

DOMAIN CONTEXT: {domain_context}

LOOPS TO DESCRIBE:
{loops_info}

TASK:
For each loop, provide a brief 1-2 sentence description explaining the feedback mechanism. Focus on WHY this creates reinforcing/balancing behavior and HOW it impacts the system.

GUIDELINES:
- Keep descriptions concise (1-2 sentences, ~20-40 words)
- Explain the feedback mechanism and system behavior
- For reinforcing loops: explain how changes amplify over time
- For balancing loops: explain how the system seeks equilibrium
- Use domain-appropriate language for {domain_context}

OUTPUT FORMAT (JSON only, no additional text):
{
  "descriptions": [
    {"id": "R01", "description": "This virtuous cycle amplifies project success as reputation attracts contributors who improve quality, further enhancing reputation"},
    {"id": "B01", "description": "This balancing loop prevents unbounded issue accumulation by creating pressure to resolve issues as they build up"},
    ...
  ]
}

IMPORTANT: Output ONLY the IDs and descriptions. Do not repeat the full loop details.

Your response (JSON only):
```

**Template Variables:**
- `{domain_context}` - Domain description
- `{loops_info}` - Formatted list of loops with IDs, types, and variables

---

## 4. Citation Finding

### Citation Suggestion Prompt
**Location:** `src/sd_model/pipeline/connection_citations.py:73-147`

```text
You are an expert in system dynamics and open source software research. Your task is to suggest relevant academic papers that support causal connections in an open source software development system dynamics model.

Think step by step. Consider the question carefully and think of the academic or professional expertise of someone that could best answer this question. You have the experience of someone with expert knowledge in that area. Be helpful and answer in detail while preferring to use information from reputable sources.

CONNECTIONS TO CITE:
{connections_info}

TASK:
For EVERY connection, suggest at least 3 relevant academic papers from your knowledge of the literature. You MUST find at least 3 papers for each connection.

GUIDELINES:
- Suggest papers about open source software development, community dynamics, software engineering, or related fields
- Each paper should support the specific causal connection (can be indirect support)
- Provide citation information: title, first 2 authors (use "et al." if more), year
- Suggest at least 3 papers per connection (prefer 3 or more)
- Explain why each paper is relevant to the connection
- Be creative: if no direct study exists, cite related work, theoretical frameworks, or analogous findings
- ALL connections must appear in the output with at least 3 papers
- Even for basic flow relationships, cite papers that describe the process or mechanism

OUTPUT FORMAT (JSON only):
{
  "citations": [
    {
      "connection_id": "C01",
      "papers": [
        {
          "title": "Joining the bazaar: Onboarding in open source projects",
          "authors": "Steinmacher, I., Silva, M. A. G., et al.",
          "year": "2015",
          "relevance": "Discusses how experienced contributors mentor newcomers in OSS projects"
        },
        {
          "title": "Community, joining process and innovation in open source software",
          "authors": "von Krogh, G., Spaeth, S., et al.",
          "year": "2003",
          "relevance": "Provides evidence for knowledge transfer through community engagement"
        }
      ],
      "reasoning": "This connection is well-supported in OSS literature, particularly in studies of contributor progression and knowledge transfer mechanisms."
    },
    {
      "connection_id": "C04",
      "papers": [
        {
          "title": "Why developers contribute to open source projects",
          "authors": "Hars, A., Ou, S.",
          "year": "2002",
          "relevance": "Identifies problem-solving as a key motivation for OSS contribution"
        }
      ],
      "reasoning": "Research on OSS contributor motivation supports this connection."
    }
  ]
}

IMPORTANT:
- ALL {len(connections)} connections MUST appear in output with at least 3 papers
- Do NOT skip any connections
- Only suggest real academic papers that you are confident exist
- Do not hallucinate or make up papers
- If direct evidence is limited, cite foundational work, theoretical frameworks, or analogous studies

Your response (JSON only):
```

**Template Variables:**
- `{connections_info}` - Formatted list of connections with IDs, from/to vars, relationships, descriptions
- `{len(connections)}` - Count of connections

**Note:** This prompt uses OpenAI GPT-5 (not DeepSeek) for better citation accuracy.

---

## 5. Theory Development Modules

### Theory Enhancement Prompt
**Location:** `src/sd_model/pipeline/theory_enhancement.py:48-115`

```text
You are a system dynamics modeling expert.

# Current System Dynamics Model

## Current Variables
{vars_text}

## Current Connections
{conns_text}

# Theories Being Used
{theories_text}

# Your Task

Analyze the model and identify what needs to be added, modified, or removed based on each theory.

For each theory, provide specific model operations:

1. **Additions** - New variables and connections to add (optional, leave empty if none)
2. **Modifications** - Existing variables to update (optional, leave empty if none)
3. **Removals** - Variables to deprecate or remove (optional, leave empty if none)

Return JSON in this structure:

{
  "theories": [
    {
      "name": "Theory Name",
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
- Focus on practical, implementable operations
- Be specific about variable names and types
- Only include additions/modifications/removals if truly needed
- For additions.connections, you can reference both existing variables and newly added variables

Return ONLY the JSON structure, no additional text.
```

**Template Variables:**
- `{vars_text}` - All current variables (format: "- Name (Type)")
- `{conns_text}` - All current connections (format: "- From → To (relationship)")
- `{theories_text}` - Formatted list of theories with descriptions

**Temperature:** 0.2

---

### RQ-Theory-Model Alignment Prompt
**Location:** `src/sd_model/pipeline/rq_alignment.py:15-148`

```text
You are a PhD research methodology expert. Evaluate the alignment between research questions, theoretical framework, and system dynamics model.

# Research Questions
{rqs_text}

# Current Theories
{theories_text}

# Model Summary
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

# Sample Model Variables
{vars_text}

# Sample Model Connections
{conns_text}

# Your Task

Provide a detailed evaluation of how well the research questions can be answered with the current theories and model. For each RQ, assess:

1. **Alignment Score** (1-10): How well can this RQ be answered?
2. **Theory Fit**: Do the current theories support this RQ?
3. **Model Fit**: Does the model structure enable answering this RQ?
4. **Critical Issues**: What's preventing full coverage?
5. **Recommendations**: What should be added/removed/modified?

Return JSON in this structure:

{
  "overall_assessment": {
    "model_rq_fit": "poor|moderate|good|excellent",
    "theory_rq_fit": "poor|moderate|good|excellent",
    "coherence": "poor|moderate|good|excellent",
    "phd_viability": "poor|moderate|good|excellent",
    "summary": "overall assessment in 2-3 sentences"
  },
  "rq_1": {
    "alignment_score": 1-10,
    "theory_fit": {
      "score": 1-10,
      "assessment": "how well theories support this RQ",
      "gaps": ["missing theoretical elements"]
    },
    "model_fit": {
      "score": 1-10,
      "assessment": "how well model structure enables answering this",
      "gaps": ["missing model elements"]
    },
    "critical_issues": [
      {
        "issue": "what's wrong",
        "severity": "low|medium|high|critical"
      }
    ],
    "recommendations": {
      "theories_to_add": [
        {
          "theory": "theory name",
          "why": "why it would help"
        }
      ],
      "theories_to_remove": [],
      "model_additions": ["what to add to model"],
      "priority": "low|medium|high"
    }
  },
  "rq_2": {
    "alignment_score": 1-10,
    "theory_fit": { ... },
    "model_fit": { ... },
    "critical_issues": [ ... ],
    "recommendations": { ... }
  },
  "rq_3": {
    "alignment_score": 1-10,
    "theory_fit": { ... },
    "model_fit": { ... },
    "critical_issues": [ ... ],
    "recommendations": { ... }
  },
  "actionable_steps": [
    {
      "step": "what to do",
      "rationale": "why this helps",
      "impact": "high|medium|low",
      "effort": "low|medium|high"
    }
  ]
}

Be honest and critical. If something doesn't fit well, say so clearly.

Return ONLY the JSON structure, no additional text.
```

**Template Variables:**
- `{rqs_text}` - Numbered list of research questions
- `{theories_text}` - List of theories with descriptions and focus areas
- `{var_count}`, `{conn_count}`, `{loop_count}` - Model statistics
- `{vars_text}` - Sample variables (first 8)
- `{conns_text}` - Sample connections (first 8)

**Temperature:** 0.1

---

### RQ Refinement Prompt
**Location:** `src/sd_model/pipeline/rq_refinement.py:15-119`

```text
You are a PhD research methodology expert specializing in system dynamics. Help refine these research questions to be more focused, measurable, and aligned with the model and theoretical framework.

# Current Research Questions
{rqs_text}

# Model Capabilities
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

# Current Alignment Assessment
{alignment_summary}

# Your Task

For each RQ, provide:
1. **Issues** with current formulation
2. **Refined versions** (2-3 alternatives)
3. **New RQ suggestions** based on model insights
4. **PhD-worthiness assessment**

Criteria for good RQs:
- Specific and measurable
- Aligned with model capabilities
- Theoretically grounded
- Contributes to knowledge
- Feasible within PhD scope

Return JSON in this structure:

{
  "current_rqs": ["RQ1...", "RQ2...", "RQ3..."],
  "refinement_suggestions": [
    {
      "rq_number": 1,
      "original": "original RQ text",
      "issues": [
        "too broad",
        "not measurable",
        "doesn't specify mechanism"
      ],
      "refined_versions": [
        {
          "version": "refined RQ text",
          "rationale": "why this is better",
          "sd_modelability": "poor|moderate|good|excellent",
          "theoretical_grounding": "poor|moderate|good|excellent",
          "phd_worthiness": 1-10,
          "feasibility": "low|medium|high",
          "contribution": "what new knowledge this adds"
        }
      ],
      "recommendation": "which refined version is best and why"
    }
  ],
  "new_rq_suggestions": [
    {
      "suggested_rq": "new RQ based on model insights",
      "based_on_model": "what model feature suggests this",
      "theoretical_basis": "which theory/theories support this",
      "phd_worthiness": 1-10,
      "originality": "assessment of novelty",
      "rationale": "why this is worth investigating"
    }
  ],
  "overall_strategy": {
    "recommended_approach": "focus|broaden|pivot",
    "reasoning": "why this strategy is best",
    "trade_offs": "what you gain and lose with this approach"
  }
}

Be creative but grounded. Suggest RQs that are ambitious but achievable.

Return ONLY the JSON structure, no additional text.
```

**Template Variables:**
- `{rqs_text}` - Numbered list of research questions
- `{var_count}`, `{conn_count}`, `{loop_count}` - Model statistics
- `{alignment_summary}` - Per-RQ alignment scores and issues from Module 3

**Temperature:** 0.3

---

### Theory Discovery Prompt
**Location:** `src/sd_model/pipeline/theory_discovery.py:14-141`

```text
You are an expert in organizational theory, knowledge management, software engineering, and system dynamics. Recommend new theories that could strengthen this PhD research project.

# Research Questions
{rqs_text}

# Current Theories
{theories_text}

# Gaps and Recommendations from Alignment Analysis
{gaps_and_recommendations}

# Your Task

Recommend theories at three levels:
1. **Direct**: Clearly relevant to current RQs and model
2. **Adjacent**: Slightly different angle, creative connection
3. **Cross-domain**: Provocative parallels from other fields

For each theory, provide:
- Theory name and key scholars
- Relevance to RQs and model
- Adjacency level (direct, adjacent, exploratory)
- PhD contribution potential
- Risk/reward assessment

Return JSON in this structure:

{
  "high_relevance": [
    {
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description of theory",
      "relevance_to_rqs": "how it addresses RQs",
      "relevance_to_model": "how it could be modeled in SD",
      "adjacency_level": "direct",
      "phd_contribution": "what novel contribution this enables",
      "model_additions": ["what to add to model"],
      "risk": "low|medium|high",
      "reward": "low|medium|high"
    }
  ],
  "adjacent_opportunities": [
    {
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description",
      "why_adjacent": "why slightly off-center but valuable",
      "novel_angle": "what new perspective this brings",
      "adjacency_level": "adjacent",
      "phd_contribution": "potential contribution",
      "risk": "medium|high",
      "reward": "medium|high"
    }
  ],
  "cross_domain_inspiration": [
    {
      "theory": "Theory from different field",
      "source_domain": "where it comes from",
      "parallel": "how it relates to OSS development",
      "transfer_potential": "what insight could transfer",
      "adjacency_level": "exploratory",
      "risk": "high",
      "reward": "low|medium|high",
      "rationale": "why this is worth considering despite risk"
    }
  ],
  "phd_strategy": {
    "recommended_theories": ["list of 2-3 top recommendations"],
    "rationale": "why these specific theories",
    "integration_strategy": "how to integrate them with existing theories",
    "expected_impact": "what this enables for the PhD"
  }
}

Focus on theories that:
- Are established (not trendy buzzwords)
- Have empirical foundation
- Can be modeled in SD
- Contribute to knowledge gaps

Be bold but responsible - suggest theories that advance the work without derailing it.

Return ONLY the JSON structure, no additional text.
```

**Template Variables:**
- `{rqs_text}` - Numbered list of research questions
- `{theories_text}` - List of current theories with descriptions
- `{gaps_and_recommendations}` - Extracted from RQ alignment results (Module 3)

**Temperature:** 0.4

---

## 6. UI & Analysis

### Loop Classification Prompt (UI)
**Location:** `src/sd_model/ui_streamlit.py:439-446`

```text
You are a system dynamics analyst. Classify the feedback loop type.
Return JSON with keys: type (reinforcing|balancing|undetermined) and reason.
If you are unsure, choose undetermined.
Variables (ordered): {vars_text}
Loop edges:
{edges_text}
Loop context: {description or 'n/a'}
```

**Template Variables:**
- `{vars_text}` - Comma-separated list of variables
- `{edges_text}` - Formatted loop edges with relationships
- `{description}` - Optional loop description

**Temperature:** 0.0 (default for complete method)

---

### Enhanced Loop Analysis Prompt (UI)
**Location:** `src/sd_model/ui_streamlit.py:570-585`

```text
You are analyzing a feedback loop in an open-source software (OSS) community model.

Loop Description: {description}
Loop Type: {loop_type}
Variables: {vars_text}

Edges:
{edges_text}{theory_text}{novel_text}

Please provide a comprehensive analysis in JSON format with these keys:
1. "behavioral_explanation": 2-3 sentences explaining how this loop behaves and what dynamics it creates
2. "system_impact": One word - "positive", "negative", or "mixed"
3. "key_insight": One concise sentence capturing the most important takeaway
4. "intervention": Optional - suggest where to intervene if this loop is problematic (or empty string)

Return ONLY valid JSON.
```

**Template Variables:**
- `{description}` - Loop description
- `{loop_type}` - Loop type (reinforcing/balancing/undetermined)
- `{vars_text}` - Comma-separated variables
- `{edges_text}` - Formatted edges
- `{theory_text}` - Theory support info (if any)
- `{novel_text}` - Novel connections info (if any)

**Temperature:** 0.3

---

### Chat Assistant System Prompt
**Location:** `src/sd_model/ui_streamlit.py:1031-1071`

```text
You are an expert System Dynamics assistant helping a researcher understand and improve their SD model of open-source software communities.

MODEL OVERVIEW:
- Total Variables: {len(variables)}
- Connections: {len(connections)}
- Focus: OSS community dynamics, contributor development, knowledge management

VARIABLES:
Stocks ({len(stocks)}): {", ".join(stocks) if stocks else "None"}
Flows ({len(flows)}): {", ".join(flows) if flows else "None"}
Auxiliaries ({len(auxiliaries)}): {", ".join(auxiliaries) if auxiliaries else "None"}

CONNECTIONS:
{connection details with descriptions, limited to first 50}

YOUR ROLE:
- Answer questions about the model structure and variables
- Suggest improvements or new connections
- Discuss System Dynamics concepts in the context of OSS communities
- Help the researcher understand their model better
- Be conversational, helpful, and concise

When suggesting new variables or connections, explain the SD rationale and how they fit the OSS community context.
```

**Template Variables:**
- `{len(variables)}`, `{len(connections)}` - Counts
- `{len(stocks)}`, `{len(flows)}`, `{len(auxiliaries)}` - Type counts
- `{stocks}`, `{flows}`, `{auxiliaries}` - Variable name lists
- Connection details - First 50 connections with descriptions

**Temperature:** 0.7 (for chat interaction)

---

## 7. Gap Analysis

### Search Query Generation Prompt
**Location:** `src/sd_model/pipeline/gap_analysis.py:98-114`

```text
You are a research assistant helping find academic papers about system dynamics.

Context: We are modeling {context}.

We have a causal connection in our model:
- From: "{connection['from_var']}"
- To: "{connection['to_var']}"
- Relationship: {connection['relationship']}

This connection currently has no citations from academic literature.

Please suggest 3-5 search queries to find relevant academic papers that might support or explain this relationship.

Return ONLY a JSON array of search query strings, like:
["query 1", "query 2", "query 3"]

Make queries specific, academic, and likely to find relevant papers in Semantic Scholar.
```

**Template Variables:**
- `{context}` - Domain context (default: "open-source software community dynamics")
- `{connection['from_var']}` - Source variable
- `{connection['to_var']}` - Target variable
- `{connection['relationship']}` - Relationship type

**Temperature:** 0.3

---

## Summary

**Total Prompts:** 12
**Files:** 9
**Primary Provider:** DeepSeek
**Special Cases:** OpenAI GPT-5 for citations only
**Temperature Range:** 0.0-0.7

All prompts request JSON-only responses with fallback parsing for malformed output.

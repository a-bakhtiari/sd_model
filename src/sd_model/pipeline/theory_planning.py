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
    model_name: str = None
) -> str:
    """Create prompt for Step 1: Strategic Theory Planning - CONDENSED.

    Args:
        theories: List of available theories
        current_model_summary: Summary of the current model structure
        model_name: Optional name of the model being enhanced

    Returns:
        Prompt string for LLM
    """

    # Format theories list
    theories_text = "\n".join([
        f"{i+1}. **{t['name']}**\n   {t.get('core_concept', '')[:200]}"
        for i, t in enumerate(theories)
    ])

    # Model context
    model_context = f"**Model**: {model_name or 'System Dynamics Model'}\n**Current Structure**: {current_model_summary.get('variables', 0)} variables, {current_model_summary.get('connections', 0)} connections"

    prompt = f"""# Strategic Theory Planning for SD Enhancement

## Context

You are planning how theories can enhance an existing SD model through process-based decomposition.

{model_context}

## Available Theories ({len(theories)} total)

{theories_text}

---

# Your Task: Strategic Planning

## 1. Theory Evaluation

For each theory, decide:
- **include**: Theory applies well to this model context
- **exclude**: Theory doesn't fit this context

## 2. Process-Based Clustering

Design 3-5 process clusters that represent distinct system aspects. Each cluster should be a self-contained process that transforms inputs to outputs.

## Writing Mechanistic Narratives

**IMPORTANT**: Do NOT label variable types (Stock, Flow, Auxiliary). Focus on mechanisms.

Your narratives must describe:

### Required Elements:

1. **Accumulations**: What builds up or depletes over time
   - "The pool of peripheral members grows when..."
   - "Knowledge accumulates through..."
   - "Trust builds up slowly over..."

2. **Rates and Speeds**: How fast things change
   - "Members transition at a rate determined by..."
   - "Documentation occurs at a pace limited by..."
   - "The speed of adoption depends on..."

3. **Feedback Loops**: Reinforcing or balancing cycles
   - "Reinforcing: More X leads to more Y, which creates more X"
   - "Balancing: As gap increases, adjustment rate increases to close it"

4. **Time Delays**: How long processes take
   - "It takes 6-12 months for newcomers to..."
   - "Benefits appear with a 3-month delay..."

5. **Nonlinearities**: Thresholds, saturation, tipping points
   - "Progress accelerates after 10+ interactions..."
   - "Effectiveness saturates when ratio exceeds 1:8..."

6. **Causal Relationships**: What drives what
   - "Transfer rate is limited by available mentors..."
   - "Quality increases with expert contributions..."

### Narrative Checklist:
✓ 2-4 accumulations described
✓ 2-4 rates/speeds mentioned
✓ At least 1 feedback loop stated
✓ Time constants specified
✓ Causal drivers explicit
✓ Constraints/limits noted

## Process Design Requirements

Each process must have:
- **Name**: Clear, descriptive process name
- **Narrative**: Mechanistically rich description (see guidelines above)
- **Theories Used**: Which included theories inform this process
- **Connections**: How this process connects to others
  - feeds_into: Output becomes input for another
  - receives_from: Gets input from another
  - feedback_loop: Bidirectional influence

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
✓ Include accumulations, rates, feedbacks, delays
✓ Design 3-5 focused process clusters
✓ Ensure processes connect (no isolated clusters)
✓ Use additional theories if needed for completeness
"""

    return prompt


def run_theory_planning(
    theories: List[Dict],
    current_model_summary: Dict,
    model_name: str = None,
    llm_client: LLMClient = None
) -> Dict:
    """Execute Step 1: Strategic Theory Planning - CONDENSED.

    Args:
        theories: List of available theories
        current_model_summary: Summary of current model
        model_name: Optional model name
        llm_client: Optional LLM client

    Returns:
        Dict with theory decisions and clustering strategy
    """

    # Create prompt
    prompt = create_planning_prompt(theories, current_model_summary, model_name)

    # Call LLM
    if llm_client is None:
        from ..config import should_use_gpt
        provider, model = should_use_gpt("theory_planning")
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
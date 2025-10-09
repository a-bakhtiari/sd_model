"""
Module 4: Research Question Refiner

Suggests improved RQ formulations based on model capabilities,
theoretical framework, and PhD research standards.
"""
from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def create_refinement_prompt(
    rqs: List[str],
    rq_alignment: Dict,
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> str:
    """Create prompt for RQ refinement suggestions."""

    # Format current RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Calculate model statistics
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Extract alignment scores from Module 3 output
    alignment_summary = ""
    for i in range(1, 4):
        rq_data = rq_alignment.get(f"rq_{i}", {})
        score = rq_data.get("alignment_score", 0)
        issues = rq_data.get("critical_issues", [])
        alignment_summary += f"\nRQ{i} - Alignment Score: {score}/10\n"
        if issues:
            alignment_summary += "Issues:\n"
            for issue in issues:
                alignment_summary += f"  - {issue.get('issue', 'N/A')} (severity: {issue.get('severity', 'unknown')})\n"

    prompt = f"""You are a PhD research methodology expert specializing in system dynamics. Help refine these research questions to be more focused, measurable, and aligned with the model and theoretical framework.

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

{{
  "current_rqs": ["RQ1...", "RQ2...", "RQ3..."],
  "refinement_suggestions": [
    {{
      "rq_number": 1,
      "original": "original RQ text",
      "issues": [
        "too broad",
        "not measurable",
        "doesn't specify mechanism"
      ],
      "refined_versions": [
        {{
          "version": "refined RQ text",
          "rationale": "why this is better",
          "sd_modelability": "poor|moderate|good|excellent",
          "theoretical_grounding": "poor|moderate|good|excellent",
          "phd_worthiness": 1-10,
          "feasibility": "low|medium|high",
          "contribution": "what new knowledge this adds"
        }}
      ],
      "recommendation": "which refined version is best and why"
    }}
  ],
  "new_rq_suggestions": [
    {{
      "suggested_rq": "new RQ based on model insights",
      "based_on_model": "what model feature suggests this",
      "theoretical_basis": "which theory/theories support this",
      "phd_worthiness": 1-10,
      "originality": "assessment of novelty",
      "rationale": "why this is worth investigating"
    }}
  ],
  "overall_strategy": {{
    "recommended_approach": "focus|broaden|pivot",
    "reasoning": "why this strategy is best",
    "trade_offs": "what you gain and lose with this approach"
  }}
}}

Be creative but grounded. Suggest RQs that are ambitious but achievable.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_rq_refinement(
    rqs: List[str],
    rq_alignment: Dict,
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> Dict:
    """Generate RQ refinement suggestions.

    Args:
        rqs: List of research questions from RQ.txt
        rq_alignment: Alignment results from Module 3
        variables: Variables data from variables_llm.json
        connections: Connections data from connections.json
        loops: Loops data from loops.json

    Returns:
        Dictionary with RQ refinement suggestions
    """

    # Create prompt
    prompt = create_refinement_prompt(rqs, rq_alignment, variables, connections, loops)

    # Call LLM
    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.3, max_tokens=4000)

    # Parse response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        return {"error": str(e), "raw_response": response}

    return result

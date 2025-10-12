"""
Module 3: RQ-Theory-Model Alignment Evaluator

Evaluates how well research questions are addressed by the current
combination of theories and model structure.
"""
from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def create_alignment_prompt(
    rqs: List[str],
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> str:
    """Create prompt for RQ-theory-model alignment evaluation."""

    # Calculate model statistics
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = 0
    if loops:
        loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Get sample variables for context
    sample_vars = variables.get("variables", [])[:8]
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in sample_vars
    ])

    # Get sample connections for context
    sample_conns = connections.get("connections", [])[:8]
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in sample_conns
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']} (Focus: {t['focus_area']})"
        for t in theories
    ])

    prompt = f"""You are a PhD research methodology expert. Evaluate the alignment between research questions, theoretical framework, and system dynamics model.

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

{{
  "overall_assessment": {{
    "model_rq_fit": "poor|moderate|good|excellent",
    "theory_rq_fit": "poor|moderate|good|excellent",
    "coherence": "poor|moderate|good|excellent",
    "phd_viability": "poor|moderate|good|excellent",
    "summary": "overall assessment in 2-3 sentences"
  }},
  "rq_1": {{
    "alignment_score": 1-10,
    "theory_fit": {{
      "score": 1-10,
      "assessment": "how well theories support this RQ",
      "gaps": ["missing theoretical elements"]
    }},
    "model_fit": {{
      "score": 1-10,
      "assessment": "how well model structure enables answering this",
      "gaps": ["missing model elements"]
    }},
    "critical_issues": [
      {{
        "issue": "what's wrong",
        "severity": "low|medium|high|critical"
      }}
    ],
    "recommendations": {{
      "theories_to_add": [
        {{
          "theory": "theory name",
          "why": "why it would help"
        }}
      ],
      "theories_to_remove": [],
      "model_additions": ["what to add to model"],
      "priority": "low|medium|high"
    }}
  }},
  "rq_2": {{
    "alignment_score": 1-10,
    "theory_fit": {{ ... }},
    "model_fit": {{ ... }},
    "critical_issues": [ ... ],
    "recommendations": {{ ... }}
  }},
  "rq_3": {{
    "alignment_score": 1-10,
    "theory_fit": {{ ... }},
    "model_fit": {{ ... }},
    "critical_issues": [ ... ],
    "recommendations": {{ ... }}
  }},
  "actionable_steps": [
    {{
      "step": "what to do",
      "rationale": "why this helps",
      "impact": "high|medium|low",
      "effort": "low|medium|high"
    }}
  ]
}}

Be honest and critical. If something doesn't fit well, say so clearly.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_rq_alignment(
    rqs: List[str],
    theories: List[Dict],
    variables: Dict,
    connections: Dict,
    loops: Dict
) -> Dict:
    """Evaluate RQ-theory-model alignment.

    Args:
        rqs: List of research questions from RQ.txt
        theories: List of theory dictionaries from theories.csv
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        loops: Loops data from loops.json

    Returns:
        Dictionary with alignment evaluation
    """

    # Create prompt
    prompt = create_alignment_prompt(rqs, theories, variables, connections, loops)

    # Call LLM
    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.1, max_tokens=4000)

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

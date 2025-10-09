"""
Module 5: Adjacent Theory Discovery

Recommends new theories (direct + adjacent) based on RQs and model gaps.
"""
from __future__ import annotations

import json
from typing import Dict, List

from ..llm.client import LLMClient


def create_discovery_prompt(
    rqs: List[str],
    current_theories: List[Dict],
    rq_alignment: Dict
) -> str:
    """Create prompt for theory discovery."""

    # Format current theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in current_theories
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Extract alignment issues and recommendations
    gaps_and_recommendations = ""
    for i in range(1, 4):
        rq_data = rq_alignment.get(f"rq_{i}", {})
        score = rq_data.get("alignment_score", 0)

        # Get gaps from model_fit and theory_fit
        model_gaps = rq_data.get("model_fit", {}).get("gaps", [])
        theory_gaps = rq_data.get("theory_fit", {}).get("gaps", [])

        # Get theory recommendations
        recs = rq_data.get("recommendations", {}).get("theories_to_add", [])

        if model_gaps or theory_gaps or recs:
            gaps_and_recommendations += f"\nRQ{i} (Alignment: {score}/10):\n"

            if theory_gaps:
                gaps_and_recommendations += "  Theory gaps:\n"
                for gap in theory_gaps:
                    gaps_and_recommendations += f"    - {gap}\n"

            if recs:
                gaps_and_recommendations += "  Suggested theories:\n"
                for rec in recs:
                    gaps_and_recommendations += f"    - {rec.get('theory', 'Unknown')}: {rec.get('why', '')}\n"

    prompt = f"""You are an expert in organizational theory, knowledge management, software engineering, and system dynamics. Recommend new theories that could strengthen this PhD research project.

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

{{
  "high_relevance": [
    {{
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
    }}
  ],
  "adjacent_opportunities": [
    {{
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description",
      "why_adjacent": "why slightly off-center but valuable",
      "novel_angle": "what new perspective this brings",
      "adjacency_level": "adjacent",
      "phd_contribution": "potential contribution",
      "risk": "medium|high",
      "reward": "medium|high"
    }}
  ],
  "cross_domain_inspiration": [
    {{
      "theory": "Theory from different field",
      "source_domain": "where it comes from",
      "parallel": "how it relates to OSS development",
      "transfer_potential": "what insight could transfer",
      "adjacency_level": "exploratory",
      "risk": "high",
      "reward": "low|medium|high",
      "rationale": "why this is worth considering despite risk"
    }}
  ],
  "phd_strategy": {{
    "recommended_theories": ["list of 2-3 top recommendations"],
    "rationale": "why these specific theories",
    "integration_strategy": "how to integrate them with existing theories",
    "expected_impact": "what this enables for the PhD"
  }}
}}

Focus on theories that:
- Are established (not trendy buzzwords)
- Have empirical foundation
- Can be modeled in SD
- Contribute to knowledge gaps

Be bold but responsible - suggest theories that advance the work without derailing it.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_theory_discovery(
    rqs: List[str],
    current_theories: List[Dict],
    rq_alignment: Dict
) -> Dict:
    """Discover new theories to strengthen research.

    Args:
        rqs: List of research questions from RQ.txt
        current_theories: List of theory dictionaries from theories.csv
        rq_alignment: Alignment results from Module 3

    Returns:
        Dictionary with theory discovery recommendations
    """

    # Create prompt
    prompt = create_discovery_prompt(rqs, current_theories, rq_alignment)

    # Call LLM
    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.4, max_tokens=4000)

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

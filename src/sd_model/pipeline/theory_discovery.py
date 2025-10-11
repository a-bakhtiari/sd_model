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
    variables: Dict,
    connections: Dict
) -> str:
    """Create prompt for theory discovery."""

    # Format current theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in current_theories
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Get all variables
    all_vars = variables.get("variables", [])
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in all_vars
    ])

    # Get all connections
    all_conns = connections.get("connections", [])
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in all_conns
    ])

    prompt = f"""You are an expert in theory development and research methodology. Recommend new theories that could strengthen this research project.

# Research Questions
{rqs_text}

# Current System Dynamics Model

## Current Variables
{vars_text}

## Current Connections
{conns_text}

# Current Theories
{theories_text}

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
  ]
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
    variables: Dict,
    connections: Dict
) -> Dict:
    """Discover new theories to strengthen research.

    Args:
        rqs: List of research questions from RQ.txt
        current_theories: List of theory dictionaries from theories.csv
        variables: Variables data from variables.json
        connections: Connections data from connections.json

    Returns:
        Dictionary with theory discovery recommendations
    """

    # Create prompt
    prompt = create_discovery_prompt(rqs, current_theories, variables, connections)

    # Call LLM (use config to determine provider/model)
    from ..config import should_use_gpt
    provider, model = should_use_gpt("theory_discovery")
    client = LLMClient(provider=provider, model=model)
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

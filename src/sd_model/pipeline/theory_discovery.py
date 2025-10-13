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
    connections: Dict,
    plumbing: Dict = None
) -> str:
    """Create prompt for theory discovery."""

    # Format current theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in current_theories
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Use the same model structure formatting as Step 1 (includes clouds)
    from .theory_planning import format_model_structure
    model_structure = format_model_structure(variables, connections, plumbing)

    prompt = f"""You are an expert in theory development and research methodology. Recommend new theories that could strengthen this research project.

# Research Questions
{rqs_text}

# Current System Dynamics Model

{model_structure}

# Current Theories
{theories_text}

# Your Task

Recommend theories that are clearly relevant to the current RQs and model.

For each theory, provide:
- Theory name and key scholars
- Brief description
- Relevance to RQs and model

Return JSON in this structure:

{{
  "recommended_theories": [
    {{
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description of theory",
      "relevance_to_rqs": "how it addresses RQs",
      "relevance_to_model": "how it could be modeled in SD"
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
    connections: Dict,
    plumbing: Dict = None
) -> Dict:
    """Discover new theories to strengthen research.

    Args:
        rqs: List of research questions from RQ.txt
        current_theories: List of theory dictionaries from theories.csv
        variables: Variables data from variables.json
        connections: Connections data from connections.json
        plumbing: Plumbing data from plumbing.json (optional)

    Returns:
        Dictionary with theory discovery recommendations
    """

    # Create prompt
    prompt = create_discovery_prompt(rqs, current_theories, variables, connections, plumbing)

    # Call LLM (use config to determine provider/model)
    from ..config import should_use_gpt
    provider, model = should_use_gpt("theory_discovery")
    client = LLMClient(provider=provider, model=model)
    response = client.complete(prompt, temperature=0.4, max_tokens=8000)

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

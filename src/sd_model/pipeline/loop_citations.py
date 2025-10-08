"""Generate citations for feedback loops using LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ..llm.client import LLMClient
from .citation_utils import generate_citations


def find_loop_citations(
    loops_data: Dict,
    descriptions_data: Dict,
    llm_client: LLMClient,
    out_path: Path,
    max_citations: int = 2
) -> Dict:
    """
    Generate citations for feedback loops using LLM's knowledge.

    The LLM suggests relevant academic papers from its training data,
    not limited to a local knowledge base.

    Args:
        loops_data: Loop data from loops.json (reinforcing + balancing)
        descriptions_data: Descriptions from loop_descriptions.json
        llm_client: LLM client for suggesting citations
        out_path: Path to write loop_citations.json
        max_citations: Maximum citations per loop (default 2)

    Returns:
        Dict with loop citations and reasoning
    """
    # Create description lookup
    desc_lookup = {
        desc["id"]: desc["description"]
        for desc in descriptions_data.get("descriptions", [])
    }

    # Merge loops with descriptions
    loops_with_desc = []

    for loop in loops_data.get("reinforcing", []) + loops_data.get("balancing", []):
        loop_id = loop.get("id", "")
        if loop_id in desc_lookup:
            loops_with_desc.append({
                "id": loop_id,
                "loop_type": "reinforcing" if loop_id.startswith("R") else "balancing",
                "variables": loop.get("loop", ""),  # Use "loop" field (not "description")
                "description": desc_lookup[loop_id]
            })

    if not loops_with_desc:
        result = {"citations": [], "notes": ["No loops to cite"]}
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # Use shared citation generation function
    result = generate_citations(
        items=loops_with_desc,
        item_type="loop",
        llm_client=llm_client,
        out_path=out_path,
        max_citations=max_citations
    )

    return result

"""Shared utilities for generating citations for connections and loops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..llm.client import LLMClient


def generate_citations(
    items: List[Dict],
    item_type: str,
    llm_client: LLMClient,
    out_path: Path,
    max_citations: int = 3
) -> Dict:
    """
    Generate citations for items (connections or loops) using LLM.

    Args:
        items: List of items with id and description
        item_type: "connection" or "loop" for prompt customization
        llm_client: LLM client for suggesting citations
        out_path: Path to write citations JSON
        max_citations: Maximum citations per item (default 3)

    Returns:
        Dict with citations and reasoning
    """
    if not items:
        result = {"citations": [], "notes": [f"No {item_type}s to cite"]}
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # Create prompt
    prompt = _create_citation_prompt(items, item_type, max_citations)

    try:
        # Use DeepSeek for citation generation
        citation_llm = LLMClient(provider="deepseek")
        response = citation_llm.complete(prompt, temperature=0.1)
        result = _parse_citation_response(response)
    except Exception as e:
        result = {
            "citations": [],
            "notes": [f"LLM citation suggestion failed: {str(e)}"]
        }

    # Write to file
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _create_citation_prompt(
    items: List[Dict],
    item_type: str,
    max_citations: int
) -> str:
    """Create prompt for LLM to suggest citations."""

    # Format items for the prompt
    if item_type == "connection":
        items_info = "\n".join([
            f"  {item['id']}: {item['from_var']} → {item['to_var']} [{item['relationship']}]\n    Description: {item['description']}"
            for item in items
        ])
        task_desc = "causal connections"
    else:  # loop
        items_info = "\n".join([
            f"  {item['id']}: {item.get('loop_type', 'feedback')} loop\n    Description: {item['description']}"
            for item in items
        ])
        task_desc = "feedback loops"

    return f"""You are an expert in system dynamics and open source software research. Your task is to suggest relevant academic papers that support {task_desc} in an open source software development system dynamics model.

Think step by step. Consider the question carefully and think of the academic or professional expertise of someone that could best answer this question. You have the experience of someone with expert knowledge in that area. Be helpful and answer in detail while preferring to use information from reputable sources.

{item_type.upper()}S TO CITE:
{items_info}

TASK:
For EVERY {item_type}, suggest at least 3 relevant academic papers from your knowledge of the literature. You MUST find at least 3 papers for each {item_type}.

GUIDELINES:
- Suggest papers about open source software development, community dynamics, software engineering, or related fields
- Each paper should support the specific {task_desc} (can be indirect support)
- Provide citation information: title, first 2 authors (use "et al." if more), year
- Suggest at least 3 papers per {item_type} (prefer 3 or more)
- Explain why each paper is relevant
- Be creative: if no direct study exists, cite related work, theoretical frameworks, or analogous findings
- ALL {item_type}s must appear in the output with at least 3 papers
- Even for basic flow relationships, cite papers that describe the process or mechanism

OUTPUT FORMAT (JSON only):
{{
  "citations": [
    {{
      "{item_type}_id": "C01",
      "papers": [
        {{
          "title": "Joining the bazaar: Onboarding in open source projects",
          "authors": "Steinmacher, I., Silva, M. A. G., et al.",
          "year": "2015",
          "relevance": "Discusses how experienced contributors mentor newcomers in OSS projects"
        }},
        {{
          "title": "Community, joining process and innovation in open source software",
          "authors": "von Krogh, G., Spaeth, S., et al.",
          "year": "2003",
          "relevance": "Provides evidence for knowledge transfer through community engagement"
        }}
      ],
      "reasoning": "This {task_desc} is well-supported in OSS literature."
    }},
    {{
      "{item_type}_id": "C04",
      "papers": [
        {{
          "title": "Why developers contribute to open source projects",
          "authors": "Hars, A., Ou, S.",
          "year": "2002",
          "relevance": "Identifies problem-solving as a key motivation for OSS contribution"
        }}
      ],
      "reasoning": "Research on OSS contributor motivation supports this {task_desc}."
    }}
  ]
}}

IMPORTANT:
- ALL {len(items)} {item_type}s MUST appear in output with at least 3 papers
- Do NOT skip any {item_type}s
- Only suggest real academic papers that you are confident exist
- Do not hallucinate or make up papers
- If direct evidence is limited, cite foundational work, theoretical frameworks, or analogous studies

Your response (JSON only):"""


def _parse_citation_response(response: str) -> Dict:
    """Parse LLM response and extract citations."""
    try:
        # Try to extract JSON from response
        response = response.strip()

        # Handle markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Handle cases where LLM adds extra text before/after JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)

            if "citations" not in result:
                result["citations"] = []

            # No validation - LLM only returns items with papers
            # This is intentional to keep output minimal
            return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        pass

    # Fallback
    return {
        "citations": [],
        "notes": [f"Failed to parse LLM response: {response[:200]}..."]
    }

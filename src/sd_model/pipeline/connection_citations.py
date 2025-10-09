from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..llm.client import LLMClient


def find_connection_citations(
    connections_data: Dict,
    descriptions_data: Dict,
    llm_client: LLMClient,
    out_path: Path,
    max_citations: int = 3
) -> Dict:
    """
    Find citations for each connection using LLM's knowledge.

    The LLM suggests relevant academic papers from its training data,
    not limited to a local knowledge base.

    Args:
        connections_data: Connection data from connections.json (with IDs)
        descriptions_data: Descriptions from connection_descriptions.json
        llm_client: LLM client for suggesting citations
        out_path: Path to write connection_citations.json
        max_citations: Maximum citations per connection (default 3)

    Returns:
        Dict with connection citations and reasoning
    """
    # Create description lookup
    desc_lookup = {
        desc["id"]: desc["description"]
        for desc in descriptions_data.get("descriptions", [])
    }

    # Merge connections with descriptions
    connections_with_desc = []
    for conn in connections_data.get("connections", []):
        conn_id = conn.get("id", "")
        if conn_id in desc_lookup:
            connections_with_desc.append({
                **conn,
                "description": desc_lookup[conn_id]
            })

    if not connections_with_desc:
        result = {"citations": [], "notes": ["No connections to cite"]}
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # Create prompt for LLM
    prompt = _create_citation_prompt(connections_with_desc, max_citations)

    try:
        # Use DeepSeek for citation generation
        citation_llm = LLMClient(provider="deepseek")
        response = citation_llm.complete(prompt, temperature=0.1)
        result = _parse_citation_response(response, connections_with_desc)
    except Exception as e:
        result = {
            "citations": [],
            "notes": [f"LLM citation suggestion failed: {str(e)}"]
        }

    # Write to file
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _create_citation_prompt(
    connections: List[Dict],
    max_citations: int
) -> str:
    """Create prompt for LLM to suggest citations from its knowledge."""

    connections_info = "\n".join([
        f"  {conn['id']}: {conn['from_var']} → {conn['to_var']} [{conn['relationship']}]\n    Description: {conn['description']}"
        for conn in connections
    ])

    return f"""You are an expert in system dynamics and open source software research. Your task is to suggest relevant academic papers that support causal connections in an open source software development system dynamics model.

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
{{
  "citations": [
    {{
      "connection_id": "C01",
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
      "reasoning": "This connection is well-supported in OSS literature, particularly in studies of contributor progression and knowledge transfer mechanisms."
    }},
    {{
      "connection_id": "C04",
      "papers": [
        {{
          "title": "Why developers contribute to open source projects",
          "authors": "Hars, A., Ou, S.",
          "year": "2002",
          "relevance": "Identifies problem-solving as a key motivation for OSS contribution"
        }}
      ],
      "reasoning": "Research on OSS contributor motivation supports this connection."
    }}
  ]
}}

IMPORTANT:
- ALL {len(connections)} connections MUST appear in output with at least 3 papers
- Do NOT skip any connections
- Only suggest real academic papers that you are confident exist
- Do not hallucinate or make up papers
- If direct evidence is limited, cite foundational work, theoretical frameworks, or analogous studies

Your response (JSON only):"""


def _parse_citation_response(response: str, connections: List[Dict]) -> Dict:
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

            # No validation - LLM only returns connections with papers
            # This is intentional to keep output minimal
            return result

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        pass

    # Fallback: create placeholder entries
    return {
        "citations": [
            {
                "connection_id": conn["id"],
                "from_var": conn["from_var"],
                "to_var": conn["to_var"],
                "relationship": conn["relationship"],
                "description": conn.get("description", ""),
                "papers": [],
                "reasoning": "Citation suggestion failed"
            }
            for conn in connections
        ],
        "notes": [f"Failed to parse LLM response: {response[:200]}..."]
    }

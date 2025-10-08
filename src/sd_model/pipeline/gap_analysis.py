"""Gap analysis to identify connections and loops lacking citations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..llm.client import LLMClient


def identify_gaps(connection_citations_path: Path, out_path: Path) -> Dict:
    """Identify connections and loops that lack citation support.

    Args:
        connection_citations_path: Path to connection_citations.json
        out_path: Where to save gap analysis results

    Returns:
        Gap analysis data
    """
    data = json.loads(connection_citations_path.read_text(encoding="utf-8"))
    connections = data.get("connections", [])

    # Categorize connections by support level
    unsupported = [c for c in connections if c.get("status") == "unsupported"]
    unverified = [c for c in connections if c.get("status") == "unverified"]
    weak = [c for c in connections if len(c.get("verified_citations", [])) < 2 and c.get("status") != "unsupported"]

    # Analyze loops with low citation coverage
    loop_coverage = {}
    for conn in connections:
        for loop_id in conn.get("in_loops", []):
            if loop_id not in loop_coverage:
                loop_coverage[loop_id] = {"total": 0, "verified": 0, "connections": []}

            loop_coverage[loop_id]["total"] += 1
            loop_coverage[loop_id]["connections"].append(
                f"{conn['from_var']} → {conn['to_var']}"
            )
            if conn.get("status") == "verified":
                loop_coverage[loop_id]["verified"] += 1

    # Identify weak loops (< 50% citation coverage)
    weak_loops = []
    for loop_id, coverage in loop_coverage.items():
        pct = (coverage["verified"] / coverage["total"] * 100) if coverage["total"] > 0 else 0
        if pct < 50:
            weak_loops.append({
                "loop_id": loop_id,
                "coverage_pct": round(pct, 1),
                "verified": coverage["verified"],
                "total": coverage["total"],
                "connections": coverage["connections"],
            })

    # Sort by priority
    weak_loops.sort(key=lambda x: (x["coverage_pct"], -x["total"]))

    result = {
        "summary": {
            "unsupported_connections": len(unsupported),
            "unverified_connections": len(unverified),
            "weak_connections": len(weak),
            "weak_loops": len(weak_loops),
        },
        "unsupported_connections": unsupported,
        "unverified_connections": unverified,
        "weak_connections": weak,
        "weak_loops": weak_loops,
    }

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def suggest_search_queries_llm(
    connection: Dict,
    llm_client: LLMClient,
    context: str = "open-source software community dynamics"
) -> List[str]:
    """Use LLM to suggest search queries for finding papers about a connection.

    Args:
        connection: Connection dict with from_var, to_var, relationship
        llm_client: LLM client for generating suggestions
        context: Context description of the model domain

    Returns:
        List of suggested search query strings
    """
    if not llm_client.enabled:
        # Fallback: generate basic query
        return [
            f"{connection['from_var']} {connection['to_var']} {context}",
            f"relationship between {connection['from_var']} and {connection['to_var']}",
        ]

    prompt = f"""You are a research assistant helping find academic papers about system dynamics.

Context: We are modeling {context}.

We have a causal connection in our model:
- From: "{connection['from_var']}"
- To: "{connection['to_var']}"
- Relationship: {connection['relationship']}

This connection currently has no citations from academic literature.

Please suggest 3-5 search queries to find relevant academic papers that might support or explain this relationship.

Return ONLY a JSON array of search query strings, like:
["query 1", "query 2", "query 3"]

Make queries specific, academic, and likely to find relevant papers in Semantic Scholar."""

    response = llm_client.complete(prompt, temperature=0.3)

    try:
        queries = json.loads(response)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries[:5]  # Limit to 5
    except Exception:
        pass

    # Fallback if LLM response is invalid
    return [
        f"{connection['from_var']} {connection['to_var']} {context}",
        f"causal relationship {connection['from_var']} {connection['to_var']}",
        f"impact of {connection['from_var']} on {connection['to_var']}",
    ]

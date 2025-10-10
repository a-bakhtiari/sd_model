"""Paper discovery using Semantic Scholar for unsupported connections."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..external.semantic_scholar import SemanticScholarClient, Paper
from ..knowledge.types import PaperSuggestion
from ..llm.client import LLMClient
from .gap_analysis import suggest_search_queries_llm


def search_papers_for_connection(
    connection: Dict,
    s2_client: SemanticScholarClient,
    llm_client: LLMClient,
    search_queries: List[str] | None = None,
    limit: int = 10
) -> List[PaperSuggestion]:
    """Search Semantic Scholar for papers relevant to a connection.

    Args:
        connection: Connection dict with from_var, to_var, relationship
        s2_client: Semantic Scholar client
        llm_client: LLM client for query generation
        search_queries: Optional pre-generated search queries
        limit: Max papers to return

    Returns:
        List of PaperSuggestion objects, sorted by relevance
    """
    # Generate search queries if not provided
    if not search_queries:
        search_queries = suggest_search_queries_llm(connection, llm_client)

    # Search for papers using each query
    all_papers: Dict[str, Paper] = {}  # paper_id -> Paper (deduplicate)

    for query in search_queries[:3]:  # Use top 3 queries
        papers = s2_client.search_papers(query, limit=limit)
        for paper in papers:
            if paper.paper_id not in all_papers:
                all_papers[paper.paper_id] = paper

    # Convert to PaperSuggestion with relevance scoring
    suggestions = []
    target_str = f"{connection['from_var']} → {connection['to_var']}"

    for paper in all_papers.values():
        # Simple relevance score based on abstract match
        relevance = _calculate_relevance(paper, connection)

        suggestions.append(PaperSuggestion(
            paper_id=paper.paper_id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            citation_count=paper.citation_count,
            relevance_score=relevance,
            abstract=paper.abstract,
            url=paper.url,
            suggested_for="connection",
            target=target_str,
        ))

    # Sort by relevance (descending) and citation count
    suggestions.sort(key=lambda x: (x.relevance_score, x.citation_count), reverse=True)

    return suggestions[:limit]


def _calculate_relevance(paper: Paper, connection: Dict) -> float:
    """Calculate relevance score for a paper given a connection.

    Simple implementation: check if connection variables appear in title/abstract.
    Range: 0.0 to 1.0
    """
    text = (paper.title + " " + (paper.abstract or "")).lower()

    from_var_words = connection['from_var'].lower().split()
    to_var_words = connection['to_var'].lower().split()

    # Count matches
    from_matches = sum(1 for word in from_var_words if word in text)
    to_matches = sum(1 for word in to_var_words if word in text)

    total_words = len(from_var_words) + len(to_var_words)
    total_matches = from_matches + to_matches

    # Base score from word matches
    word_score = total_matches / total_words if total_words > 0 else 0

    # Bonus for recent papers (last 10 years)
    recency_bonus = 0.0
    if paper.year and paper.year >= 2014:
        years_ago = 2024 - paper.year
        recency_bonus = max(0, (10 - years_ago) / 10 * 0.2)  # Up to +0.2

    # Bonus for highly cited papers
    citation_bonus = 0.0
    if paper.citation_count > 100:
        citation_bonus = min(0.2, paper.citation_count / 1000)  # Up to +0.2

    return min(1.0, word_score + recency_bonus + citation_bonus)


def suggest_papers_for_gaps(
    gaps_path: Path,
    s2_client: SemanticScholarClient,
    llm_client: LLMClient,
    out_path: Path,
    limit_per_gap: int = 5
) -> Dict:
    """Generate paper suggestions for all identified gaps.

    Args:
        gaps_path: Path to gap_analysis.json
        s2_client: Semantic Scholar client
        llm_client: LLM client
        out_path: Where to save suggestions
        limit_per_gap: Max papers per gap

    Returns:
        Paper suggestions data
    """
    gaps_data = json.loads(gaps_path.read_text(encoding="utf-8"))
    unsupported = gaps_data.get("unsupported_connections", [])

    suggestions_list = []

    # Generate suggestions for each unsupported connection
    for conn in unsupported[:20]:  # Limit to top 20 gaps to avoid excessive API calls
        papers = search_papers_for_connection(
            connection=conn,
            s2_client=s2_client,
            llm_client=llm_client,
            limit=limit_per_gap
        )

        if papers:
            suggestions_list.append({
                "target_type": "connection",
                "target": f"{conn['from_var']} → {conn['to_var']}",
                "connection": conn,
                "papers": [p.dict() for p in papers],
            })

    result = {
        "generated_at": gaps_data.get("summary", {}),
        "total_suggestions": len(suggestions_list),
        "suggestions": suggestions_list,
    }

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

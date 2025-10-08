"""Citation verification using Semantic Scholar API."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..external.semantic_scholar import SemanticScholarClient
from ..knowledge.loader import load_bibliography, load_theories
from ..knowledge.types import VerifiedCitation


def verify_all_citations(
    theories_dir: Path,
    bib_path: Path,
    s2_client: SemanticScholarClient,
    out_path: Path,
) -> Dict[str, VerifiedCitation]:
    """Verify all citations in theories using Semantic Scholar.

    Args:
        theories_dir: Directory containing theory YAML files
        bib_path: Path to references.bib
        s2_client: Semantic Scholar API client
        out_path: Where to save verification results

    Returns:
        Dictionary mapping citation_key -> VerifiedCitation
    """
    # Load theories and bibliography
    theories = load_theories(theories_dir)
    try:
        bib_entries = load_bibliography(bib_path)
    except FileNotFoundError:
        bib_entries = {}

    # Collect all unique citation keys from theories
    citation_keys = set()
    for theory in theories:
        citation_keys.add(theory.citation_key)
        for conn in theory.expected_connections:
            citation_keys.update(conn.citations)

    # Verify each citation
    verified_citations: Dict[str, VerifiedCitation] = {}
    timestamp = datetime.utcnow().isoformat() + "Z"

    for citation_key in sorted(citation_keys):
        if not citation_key:
            continue

        # Get BibTeX entry
        bib_entry = bib_entries.get(citation_key)
        if not bib_entry:
            # Citation key not in bibliography
            verified_citations[citation_key] = VerifiedCitation(
                citation_key=citation_key,
                verified=False,
                verified_at=timestamp,
            )
            continue

        # Extract metadata from BibTeX
        title = bib_entry.get("title", "").strip("{}").strip()
        authors_str = bib_entry.get("author", "")
        authors = [a.strip() for a in authors_str.split(" and ")] if authors_str else []
        year_str = bib_entry.get("year", "")
        year = int(year_str) if year_str.isdigit() else None

        # Verify with Semantic Scholar
        paper = s2_client.verify_paper(title=title, authors=authors, year=year)

        if paper:
            # Successfully verified
            verified_citations[citation_key] = VerifiedCitation(
                citation_key=citation_key,
                verified=True,
                paper_id=paper.paper_id,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                citation_count=paper.citation_count,
                url=paper.url,
                abstract=paper.abstract,
                verified_at=timestamp,
            )
        else:
            # Not found in Semantic Scholar
            verified_citations[citation_key] = VerifiedCitation(
                citation_key=citation_key,
                verified=False,
                title=title,
                authors=authors,
                year=year,
                verified_at=timestamp,
            )

    # Save results
    result = {
        "verified_at": timestamp,
        "total_citations": len(verified_citations),
        "verified_count": sum(1 for v in verified_citations.values() if v.verified),
        "unverified_count": sum(1 for v in verified_citations.values() if not v.verified),
        "citations": {k: v.dict() for k, v in verified_citations.items()},
    }

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return verified_citations


def generate_connection_citation_table(
    connections_path: Path,
    theories_dir: Path,
    verified_citations_path: Path,
    loops_path: Path,
    out_path: Path,
) -> Dict:
    """Generate a table mapping connections to their citations.

    Args:
        connections_path: Path to connections.json
        theories_dir: Directory with theory YAMLs
        verified_citations_path: Path to citations_verified.json
        loops_path: Path to loops.json
        out_path: Where to save connection-citation table

    Returns:
        Connection-citation mapping data
    """
    # Load data
    connections_data = json.loads(connections_path.read_text(encoding="utf-8"))
    connections = connections_data.get("connections", [])

    theories = load_theories(theories_dir)

    verified_data = {}
    if verified_citations_path.exists():
        verified_data = json.loads(verified_citations_path.read_text(encoding="utf-8"))
    verified_citations = verified_data.get("citations", {})

    loops_data = {}
    if loops_path.exists():
        loops_data = json.loads(loops_path.read_text(encoding="utf-8"))

    # Build connection -> theories/citations mapping
    connection_map: Dict[tuple, Dict] = {}

    # First pass: get all connections from theories
    for theory in theories:
        for conn in theory.expected_connections:
            key = (conn.from_var, conn.to_var, conn.relationship)
            if key not in connection_map:
                connection_map[key] = {
                    "from_var": conn.from_var,
                    "to_var": conn.to_var,
                    "relationship": conn.relationship,
                    "citations": [],
                    "theories": [],
                    "in_loops": [],
                    "verified_citations": [],
                    "unverified_citations": [],
                }

            connection_map[key]["theories"].append(theory.theory_name)
            for cite_key in conn.citations:
                if cite_key not in connection_map[key]["citations"]:
                    connection_map[key]["citations"].append(cite_key)

                    # Check verification status
                    cite_info = verified_citations.get(cite_key, {})
                    if cite_info.get("verified"):
                        connection_map[key]["verified_citations"].append(cite_key)
                    else:
                        connection_map[key]["unverified_citations"].append(cite_key)

    # Second pass: identify which loops each connection is in
    for loop_type in ["reinforcing", "balancing", "undetermined"]:
        for loop in loops_data.get(loop_type, []):
            loop_id = loop.get("id", "")
            for edge in loop.get("edges", []):
                key = (
                    edge.get("from_var"),
                    edge.get("to_var"),
                    edge.get("relationship"),
                )
                if key in connection_map:
                    connection_map[key]["in_loops"].append(loop_id)

    # Third pass: mark connections not in theories as unsupported
    for conn in connections:
        key = (conn.get("from_var"), conn.get("to_var"), conn.get("relationship"))
        if key not in connection_map:
            # Unsupported connection
            connection_map[key] = {
                "from_var": conn["from_var"],
                "to_var": conn["to_var"],
                "relationship": conn["relationship"],
                "citations": [],
                "theories": [],
                "in_loops": [],
                "verified_citations": [],
                "unverified_citations": [],
                "status": "unsupported",
            }

    # Convert to list
    connection_list = list(connection_map.values())

    # Add status field
    for conn in connection_list:
        if conn.get("status"):
            continue  # Already marked as unsupported
        elif len(conn["verified_citations"]) > 0:
            conn["status"] = "verified"
        elif len(conn["citations"]) > 0:
            conn["status"] = "unverified"
        else:
            conn["status"] = "unsupported"

    # Summary statistics
    summary = {
        "total_connections": len(connection_list),
        "verified": sum(1 for c in connection_list if c["status"] == "verified"),
        "unverified": sum(1 for c in connection_list if c["status"] == "unverified"),
        "unsupported": sum(1 for c in connection_list if c["status"] == "unsupported"),
    }

    result = {"summary": summary, "connections": connection_list}

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

"""Generate CSV exports from pipeline artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict


def load_json(path: Path | None) -> dict:
    """Load JSON file, return empty dict if not found or None."""
    if path is None or not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_fields(fields):
    """Format fields of study list for CSV."""
    if isinstance(fields, list):
        return "; ".join(str(f) for f in fields if f)
    return ""


def generate_connections_csv(
    connections_path: Path,
    descriptions_path: Path,
    variables_path: Path,
    citations_path: Path,
    output_path: Path,
) -> int:
    """Generate connections CSV with all metadata.

    Returns:
        Number of rows written
    """
    # Load data
    connections_data = load_json(connections_path)
    descriptions_data = load_json(descriptions_path)
    variables_data = load_json(variables_path)
    citations_data = load_json(citations_path)

    connections = connections_data.get("connections", [])
    descriptions = {d["id"]: d["description"] for d in descriptions_data.get("descriptions", [])}
    variables = {v["name"]: v["type"] for v in variables_data.get("variables", [])}
    citations = {c["connection_id"]: c for c in citations_data.get("citations", [])}

    # CSV columns
    fieldnames = [
        "connection_id",
        "from_var",
        "to_var",
        "relationship",
        "description",
        "from_type",
        "to_type",
        "citation_title",
        "citation_authors",
        "citation_year",
        "citation_relevance",
        "semantic_scholar_url",
        "semantic_scholar_paper_id",
        "citation_count",
        "abstract",
        "venue",
        "fields_of_study"
    ]

    rows = []

    for conn in connections:
        conn_id = conn.get("id")
        from_var = conn.get("from_var", "")
        to_var = conn.get("to_var", "")
        relationship = conn.get("relationship", "")
        description = descriptions.get(conn_id, "")
        from_type = variables.get(from_var, "")
        to_type = variables.get(to_var, "")

        # Get citations for this connection
        citation_info = citations.get(conn_id)

        if citation_info:
            papers = citation_info.get("papers", [])

            # Create one row per citation
            for paper in papers:
                s2_match = paper.get("semantic_scholar_match", {})

                row = {
                    "connection_id": conn_id,
                    "from_var": from_var,
                    "to_var": to_var,
                    "relationship": relationship,
                    "description": description,
                    "from_type": from_type,
                    "to_type": to_type,
                    "citation_title": paper.get("title", ""),
                    "citation_authors": paper.get("authors", ""),
                    "citation_year": paper.get("year", ""),
                    "citation_relevance": paper.get("relevance", ""),
                    "semantic_scholar_url": s2_match.get("url", ""),
                    "semantic_scholar_paper_id": s2_match.get("paper_id", ""),
                    "citation_count": s2_match.get("citation_count", ""),
                    "abstract": s2_match.get("abstract", ""),
                    "venue": s2_match.get("venue", ""),
                    "fields_of_study": format_fields(s2_match.get("fields_of_study", []))
                }
                rows.append(row)
        else:
            # No citations for this connection
            row = {
                "connection_id": conn_id,
                "from_var": from_var,
                "to_var": to_var,
                "relationship": relationship,
                "description": description,
                "from_type": from_type,
                "to_type": to_type,
                "citation_title": "",
                "citation_authors": "",
                "citation_year": "",
                "citation_relevance": "",
                "semantic_scholar_url": "",
                "semantic_scholar_paper_id": "",
                "citation_count": "",
                "abstract": "",
                "venue": "",
                "fields_of_study": ""
            }
            rows.append(row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def generate_loops_csv(
    loops_path: Path,
    descriptions_path: Path,
    citations_path: Path,
    output_path: Path,
) -> int:
    """Generate loops CSV with all metadata.

    Returns:
        Number of rows written
    """
    # Load data
    loops_data = load_json(loops_path)
    descriptions_data = load_json(descriptions_path)
    citations_data = load_json(citations_path)

    # Collect all loops
    all_loops = []
    for loop_type in ["reinforcing", "balancing", "undetermined"]:
        for loop in loops_data.get(loop_type, []):
            loop["loop_type"] = loop_type
            all_loops.append(loop)

    descriptions = {d["id"]: d["description"] for d in descriptions_data.get("descriptions", [])}
    citations = {c["loop_id"]: c for c in citations_data.get("citations", [])}

    # CSV columns
    fieldnames = [
        "loop_id",
        "loop_type",
        "loop_edges",
        "description",
        "citation_title",
        "citation_authors",
        "citation_year",
        "citation_relevance",
        "semantic_scholar_url",
        "semantic_scholar_paper_id",
        "citation_count",
        "abstract",
        "venue",
        "fields_of_study"
    ]

    rows = []

    for loop in all_loops:
        loop_id = loop.get("id")
        loop_type = loop.get("loop_type", "")

        # Format edges as a path string
        edges = loop.get("edges", [])
        loop_edges = " -> ".join([e.get("from_var", "") for e in edges] + [edges[0].get("from_var", "")] if edges else [])

        description = descriptions.get(loop_id, "")

        # Get citations for this loop
        citation_info = citations.get(loop_id)

        if citation_info:
            papers = citation_info.get("papers", [])

            # Create one row per citation
            for paper in papers:
                s2_match = paper.get("semantic_scholar_match", {})

                row = {
                    "loop_id": loop_id,
                    "loop_type": loop_type,
                    "loop_edges": loop_edges,
                    "description": description,
                    "citation_title": paper.get("title", ""),
                    "citation_authors": paper.get("authors", ""),
                    "citation_year": paper.get("year", ""),
                    "citation_relevance": paper.get("relevance", ""),
                    "semantic_scholar_url": s2_match.get("url", ""),
                    "semantic_scholar_paper_id": s2_match.get("paper_id", ""),
                    "citation_count": s2_match.get("citation_count", ""),
                    "abstract": s2_match.get("abstract", ""),
                    "venue": s2_match.get("venue", ""),
                    "fields_of_study": format_fields(s2_match.get("fields_of_study", []))
                }
                rows.append(row)
        else:
            # No citations for this loop
            row = {
                "loop_id": loop_id,
                "loop_type": loop_type,
                "loop_edges": loop_edges,
                "description": description,
                "citation_title": "",
                "citation_authors": "",
                "citation_year": "",
                "citation_relevance": "",
                "semantic_scholar_url": "",
                "semantic_scholar_paper_id": "",
                "citation_count": "",
                "abstract": "",
                "venue": "",
                "fields_of_study": ""
            }
            rows.append(row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

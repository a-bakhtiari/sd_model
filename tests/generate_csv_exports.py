#!/usr/bin/env python3
"""
Generate CSV exports from pipeline artifacts.

Creates two CSV files:
- connections_export.csv: One row per citation for each connection
- loops_export.csv: One row per citation for each loop

Each row includes all metadata from Semantic Scholar (abstract, venue, etc.)
"""

import csv
import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))


def load_json(path: Path, fallback_path: Path = None) -> dict:
    """Load JSON file, return empty dict if not found."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    if fallback_path and fallback_path.exists():
        print(f"Info: Using fallback {fallback_path.name}")
        with open(fallback_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"Warning: {path.name} not found")
    return {}


def format_authors(authors):
    """Format authors list or string for CSV."""
    if isinstance(authors, list):
        return "; ".join(authors)
    return str(authors) if authors else ""


def format_fields(fields):
    """Format fields of study list for CSV."""
    if isinstance(fields, list):
        return "; ".join(str(f) for f in fields if f)
    return ""


def generate_connections_csv(artifacts_dir: Path, output_path: Path, tests_dir: Path = None):
    """Generate connections CSV with all metadata."""

    # Load data
    connections_data = load_json(artifacts_dir / "connections.json")
    descriptions_data = load_json(artifacts_dir / "connection_descriptions.json")
    variables_data = load_json(artifacts_dir / "variables_llm.json")

    # Try artifacts dir first, fall back to tests dir for verified citations
    fallback = tests_dir / "connection_citations_verified.json" if tests_dir else None
    citations_data = load_json(artifacts_dir / "connection_citations_verified.json", fallback)

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

    print(f"✓ Generated {output_path}")
    print(f"  {len(rows)} rows from {len(connections)} connections")


def generate_loops_csv(artifacts_dir: Path, output_path: Path, tests_dir: Path = None):
    """Generate loops CSV with all metadata."""

    # Load data
    loops_data = load_json(artifacts_dir / "loops.json")
    descriptions_data = load_json(artifacts_dir / "loop_descriptions.json")

    # Try artifacts dir first, fall back to tests dir for verified citations
    fallback = tests_dir / "loop_citations_verified.json" if tests_dir else None
    citations_data = load_json(artifacts_dir / "loop_citations_verified.json", fallback)

    # Collect all loops
    all_loops = []
    for loop_type in ["reinforcing", "balancing", "undetermined"]:
        for loop in loops_data.get(loop_type, []):
            loop["loop_type"] = loop_type
            all_loops.append(loop)

    descriptions = {d["loop_id"]: d["description"] for d in descriptions_data.get("descriptions", [])}
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
        edge_strs = [f"{e.get('from_var', '')} -> {e.get('to_var', '')}" for e in edges]
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

    print(f"✓ Generated {output_path}")
    print(f"  {len(rows)} rows from {len(all_loops)} loops")


def main():
    """Generate both CSV exports."""
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    tests_dir = repo_root / "tests"

    print("Generating CSV exports...")
    print()

    # Generate connections CSV
    connections_csv = tests_dir / "connections_export.csv"
    generate_connections_csv(artifacts_dir, connections_csv, tests_dir)
    print()

    # Generate loops CSV
    loops_csv = tests_dir / "loops_export.csv"
    generate_loops_csv(artifacts_dir, loops_csv, tests_dir)
    print()

    print("Done!")


if __name__ == "__main__":
    main()

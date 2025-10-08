"""Helper functions for creating and managing theories."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from ..external.semantic_scholar import Paper
from ..knowledge.types import Theory, ExpectedConnection, PaperSuggestion


def create_theory_from_paper(
    paper: PaperSuggestion | Paper,
    suggested_connections: List[Dict],
    theory_name: str | None = None,
) -> Theory:
    """Create a Theory object from a paper and suggested connections.

    Args:
        paper: PaperSuggestion or Paper object
        suggested_connections: List of connection dicts to include
        theory_name: Optional custom theory name (defaults to paper title)

    Returns:
        Theory object ready to be saved as YAML
    """
    # Generate theory name from paper title if not provided
    if not theory_name:
        title = paper.title if isinstance(paper, PaperSuggestion) else paper.title
        # Clean up title: remove special chars, limit length
        theory_name = re.sub(r'[^\w\s-]', '', title)
        theory_name = theory_name[:50].strip()

    # Generate citation key from first author + year
    authors = paper.authors if isinstance(paper, PaperSuggestion) else paper.authors
    year = paper.year if isinstance(paper, PaperSuggestion) else paper.year

    first_author = authors[0].split()[-1].lower() if authors else "unknown"
    citation_key = f"{first_author}{year}" if year else f"{first_author}"

    # Convert connections to ExpectedConnection objects
    expected_connections = []
    for conn in suggested_connections:
        expected_connections.append(ExpectedConnection(
            from_var=conn["from_var"],
            to_var=conn["to_var"],
            relationship=conn["relationship"],
            citations=[citation_key],
        ))

    return Theory(
        theory_name=theory_name,
        citation_key=citation_key,
        expected_connections=expected_connections,
    )


def save_theory_yaml(theory: Theory, theories_dir: Path) -> Path:
    """Save a Theory object as a YAML file.

    Args:
        theory: Theory object to save
        theories_dir: Directory to save theory YAML files

    Returns:
        Path to the saved file
    """
    import yaml

    # Generate filename from theory name
    filename = re.sub(r'[^\w\s-]', '', theory.theory_name.lower())
    filename = re.sub(r'\s+', '_', filename)
    filename = f"{filename}.yml"

    file_path = theories_dir / filename

    # Convert to dict for YAML serialization
    theory_dict = {
        "theory_name": theory.theory_name,
        "citation_key": theory.citation_key,
        "expected_connections": [
            {
                "from_var": conn.from_var,
                "to_var": conn.to_var,
                "relationship": conn.relationship,
                "citations": conn.citations,
            }
            for conn in theory.expected_connections
        ]
    }

    # Save as YAML
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(theory_dict, f, default_flow_style=False, allow_unicode=True)

    return file_path


def add_paper_to_bibliography(
    paper: PaperSuggestion | Paper,
    bib_path: Path,
    citation_key: str | None = None,
) -> str:
    """Add a paper to references.bib file.

    Args:
        paper: PaperSuggestion or Paper object
        bib_path: Path to references.bib
        citation_key: Optional custom citation key

    Returns:
        The citation key used
    """
    # Generate citation key if not provided
    if not citation_key:
        authors = paper.authors if isinstance(paper, PaperSuggestion) else paper.authors
        year = paper.year if isinstance(paper, PaperSuggestion) else paper.year
        first_author = authors[0].split()[-1].lower() if authors else "unknown"
        citation_key = f"{first_author}{year}" if year else f"{first_author}"

    # Read existing bibliography
    existing_bib = ""
    if bib_path.exists():
        existing_bib = bib_path.read_text(encoding="utf-8")

    # Check if citation key already exists
    if f"@{{{citation_key}," in existing_bib or f"@article{{{citation_key}," in existing_bib:
        return citation_key  # Already exists

    # Generate BibTeX entry
    authors = paper.authors if isinstance(paper, PaperSuggestion) else paper.authors
    year = paper.year if isinstance(paper, PaperSuggestion) else paper.year
    title = paper.title if isinstance(paper, PaperSuggestion) else paper.title

    authors_bibtex = " and ".join(authors[:5])  # Limit to first 5 authors

    # Determine entry type (article, inproceedings, etc.)
    # Simple heuristic: if venue contains "conference" or "proceedings", use inproceedings
    venue = getattr(paper, 'venue', None)
    entry_type = "article"
    if venue and any(keyword in venue.lower() for keyword in ["conference", "proceedings", "workshop"]):
        entry_type = "inproceedings"

    bibtex_entry = f"""
@{entry_type}{{{citation_key},
  author = {{{authors_bibtex}}},
  title = {{{title}}},
  year = {{{year or "n.d."}}},
"""

    if venue:
        if entry_type == "article":
            bibtex_entry += f"  journal = {{{venue}}},\n"
        else:
            bibtex_entry += f"  booktitle = {{{venue}}},\n"

    bibtex_entry += "}\n"

    # Append to bibliography file
    with open(bib_path, 'a', encoding='utf-8') as f:
        f.write(bibtex_entry)

    return citation_key


def update_theory_yaml(
    theory_path: Path,
    new_connections: List[Dict] | None = None,
    remove_connections: List[Dict] | None = None,
) -> Theory:
    """Update an existing theory YAML file.

    Args:
        theory_path: Path to the theory YAML file
        new_connections: Connections to add
        remove_connections: Connections to remove

    Returns:
        Updated Theory object
    """
    import yaml

    # Load existing theory
    with open(theory_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    expected_connections = data.get("expected_connections", [])

    # Remove connections
    if remove_connections:
        remove_set = {
            (c["from_var"], c["to_var"], c["relationship"])
            for c in remove_connections
        }
        expected_connections = [
            c for c in expected_connections
            if (c["from_var"], c["to_var"], c["relationship"]) not in remove_set
        ]

    # Add new connections
    if new_connections:
        existing_set = {
            (c["from_var"], c["to_var"], c["relationship"])
            for c in expected_connections
        }
        for new_conn in new_connections:
            key = (new_conn["from_var"], new_conn["to_var"], new_conn["relationship"])
            if key not in existing_set:
                expected_connections.append(new_conn)

    # Update data
    data["expected_connections"] = expected_connections

    # Save updated YAML
    with open(theory_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    # Convert to Theory object and return
    expected_conn_objects = [
        ExpectedConnection(**conn) for conn in expected_connections
    ]

    return Theory(
        theory_name=data["theory_name"],
        citation_key=data["citation_key"],
        expected_connections=expected_conn_objects,
    )

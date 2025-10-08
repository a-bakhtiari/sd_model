"""Citation verification using Semantic Scholar API and LLM validation."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..external.semantic_scholar import SemanticScholarClient
from ..knowledge.loader import load_bibliography, load_theories
from ..knowledge.types import VerifiedCitation
from ..llm.client import LLMClient


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


def verify_paper_with_llm(
    original_title: str,
    original_authors: str,
    original_year: str,
    s2_title: str,
    s2_authors: list,
    s2_year: int,
    llm_client: LLMClient,
    debug_file=None
) -> bool:
    """
    Use LLM to validate if Semantic Scholar result matches original citation.

    Two-stage verification:
    1. Search Semantic Scholar for the paper by title
    2. Use LLM to validate that the search result matches the original citation

    Args:
        original_title: Title from LLM-generated citation
        original_authors: Authors string from LLM (e.g., "Smith, J., et al.")
        original_year: Year from LLM citation
        s2_title: Title from Semantic Scholar
        s2_authors: Author list from Semantic Scholar
        s2_year: Year from Semantic Scholar
        llm_client: LLM client for validation
        debug_file: Optional file handle for debug logging

    Returns:
        True if LLM confirms match, False otherwise
    """
    # Format S2 authors for comparison
    s2_authors_str = ", ".join(s2_authors[:3])
    if len(s2_authors) > 3:
        s2_authors_str += ", et al."

    prompt = f"""You are validating academic paper citations. Compare the original citation with the search result from Semantic Scholar.

ORIGINAL CITATION:
Title: {original_title}
Authors: {original_authors}
Year: {original_year}

SEMANTIC SCHOLAR RESULT:
Title: {s2_title}
Authors: {s2_authors_str}
Year: {s2_year}

QUESTION: Do these refer to the same paper? Consider:
- Title may have minor formatting differences (punctuation, capitalization)
- Author names may be formatted differently (first name vs initial)
- Year should match or be very close (±1 year acceptable)

Answer with a single word: "yes" or "no"

Your answer:"""

    try:
        response = llm_client.complete(prompt, temperature=0.0).strip().lower()

        # Log to debug file
        if debug_file:
            debug_file.write("=" * 80 + "\n")
            debug_file.write(f"ORIGINAL: {original_title}\n")
            debug_file.write(f"S2 MATCH: {s2_title}\n")
            debug_file.write("-" * 80 + "\n")
            debug_file.write("PROMPT:\n")
            debug_file.write(prompt)
            debug_file.write("\n" + "-" * 80 + "\n")
            debug_file.write(f"LLM RESPONSE: {response}\n")
            debug_file.write("=" * 80 + "\n\n")

        # Parse response (handle "yes.", "yes\n", etc.)
        if "yes" in response[:10]:
            return True
        else:
            return False
    except Exception as e:
        print(f"  [WARNING] LLM validation failed: {e}")
        if debug_file:
            debug_file.write(f"ERROR: {e}\n\n")
        return False


def verify_llm_generated_citations(
    citations_path: Path,
    output_path: Path,
    s2_client: SemanticScholarClient,
    llm_client: LLMClient,
    debug_path: Path = None,
    verbose: bool = True
) -> Dict:
    """
    Verify LLM-generated citations using Semantic Scholar and LLM validation.

    Args:
        citations_path: Path to citations JSON file (e.g., connection_citations.json)
        output_path: Path to write verified citations JSON
        s2_client: Semantic Scholar client
        llm_client: LLM client for validation
        debug_path: Optional path to write debug log
        verbose: Print progress messages

    Returns:
        Dict with verified citations and summary stats
    """
    if verbose:
        print(f"Loading citations from: {citations_path}")

    with open(citations_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    citations = data.get("citations", [])
    if verbose:
        print(f"Found {len(citations)} items with citations\n")

    # Open debug file if path provided
    debug_file = None
    if debug_path:
        debug_file = open(debug_path, "w", encoding="utf-8")
        debug_file.write("LLM VALIDATION DEBUG LOG\n")
        debug_file.write("=" * 80 + "\n\n")

    total_papers = 0
    verified_papers = 0
    unverified_papers = 0

    verified_citations = []

    for citation in citations:
        item_id = citation.get("connection_id") or citation.get("loop_id", "")
        papers = citation.get("papers", [])
        reasoning = citation.get("reasoning", "")

        if verbose:
            print(f"Verifying {item_id}: {len(papers)} papers")

        verified_papers_list = []

        for paper in papers:
            total_papers += 1

            title = paper.get("title", "")
            authors = paper.get("authors", "")
            year = paper.get("year", "")
            relevance = paper.get("relevance", "")

            if verbose:
                print(f"  - {title[:60]}...")

            # Stage 1: Search Semantic Scholar
            try:
                year_int = int(year) if year else None
            except ValueError:
                year_int = None

            results = s2_client.search_papers(title, limit=1)

            if not results:
                # Paper not found in Semantic Scholar
                if verbose:
                    print(f"    ✗ Not found in Semantic Scholar")
                unverified_papers += 1
                continue

            # Got a result, now validate with LLM
            s2_paper = results[0]

            # Stage 2: LLM validation
            is_match = verify_paper_with_llm(
                original_title=title,
                original_authors=authors,
                original_year=year,
                s2_title=s2_paper.title,
                s2_authors=s2_paper.authors,
                s2_year=s2_paper.year or 0,
                llm_client=llm_client,
                debug_file=debug_file
            )

            if is_match:
                if verbose:
                    print(f"    ✓ Verified (LLM confirmed match)")
                verified_papers_list.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "relevance": relevance,
                    "verified": True,
                    "verification_method": "semantic_scholar_with_llm",
                    "semantic_scholar_match": {
                        "title": s2_paper.title,
                        "authors": s2_paper.authors,
                        "year": s2_paper.year,
                        "url": s2_paper.url,
                        "paper_id": s2_paper.paper_id,
                        "citation_count": s2_paper.citation_count,
                        "abstract": s2_paper.abstract,
                        "venue": s2_paper.venue,
                        "fields_of_study": s2_paper.fields_of_study or []
                    }
                })
                verified_papers += 1
            else:
                if verbose:
                    print(f"    ✗ Mismatch (LLM rejected: '{s2_paper.title[:40]}...')")
                unverified_papers += 1

        # Only save items with at least one verified paper
        if verified_papers_list:
            # Determine the correct ID key (connection_id or loop_id)
            id_key = "connection_id" if "connection_id" in citation else "loop_id"
            verified_citations.append({
                id_key: item_id,
                "papers": verified_papers_list,
                "reasoning": reasoning
            })

    # Create output
    output_data = {
        "citations": verified_citations,
        "summary": {
            "total_papers": total_papers,
            "verified": verified_papers,
            "unverified": unverified_papers,
            "verification_rate": round(verified_papers / total_papers, 3) if total_papers > 0 else 0.0
        }
    }

    # Close debug file
    if debug_file:
        debug_file.close()

    # Write to file
    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")

    # Print summary
    if verbose:
        print(f"\n{'=' * 60}")
        print("VERIFICATION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Output saved to: {output_path}")
        if debug_path:
            print(f"Debug log saved to: {debug_path}")
        print(f"Total papers: {total_papers}")
        print(f"Verified: {verified_papers}")
        print(f"Unverified: {unverified_papers}")
        print(f"Verification rate: {output_data['summary']['verification_rate']:.1%}")
        print(f"{'=' * 60}")

    return output_data

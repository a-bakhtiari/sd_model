#!/usr/bin/env python3
"""
Verify connection citations using Semantic Scholar API and LLM validation.

Two-stage verification:
1. Search Semantic Scholar for the paper by title
2. Use LLM to validate that the search result matches the original citation
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.external.semantic_scholar import SemanticScholarClient
from sd_model.llm.client import LLMClient


def verify_paper_with_llm(
    original_title: str,
    original_authors: str,
    original_year: str,
    s2_title: str,
    s2_authors: list,
    s2_year: int,
    llm_client: LLMClient,
    debug_file = None
) -> bool:
    """
    Use LLM to validate if Semantic Scholar result matches original citation.

    Args:
        original_title: Title from LLM-generated citation
        original_authors: Authors string from LLM (e.g., "Smith, J., et al.")
        original_year: Year from LLM citation
        s2_title: Title from Semantic Scholar
        s2_authors: Author list from Semantic Scholar
        s2_year: Year from Semantic Scholar
        llm_client: LLM client for validation

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
            debug_file.write("="*80 + "\n")
            debug_file.write(f"ORIGINAL: {original_title}\n")
            debug_file.write(f"S2 MATCH: {s2_title}\n")
            debug_file.write("-"*80 + "\n")
            debug_file.write("PROMPT:\n")
            debug_file.write(prompt)
            debug_file.write("\n" + "-"*80 + "\n")
            debug_file.write(f"LLM RESPONSE: {response}\n")
            debug_file.write("="*80 + "\n\n")

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


def verify_citations(
    citations_path: Path,
    output_path: Path,
    s2_client: SemanticScholarClient,
    llm_client: LLMClient,
    debug_path: Path = None
):
    """
    Verify all citations in connection_citations.json.

    Args:
        citations_path: Path to connection_citations.json
        output_path: Path to write connection_citations_verified.json
        s2_client: Semantic Scholar client
        llm_client: LLM client for validation
        debug_path: Optional path to write debug log
    """
    print(f"Loading citations from: {citations_path}")
    with open(citations_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    citations = data.get("citations", [])
    print(f"Found {len(citations)} connections with citations\n")

    # Open debug file if path provided
    debug_file = None
    if debug_path:
        debug_file = open(debug_path, "w", encoding="utf-8")
        debug_file.write("LLM VALIDATION DEBUG LOG\n")
        debug_file.write("="*80 + "\n\n")

    total_papers = 0
    verified_papers = 0
    unverified_papers = 0

    verified_citations = []

    for citation in citations:
        conn_id = citation.get("connection_id", "")
        papers = citation.get("papers", [])
        reasoning = citation.get("reasoning", "")

        print(f"Verifying {conn_id}: {len(papers)} papers")

        verified_papers_list = []

        for paper in papers:
            total_papers += 1

            title = paper.get("title", "")
            authors = paper.get("authors", "")
            year = paper.get("year", "")
            relevance = paper.get("relevance", "")

            print(f"  - {title[:60]}...")

            # Stage 1: Search Semantic Scholar
            try:
                year_int = int(year) if year else None
            except ValueError:
                year_int = None

            results = s2_client.search_papers(title, limit=1)

            if not results:
                # Paper not found in Semantic Scholar
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
                        "citation_count": s2_paper.citation_count
                    }
                })
                verified_papers += 1
            else:
                print(f"    ✗ Mismatch (LLM rejected: '{s2_paper.title[:40]}...')")
                unverified_papers += 1

        # Only save connections with at least one verified paper
        if verified_papers_list:
            verified_citations.append({
                "connection_id": conn_id,
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
    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Output saved to: {output_path}")
    if debug_path:
        print(f"Debug log saved to: {debug_path}")
    print(f"Total papers: {total_papers}")
    print(f"Verified: {verified_papers}")
    print(f"Unverified: {unverified_papers}")
    print(f"Verification rate: {output_data['summary']['verification_rate']:.1%}")
    print(f"{'='*60}")


def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    citations_path = artifacts_dir / "connection_citations.json"
    output_path = repo_root / "tests" / "connection_citations_verified.json"
    debug_path = repo_root / "tests" / "connection_citations_verification_debug.txt"

    # Initialize clients
    print("Initializing Semantic Scholar client...")
    s2_client = SemanticScholarClient()

    print("Initializing LLM client...")
    llm_client = LLMClient()

    if not llm_client.enabled:
        print("ERROR: LLM client not enabled. Check your .env file for DEEPSEEK_API_KEY")
        sys.exit(1)

    print()

    # Verify citations
    verify_citations(
        citations_path=citations_path,
        output_path=output_path,
        s2_client=s2_client,
        llm_client=llm_client,
        debug_path=debug_path
    )


if __name__ == "__main__":
    main()

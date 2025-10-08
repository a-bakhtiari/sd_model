#!/usr/bin/env python3
"""
Test script for generating loop citations.
Fast iteration without running the full pipeline.
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.llm.client import LLMClient
from sd_model.pipeline.citation_utils import generate_citations


def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    loops_path = artifacts_dir / "loops.json"
    descriptions_path = repo_root / "tests" / "loop_descriptions.json"
    output_path = repo_root / "tests" / "loop_citations.json"

    # Load data
    print(f"Loading loops from: {loops_path}")
    with open(loops_path, "r", encoding="utf-8") as f:
        loops_data = json.load(f)

    print(f"Loading descriptions from: {descriptions_path}")
    with open(descriptions_path, "r", encoding="utf-8") as f:
        descriptions_data = json.load(f)

    # Prepare loops with descriptions
    desc_lookup = {desc["id"]: desc["description"] for desc in descriptions_data.get("descriptions", [])}

    loops_with_desc = []
    for loop in loops_data.get("reinforcing", []) + loops_data.get("balancing", []):
        loop_id = loop.get("id", "")
        if loop_id in desc_lookup:
            loops_with_desc.append({
                "id": loop_id,
                "loop_type": "reinforcing" if loop_id.startswith("R") else "balancing",
                "variables": " → ".join(loop.get("variables", [])),
                "description": desc_lookup[loop_id]
            })

    print(f"\nFound {len(loops_with_desc)} loops with descriptions")

    # Initialize LLM client
    print("\nInitializing LLM client...")
    llm_client = LLMClient()

    if not llm_client.enabled:
        print("ERROR: LLM client not enabled. Check your .env file for DEEPSEEK_API_KEY")
        sys.exit(1)

    # Generate citations
    print("\nSuggesting citations for loops from LLM's knowledge...")
    print("This may take a few moments as the LLM suggests relevant papers...\n")

    result = generate_citations(
        items=loops_with_desc,
        item_type="loop",
        llm_client=llm_client,
        out_path=output_path,
        max_citations=2
    )

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Output saved to: {output_path}")

    citations = result.get("citations", [])
    print(f"Citations suggested for: {len(citations)} loops")

    # Count how many loops have papers
    with_papers = sum(1 for c in citations if c.get("papers", []))
    without_papers = len(citations) - with_papers

    print(f"  - With papers: {with_papers}")
    print(f"  - Without papers: {without_papers}")

    if result.get("notes"):
        print(f"\nNotes:")
        for note in result["notes"]:
            print(f"  - {note}")

    # Show first 3 examples with papers
    print(f"\nFirst 3 examples with suggested papers:")
    shown = 0
    for cit in citations:
        if cit.get("papers") and shown < 3:
            print(f"\n  {cit['loop_id']}:")
            print(f"    Papers suggested: {len(cit['papers'])}")
            for paper in cit["papers"]:
                print(f"      - {paper.get('title', 'N/A')}")
                print(f"        Authors: {paper.get('authors', 'N/A')}")
                print(f"        Year: {paper.get('year', 'N/A')}")
                print(f"        Relevance: {paper.get('relevance', 'N/A')}")
            print(f"    Reasoning: {cit.get('reasoning', 'N/A')}")
            shown += 1

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()

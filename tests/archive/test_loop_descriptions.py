#!/usr/bin/env python3
"""
Test script for generating loop descriptions.
Fast iteration without running the full pipeline.
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.llm.client import LLMClient
from sd_model.pipeline.loop_descriptions import generate_loop_descriptions


def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    loops_path = artifacts_dir / "loops.json"
    output_path = repo_root / "tests" / "loop_descriptions.json"

    # Load data
    print(f"Loading loops from: {loops_path}")
    with open(loops_path, "r", encoding="utf-8") as f:
        loops_data = json.load(f)

    reinforcing_count = len(loops_data.get("reinforcing", []))
    balancing_count = len(loops_data.get("balancing", []))
    total_loops = reinforcing_count + balancing_count

    print(f"\nFound {total_loops} loops:")
    print(f"  - Reinforcing: {reinforcing_count}")
    print(f"  - Balancing: {balancing_count}")

    # Initialize LLM client
    print("\nInitializing LLM client...")
    llm_client = LLMClient()

    if not llm_client.enabled:
        print("ERROR: LLM client not enabled. Check your .env file for DEEPSEEK_API_KEY")
        sys.exit(1)

    # Generate descriptions
    print("\nGenerating loop descriptions...")
    print("This may take a few moments as the LLM processes all loops...\n")

    result = generate_loop_descriptions(
        loops_data=loops_data,
        llm_client=llm_client,
        out_path=output_path,
        domain_context="open source software development"
    )

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Output saved to: {output_path}")
    print(f"Descriptions generated: {len(result.get('descriptions', []))}")

    if result.get("notes"):
        print(f"\nNotes:")
        for note in result["notes"]:
            print(f"  - {note}")

    # Show first 3 examples
    descriptions = result.get("descriptions", [])
    if descriptions:
        print(f"\nFirst 3 examples:")
        for desc in descriptions[:3]:
            print(f"  {desc['id']}: {desc['description']}")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()

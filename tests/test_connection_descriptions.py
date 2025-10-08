#!/usr/bin/env python3
"""
Test script for generating connection descriptions.
Fast iteration without running the full pipeline.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.llm.client import LLMClient
from sd_model.pipeline.connection_descriptions import generate_connection_descriptions


def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    connections_path = artifacts_dir / "connections.json"
    variables_path = artifacts_dir / "variables_llm.json"
    output_path = repo_root / "tests" / "connection_descriptions.json"

    # Load data
    print(f"Loading connections from: {connections_path}")
    with open(connections_path, "r", encoding="utf-8") as f:
        connections_data = json.load(f)

    print(f"Loading variables from: {variables_path}")
    with open(variables_path, "r", encoding="utf-8") as f:
        variables_data = json.load(f)

    print(f"\nFound {len(connections_data.get('connections', []))} connections")
    print(f"Found {len(variables_data.get('variables', []))} variables")

    # Initialize LLM client
    print("\nInitializing LLM client...")
    llm_client = LLMClient()

    if not llm_client.enabled:
        print("ERROR: LLM client not enabled. Check your .env file for DEEPSEEK_API_KEY")
        sys.exit(1)

    # Generate descriptions
    print("\nGenerating connection descriptions...")
    print("This may take a few moments as the LLM processes all connections...\n")

    result = generate_connection_descriptions(
        connections_data=connections_data,
        variables_data=variables_data,
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

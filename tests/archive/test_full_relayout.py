#!/usr/bin/env python3
"""
Test full diagram relayout with clustering
"""
from pathlib import Path
import json
from src.sd_model.mdl_full_relayout import reposition_entire_diagram
from src.sd_model.llm.client import LLMClient


def test_full_relayout_oss_model():
    """Test full relayout with clustering on oss_model."""
    print("=" * 80)
    print("Test: Full Diagram Relayout with Clustering (oss_model)")
    print("=" * 80)

    mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
    enhancement_json_path = Path("projects/oss_model/artifacts/theory_enhancement.json")
    output_path = Path("tests/oss_model_full_relayout.mdl")

    # Load enhancement JSON
    with open(enhancement_json_path) as f:
        enhancement_json = json.load(f)

    # Extract new variables and connections
    new_variables = []
    new_connections = []

    for suggestion in enhancement_json.get('missing_from_theories', []):
        sd_impl = suggestion.get('sd_implementation', {})

        for var_spec in sd_impl.get('new_variables', []):
            new_variables.append({
                'name': var_spec['name'],
                'type': var_spec['type'],
                'description': var_spec.get('description', '')
            })

        for conn_spec in sd_impl.get('new_connections', []):
            new_connections.append(conn_spec)

    print(f"\n1. Input: {mdl_path}")
    print(f"2. Output: {output_path}")
    print(f"3. New variables to add: {len(new_variables)}")
    print(f"4. Will reposition ALL variables into clusters")

    # Create LLM client
    try:
        llm_client = LLMClient(provider="deepseek")
    except RuntimeError as e:
        print(f"Error: LLM required for full relayout: {e}")
        return

    # Apply full relayout
    summary = reposition_entire_diagram(
        mdl_path,
        new_variables,
        new_connections,
        output_path,
        llm_client
    )

    print(f"\n5. Summary:")
    if 'error' in summary:
        print(f"   Error: {summary['error']}")
    else:
        print(f"   Variables repositioned: {summary.get('variables_repositioned', 0)}")
        print(f"   Clusters created: {summary.get('clusters', 0)}")

    print(f"\n6. File size: {output_path.stat().st_size} bytes")

    print("\n" + "=" * 80)
    print("✅ Test complete! Open in Vensim to see clustered layout:")
    print(f"   {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    test_full_relayout_oss_model()

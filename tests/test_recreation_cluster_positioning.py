#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Cluster-Aware Spatial Positioning

Tests the new cluster_positions feature where LLM suggests high-level
spatial layout for process clusters based on inter-cluster connections.

This test manually adds cluster_positions to existing theory_concretization_step2.json
to verify the layout algorithm works correctly.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.mdl_creator import create_mdl_from_scratch


def test_cluster_positioning():
    """Test cluster-aware spatial positioning."""

    # Paths
    project_dir = Path(__file__).parent.parent / "projects" / "sd_test"
    theory_json_path = project_dir / "artifacts" / "theory" / "theory_concretization_step2.json"
    original_mdl_path = project_dir / "mdl" / "test.mdl"
    output_mdl_path = Path(__file__).parent / "test_recreation_cluster_positioning.mdl"

    # Load existing theory concretization
    print(f"📖 Loading theory concretization from: {theory_json_path.name}")
    with open(theory_json_path, 'r', encoding='utf-8') as f:
        theory_data = json.load(f)

    # Get process names
    processes = theory_data.get('processes', [])
    process_names = [p['process_name'] for p in processes]

    print(f"   Found {len(processes)} processes:")
    for name in process_names:
        print(f"      - {name}")

    # Manually add cluster_positions to simulate LLM output
    # Arrange in 2×3 grid (2 columns, 3 rows)
    # Position connected clusters near each other
    cluster_positions = {
        "Knowledge Socialization": [0, 0],       # Top-left
        "Knowledge Externalization": [0, 1],     # Top-right (adjacent to Socialization)
        "Knowledge Combination": [1, 0],         # Middle-left
        "Knowledge Internalization": [1, 1],     # Middle-right
        "Community Core Development": [2, 0]     # Bottom-left
    }

    # Note: In a real SECI model, these would be connected:
    # Socialization → Externalization → Combination → Internalization → (back to Socialization)
    # This 2-column layout keeps the flow readable with shorter arrows

    theory_data['cluster_positions'] = cluster_positions

    print(f"\n📐 Manual cluster layout (simulating LLM output):")
    print(f"   Grid: 2 columns × 3 rows")
    for name, pos in cluster_positions.items():
        row, col = pos
        print(f"      {name:40s} → Grid [{row}, {col}]")

    # Create MDL with cluster positioning
    print(f"\n🔨 Creating MDL with cluster-aware layout...")
    print(f"   Clusters positioned in 2D grid based on connections")
    print(f"   Each cluster: ~1500px wide, ~800px tall")
    print(f"   Variables within cluster: 5-column grid")

    result = create_mdl_from_scratch(
        theory_concretization=theory_data,
        output_path=output_mdl_path,
        llm_client=None,
        clustering_scheme=None,
        template_mdl_path=original_mdl_path
    )

    # Report results
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Success!")
        print(f"   Variables added: {result.get('variables_added', 0)}")
        print(f"   Connections added: {result.get('connections_added', 0)}")
        print(f"   Output: {output_mdl_path}")

        print(f"\n👀 Open in Vensim to verify cluster positioning:")
        print(f"   Expected layout (X, Y base positions):")
        print(f"   - Knowledge Socialization:    (~3000, ~100)   [Row 0, Col 0]")
        print(f"   - Knowledge Externalization:  (~4500, ~100)   [Row 0, Col 1]")
        print(f"   - Knowledge Combination:      (~3000, ~900)   [Row 1, Col 0]")
        print(f"   - Knowledge Internalization:  (~4500, ~900)   [Row 1, Col 1]")
        print(f"   - Community Core Development: (~3000, ~1700)  [Row 2, Col 0]")
        print(f"\n   Connected clusters should be spatially near each other!")


if __name__ == "__main__":
    test_cluster_positioning()

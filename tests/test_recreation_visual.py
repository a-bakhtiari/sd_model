#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visual Test for Recreation Mode Side-by-Side Layout

Creates test MDL file using existing theory_concretization_step2.json
to verify side-by-side layout (original left, theory right) WITHOUT expensive LLM positioning.

Output: tests/test_recreation_visual.mdl
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.mdl_creator import create_mdl_from_scratch


def test_recreation_side_by_side():
    """Generate test MDL with side-by-side layout using grid positioning."""

    # Paths
    project_dir = Path(__file__).parent.parent / "projects" / "sd_test"
    theory_json_path = project_dir / "artifacts" / "theory" / "theory_concretization_step2.json"
    original_mdl_path = project_dir / "mdl" / "test.mdl"
    output_mdl_path = Path(__file__).parent / "test_recreation_visual.mdl"

    # Verify files exist
    if not theory_json_path.exists():
        print(f"❌ Theory JSON not found: {theory_json_path}")
        return

    if not original_mdl_path.exists():
        print(f"❌ Original MDL not found: {original_mdl_path}")
        return

    # Load theory concretization
    print(f"📖 Loading theory concretization from: {theory_json_path}")
    with open(theory_json_path, 'r', encoding='utf-8') as f:
        theory_data = json.load(f)

    # Count processes and variables
    processes = theory_data.get('processes', [])
    total_vars = sum(len(p.get('variables', [])) for p in processes)
    total_conns = sum(len(p.get('connections', [])) for p in processes)

    print(f"   Found {len(processes)} processes, {total_vars} variables, {total_conns} connections")

    # Create side-by-side MDL
    print(f"\n🔨 Creating side-by-side MDL layout...")
    print(f"   Original model: LEFT side (X: 0-2000)")
    print(f"   Theory model:   RIGHT side (X: 3000+, grid layout by process cluster)")
    print(f"   NO LLM positioning (fast, cheap, simple grid)")

    result = create_mdl_from_scratch(
        theory_concretization=theory_data,
        output_path=output_mdl_path,
        llm_client=None,  # No LLM needed
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
        print(f"\n👀 Open in Vensim to visually verify side-by-side layout:")
        print(f"   - Original 9 variables should be on LEFT")
        print(f"   - Theory {total_vars} variables should be on RIGHT (grid by process)")
        print(f"   - No repositioning of original variables")


if __name__ == "__main__":
    test_recreation_side_by_side()

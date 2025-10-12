#!/usr/bin/env python3
"""Test MDL parser."""

import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.mdl_parser import MDLParser, parse_mdl_to_json


def test_mdl_parser():
    """Test MDL parser on sd_test model."""
    print("=" * 80)
    print("Testing MDL Parser")
    print("=" * 80)

    # Parse sd_test MDL
    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    output_dir = Path("tests/mdl_parser_output")

    print(f"\n1. Parsing: {mdl_path}")

    result = parse_mdl_to_json(mdl_path, output_dir)

    print(f"\n2. Extracted:")
    print(f"   - Variables: {len(result['variables'])}")
    print(f"   - Connections: {len(result['connections'])}")
    print(f"   - Valves: {len(result['valves'])}")
    print(f"   - Clouds: {len(result['clouds'])}")
    print(f"   - Equations: {len(result['equations'])}")

    print(f"\n3. Variables:")
    for var in result['variables']:
        color_str = f" [{var['color']['border']}]" if 'color' in var else ""
        print(f"   {var['id']:2d}. {var['name']:40s} {var['type']:10s} @ ({var['x']:4d},{var['y']:4d}){color_str}")

    print(f"\n4. Connections:")
    for conn in result['connections'][:10]:  # Show first 10
        sign = '+' if conn['relationship'] == 'positive' else '-' if conn['relationship'] == 'negative' else '?'
        print(f"   {conn['from_var']:30s} {sign}→ {conn['to_var']}")

    print(f"\n5. Saved JSON files to: {output_dir}/")
    print(f"   - variables.json")
    print(f"   - connections.json")
    if result['valves'] or result['clouds']:
        print(f"   - plumbing.json")

    # Validate extraction
    print(f"\n6. Validation:")
    expected_vars = [
        "New Contributors",
        "Core Developer",
        "Experienced Contributors",
        "Developer's Turnover",
        "Skill up",
        "Promotion Rate",
        "Implicit Knowledge Transfer (Mentorship)",
        "Explicit Knowledge Transfer (Documentation, Contributor's Guides)"
    ]

    extracted_names = [v['name'] for v in result['variables']]
    missing = set(expected_vars) - set(extracted_names)
    extra = set(extracted_names) - set(expected_vars)

    if missing:
        print(f"   ✗ Missing variables: {missing}")
    else:
        print(f"   ✓ All expected variables found")

    if extra:
        print(f"   ℹ Extra variables: {extra}")

    # Check positions extracted
    has_positions = all(
        v.get('x') is not None and v.get('y') is not None
        for v in result['variables']
    )
    print(f"   {'✓' if has_positions else '✗'} All variables have positions")

    # Check connections have relationships
    has_relationships = sum(
        1 for c in result['connections']
        if c['relationship'] in ['positive', 'negative']
    )
    print(f"   ✓ {has_relationships}/{len(result['connections'])} connections have identified relationships")

    print("\n" + "=" * 80)
    print("✅ MDL Parser test complete")
    print("=" * 80)


if __name__ == "__main__":
    test_mdl_parser()
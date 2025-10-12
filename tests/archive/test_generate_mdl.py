#!/usr/bin/env python3
"""Test MDL generator."""

import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.generate_mdl import generate_mdl


def test_generate_mdl():
    """Test MDL generator with parsed sd_test data."""
    print("=" * 80)
    print("Testing MDL Generator")
    print("=" * 80)

    # Use JSON files from parser test
    json_dir = Path("tests/mdl_parser_output")
    output_path = Path("tests/generated_test.mdl")

    print(f"\n1. Loading JSON files from: {json_dir}")

    # Load JSON files
    import json
    vars_json = json.loads((json_dir / "variables.json").read_text())
    conns_json = json.loads((json_dir / "connections.json").read_text())
    plumbing_json = json.loads((json_dir / "plumbing.json").read_text())

    print(f"   - Variables: {len(vars_json['variables'])}")
    print(f"   - Connections: {len(conns_json['connections'])}")
    print(f"   - Valves: {len(plumbing_json.get('valves', []))}")
    print(f"   - Clouds: {len(plumbing_json.get('clouds', []))}")

    print(f"\n2. Generating MDL...")

    # Generate MDL
    mdl_text = generate_mdl(
        vars_json,
        conns_json,
        plumbing_json,
        with_control=True,
        markers="std"
    )

    # Save
    output_path.write_text(mdl_text, encoding="utf-8")
    print(f"   ✓ Generated {len(mdl_text)} chars")
    print(f"   ✓ Saved to: {output_path}")

    # Validate structure
    print(f"\n3. Validation:")

    lines = mdl_text.split('\n')
    print(f"   - Total lines: {len(lines)}")

    # Check sections
    has_utf8 = "{UTF-8}" in mdl_text
    has_control = ".Control" in mdl_text
    has_sketch = "\\\\\\---///" in mdl_text or "--///" in mdl_text
    has_footer = "///---" in mdl_text

    print(f"   {'✓' if has_utf8 else '✗'} UTF-8 header")
    print(f"   {'✓' if has_control else '✗'} Control section")
    print(f"   {'✓' if has_sketch else '✗'} Sketch section")
    print(f"   {'✓' if has_footer else '✗'} Footer")

    # Count element types
    type10_count = sum(1 for line in lines if line.startswith("10,"))
    type11_count = sum(1 for line in lines if line.startswith("11,"))
    type12_count = sum(1 for line in lines if line.startswith("12,"))
    type1_count = sum(1 for line in lines if line.startswith("1,"))

    print(f"\n4. Sketch elements:")
    print(f"   - Type 10 (variables): {type10_count}")
    print(f"   - Type 11 (valves): {type11_count}")
    print(f"   - Type 12 (clouds): {type12_count}")
    print(f"   - Type 1 (connections): {type1_count}")

    print("\n" + "=" * 80)
    print("✅ MDL Generator test complete")
    print(f"Generated file: {output_path}")
    print("Next: Open in Vensim to verify structure")
    print("=" * 80)


if __name__ == "__main__":
    test_generate_mdl()
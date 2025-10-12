#!/usr/bin/env python3
"""Test color coding in MDL generation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.generate_mdl import generate_mdl


def test_color_coding():
    """Test MDL generator with colored elements."""
    print("=" * 80)
    print("Testing Color Coding in MDL")
    print("=" * 80)

    # Use JSON files with colored variables
    json_dir = Path("tests/mdl_parser_output")
    output_path = Path("tests/generated_with_colors.mdl")

    print(f"\n1. Loading JSON files from: {json_dir}")

    # Load JSON files
    vars_json = json.loads((json_dir / "variables_colored.json").read_text())
    conns_json = json.loads((json_dir / "connections.json").read_text())
    plumbing_json = json.loads((json_dir / "plumbing.json").read_text())

    print(f"\n2. Color assignments:")
    for var in vars_json['variables']:
        if 'color' in var:
            color = var['color']['border']
            # Interpret color
            if color == "0-255-0":
                color_name = "GREEN (new)"
            elif color == "255-255-0":
                color_name = "YELLOW (modified)"
            elif color == "255-0-0":
                color_name = "RED (to remove)"
            elif color == "0-0-255":
                color_name = "BLUE (custom)"
            else:
                color_name = color
            print(f"   - {var['name']:40s}: {color_name}")

    print(f"\n3. Generating MDL with colors...")

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

    # Check colored lines in sketch
    print(f"\n4. Verifying color codes in sketch:")
    lines = mdl_text.split('\n')
    colored_count = 0

    for line in lines:
        if line.startswith("10,") and ("0-255-0" in line or "255-255-0" in line or
                                        "255-0-0" in line or "0-0-255" in line):
            # Extract variable ID and color
            parts = line.split(',')
            if len(parts) > 17:
                var_id = parts[1]
                var_name = parts[2]
                # The color is in field 17 (index 16) for colored elements
                color = parts[16]
                print(f"   ID {var_id:2s}: {var_name:40s} -> {color}")
                colored_count += 1

    print(f"\n   Total colored elements: {colored_count}")

    # Also save to project folder
    project_output = Path("projects/sd_test/mdl/generated_with_colors.mdl")
    project_output.write_text(mdl_text, encoding="utf-8")
    print(f"\n5. Also saved to: {project_output}")

    print("\n" + "=" * 80)
    print("✅ Color coding test complete")
    print("Open the generated MDL in Vensim to see:")
    print("  - GREEN border: New Contributors (new addition)")
    print("  - YELLOW border: Core Developer (modified)")
    print("  - RED border: Developer's Turnover (to be removed)")
    print("  - BLUE border: Implicit Knowledge Transfer (custom)")
    print("=" * 80)


if __name__ == "__main__":
    test_color_coding()
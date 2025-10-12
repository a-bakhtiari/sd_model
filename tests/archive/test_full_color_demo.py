#!/usr/bin/env python3
"""Full color coding demonstration."""

import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.generate_mdl import generate_mdl


def test_full_color_demo():
    """Generate MDL with comprehensive color coding."""
    print("=" * 80)
    print("Full Color Coding Demonstration")
    print("=" * 80)

    json_dir = Path("tests/mdl_parser_output")
    output_path = Path("tests/generated_color_demo.mdl")

    # Load JSON files with colors
    vars_json = json.loads((json_dir / "variables_colored.json").read_text())
    conns_json = json.loads((json_dir / "connections_colored.json").read_text())
    plumbing_json = json.loads((json_dir / "plumbing.json").read_text())

    print("\n1. Color Scheme for Theory Enhancement:")
    print("   - GREEN (0-255-0)   = New additions")
    print("   - YELLOW (255-255-0) = Modified elements")
    print("   - RED (255-0-0)     = To be removed")
    print("   - BLUE (0-0-255)    = Custom/special")

    print("\n2. Colored Elements:")
    print("\n   Variables:")
    for var in vars_json['variables']:
        if 'color' in var:
            color = var['color']['border']
            print(f"     • {var['name']:40s}: {color}")

    print("\n   Connections:")
    for conn in conns_json['connections']:
        if 'color' in conn:
            color = conn['color']['line']
            print(f"     • {conn['from_var']} → {conn['to_var']}: {color}")

    print(f"\n3. Generating MDL...")
    mdl_text = generate_mdl(
        vars_json,
        conns_json,
        plumbing_json,
        with_control=True,
        markers="std"
    )

    output_path.write_text(mdl_text, encoding="utf-8")
    print(f"   ✓ Saved to: {output_path}")

    # Also save to project
    project_path = Path("projects/sd_test/mdl/generated_color_demo.mdl")
    project_path.write_text(mdl_text, encoding="utf-8")
    print(f"   ✓ Also saved to: {project_path}")

    # Extract and show the actual MDL lines with colors
    print("\n4. Generated MDL sketch lines with colors:")
    lines = mdl_text.split('\n')

    print("\n   Colored variables (Type 10):")
    for line in lines:
        if line.startswith("10,") and any(color in line for color in
            ["0-255-0", "255-255-0", "255-0-0", "0-0-255"]):
            parts = line.split(',')
            if len(parts) > 16:
                print(f"     {line[:100]}...")

    print("\n   Colored connections (Type 1):")
    for line in lines:
        if line.startswith("1,20,"):  # Our colored connection
            print(f"     {line[:80]}...")

    print("\n" + "=" * 80)
    print("✅ Color demonstration complete!")
    print("\nUsage in Theory Enhancement Workflow:")
    print("1. Parse existing MDL")
    print("2. Apply theory enhancement operations")
    print("3. Add appropriate colors to changed elements:")
    print("   - Green for new variables/connections")
    print("   - Yellow for modified elements")
    print("   - Red for deprecated elements")
    print("4. Generate new MDL with visual indicators")
    print("5. Review in Vensim with colored highlights")
    print("=" * 80)


if __name__ == "__main__":
    test_full_color_demo()
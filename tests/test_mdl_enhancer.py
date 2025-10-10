#!/usr/bin/env python3
"""Test MDL Enhancement Processor."""

import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.mdl_enhancer import apply_enhancements


def test_add_single_variable():
    """Test adding a single new variable to the model."""
    print("=" * 80)
    print("Test: Add Single Variable")
    print("=" * 80)

    # Input files
    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    output_path = Path("tests/test_enhanced_single_var.mdl")

    # Create minimal enhancement JSON
    enhancement_json = {
        "missing_from_theories": [
            {
                "theory_name": "Test Theory",
                "missing_element": "Test Element",
                "sd_implementation": {
                    "new_variables": [
                        {
                            "name": "Test Variable",
                            "type": "Stock",
                            "description": "A test stock variable"
                        }
                    ],
                    "new_connections": []
                }
            }
        ]
    }

    # Save temporary enhancement JSON
    enhancement_path = Path("tests/temp_enhancement.json")
    with open(enhancement_path, 'w') as f:
        json.dump(enhancement_json, f, indent=2)

    print("\n1. Applying enhancement...")
    summary = apply_enhancements(
        mdl_path,
        enhancement_path,
        output_path,
        add_colors=True
    )

    print(f"\n2. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")

    print(f"\n3. Generated file: {output_path}")
    print(f"   Size: {output_path.stat().st_size} bytes")

    # Check that the variable is in the output
    with open(output_path) as f:
        content = f.read()
        if "Test Variable" in content:
            print("   ✅ Variable 'Test Variable' found in MDL")
        else:
            print("   ❌ Variable 'Test Variable' NOT found in MDL")

        if "0-255-0" in content:  # Green color
            print("   ✅ Green color coding applied")
        else:
            print("   ⚠️  Color coding not found")

    # Clean up
    enhancement_path.unlink()

    print("\n" + "=" * 80)
    print("✅ Test complete! Check the file in Vensim:")
    print(f"   {output_path}")
    print("=" * 80)


def test_add_variable_with_connection():
    """Test adding a variable with a connection to existing variable."""
    print("\n" + "=" * 80)
    print("Test: Add Variable with Connection")
    print("=" * 80)

    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    output_path = Path("tests/test_enhanced_with_connection.mdl")

    # Enhancement with variable + connection
    enhancement_json = {
        "missing_from_theories": [
            {
                "theory_name": "Test Theory",
                "sd_implementation": {
                    "new_variables": [
                        {
                            "name": "Community Engagement",
                            "type": "Auxiliary",
                            "description": "Measures community participation level"
                        }
                    ],
                    "new_connections": [
                        {
                            "from": "Core Developer",
                            "to": "Community Engagement",
                            "relationship": "positive",
                            "rationale": "More core developers increases engagement"
                        }
                    ]
                }
            }
        ]
    }

    enhancement_path = Path("tests/temp_enhancement2.json")
    with open(enhancement_path, 'w') as f:
        json.dump(enhancement_json, f, indent=2)

    print("\n1. Applying enhancement...")
    summary = apply_enhancements(
        mdl_path,
        enhancement_path,
        output_path,
        add_colors=True
    )

    print(f"\n2. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")

    print(f"\n3. Generated: {output_path}")

    # Verify content
    with open(output_path) as f:
        content = f.read()
        if "Community Engagement" in content:
            print("   ✅ Variable 'Community Engagement' found")

        # Check if connection exists in equations
        if "Core Developer" in content and "Community Engagement" in content:
            print("   ✅ Both variables present for connection")

    enhancement_path.unlink()

    print("\n" + "=" * 80)
    print("✅ Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_add_single_variable()
    test_add_variable_with_connection()

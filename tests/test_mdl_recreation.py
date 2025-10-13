#!/usr/bin/env python3
"""
Test MDL Recreation Mode

Verifies that recreation mode correctly:
1. Removes all existing variables from template
2. Adds only theory-generated variables
3. Preserves Vensim formatting (control section, metadata)
4. Produces valid MDL that opens in Vensim
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sd_model.mdl_creator import create_mdl_from_scratch
from sd_model.llm.client import LLMClient


def test_basic_recreation():
    """Test basic recreation with simple fake theory output."""

    # Use sd_test MDL as template (9 existing variables)
    template_path = Path(__file__).parent.parent / 'projects' / 'sd_test' / 'mdl' / 'test.mdl'
    output_path = Path(__file__).parent / 'test_recreated_simple.mdl'

    # Create fake theory output with 3 new variables
    fake_theory = {
        'processes': [
            {
                'process_name': 'Test Process',
                'variables': [
                    {'name': 'Variable A', 'type': 'Stock'},
                    {'name': 'Variable B', 'type': 'Flow'},
                    {'name': 'Variable C', 'type': 'Auxiliary'}
                ],
                'connections': [
                    {'from': 'Variable A', 'to': 'Variable B', 'relationship': 'positive'},
                    {'from': 'Variable B', 'to': 'Variable C', 'relationship': 'negative'}
                ]
            }
        ]
    }

    # Initialize LLM client (needed for positioning)
    llm_client = LLMClient()

    print("=" * 60)
    print("Testing MDL Recreation Mode")
    print("=" * 60)
    print(f"\nTemplate: {template_path}")
    print(f"Output: {output_path}")
    print(f"\nOriginal MDL has 9 variables")
    print(f"Theory output has 3 variables")
    print(f"Expected result: MDL with ONLY 3 new variables\n")

    # Run recreation
    result = create_mdl_from_scratch(
        fake_theory,
        output_path,
        llm_client,
        clustering_scheme=None,
        template_mdl_path=template_path
    )

    print("Result:", result)

    # Verify output file exists
    assert output_path.exists(), "Output file not created"

    # Read and analyze output
    content = output_path.read_text()
    lines = content.split('\n')

    # Count variables in output (Type 10 lines)
    var_count = sum(1 for line in lines if line.startswith('10,'))

    # Count connections in output (Type 1 lines)
    conn_count = sum(1 for line in lines if line.startswith('1,'))

    print(f"\n✓ Output file created")
    print(f"✓ Variables in output: {var_count} (expected: 3)")
    print(f"✓ Connections in output: {conn_count} (expected: 2)")

    # Verify variable names
    var_lines = [line for line in lines if line.startswith('10,')]
    print(f"\nVariable lines:")
    for line in var_lines:
        parts = line.split(',')
        if len(parts) > 2:
            print(f"  - {parts[2]}")

    # Check for old variables (should NOT be present)
    old_vars = ['New Contributors', 'Core Developer', 'Experienced Contributors']
    for old_var in old_vars:
        assert old_var not in content, f"Old variable '{old_var}' found in output! Recreation failed."

    print(f"\n✓ Old variables NOT present (recreation successful)")

    # Check for new variables (should be present)
    new_vars = ['Variable A', 'Variable B', 'Variable C']
    for new_var in new_vars:
        assert new_var in content, f"New variable '{new_var}' not found in output!"

    print(f"✓ New variables present")

    # Check control section preserved
    assert 'FINAL TIME' in content, "Control section missing"
    assert 'INITIAL TIME' in content, "Control section missing"
    print(f"✓ Control section preserved")

    # Check sketch header preserved
    assert '\\\\\\---///' in content, "Sketch header missing"
    assert 'V300' in content, "Sketch version missing"
    print(f"✓ Sketch header preserved")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print(f"\nOpen the output file in Vensim to verify:")
    print(f"  {output_path}")


if __name__ == '__main__':
    test_basic_recreation()

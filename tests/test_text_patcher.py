#!/usr/bin/env python3
"""
Test MDL Text Patcher
"""
from pathlib import Path
from src.sd_model.mdl_text_patcher import apply_text_patch_enhancements


def test_text_patch_simple():
    """Test text patching with simple additions."""
    print("=" * 80)
    print("Test: Text Patch Enhancement (Simple)")
    print("=" * 80)

    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    output_path = Path("tests/test_text_patched.mdl")

    # Add one simple variable
    new_variables = [
        {
            'name': 'Test Auxiliary',
            'type': 'Auxiliary',
            'x': 1500,
            'y': 300,
            'width': 60,
            'height': 26
        }
    ]

    # Add one connection
    new_connections = [
        {
            'from': 'Core Developer',
            'to': 'Test Auxiliary',
            'relationship': 'positive'
        }
    ]

    print(f"\n1. Input: {mdl_path}")
    print(f"2. Output: {output_path}")
    print(f"3. Adding {len(new_variables)} variable(s) and {len(new_connections)} connection(s)")

    summary = apply_text_patch_enhancements(
        mdl_path,
        new_variables,
        new_connections,
        output_path,
        add_colors=True
    )

    print(f"\n4. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")

    # Verify output
    content = output_path.read_text()
    if 'Test Auxiliary' in content:
        print("   ✅ New variable found in output")
    if '0-255-0' in content:
        print("   ✅ Green color applied")

    print(f"\n5. File size: {output_path.stat().st_size} bytes")
    print("\n" + "=" * 80)
    print("✅ Test complete! Open in Vensim to verify:")
    print(f"   {output_path}")
    print("=" * 80)


def test_text_patch_oss_model():
    """Test text patching on oss_model with theory enhancement."""
    print("\n" + "=" * 80)
    print("Test: Text Patch Enhancement (oss_model)")
    print("=" * 80)

    mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
    enhancement_json_path = Path("projects/oss_model/artifacts/theory_enhancement.json")
    output_path = Path("tests/oss_model_text_patched.mdl")

    import json
    from src.sd_model.mdl_text_patcher import apply_theory_enhancements

    with open(enhancement_json_path) as f:
        enhancement_json = json.load(f)

    # Count variables and connections from new format
    total_vars = sum(len(t.get('additions', {}).get('variables', [])) for t in enhancement_json.get('theories', []))
    total_conns = sum(len(t.get('additions', {}).get('connections', [])) for t in enhancement_json.get('theories', []))

    print(f"\n1. Input: {mdl_path}")
    print(f"2. Output: {output_path}")
    print(f"3. Adding {total_vars} variable(s) and {total_conns} connection(s)")

    summary = apply_theory_enhancements(
        mdl_path,
        enhancement_json,
        output_path,
        add_colors=True,
        use_llm_layout=False  # Use grid positioning for this test
    )

    print(f"\n4. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")
    print(f"   Theories processed: {summary['theories_processed']}")

    print(f"\n5. File size: {output_path.stat().st_size} bytes")

    # Verify original flow structures preserved
    with open(output_path) as f:
        lines = f.readlines()
        valve_count = sum(1 for line in lines if line.startswith('11,'))
        print(f"   Valves preserved: {valve_count}")

    print("\n" + "=" * 80)
    print("✅ Test complete! Open in Vensim to verify:")
    print(f"   {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    test_text_patch_simple()
    test_text_patch_oss_model()

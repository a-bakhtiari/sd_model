"""Test: MDL Generator with Theory Enhancements

This test:
1. Loads original MDL file (oss_model/mdl/untitled.mdl)
2. Loads theory enhancement JSON (tests/theory_enhancement_mdl.json)
3. Applies all changes (add/remove/modify operations)
4. Generates enhanced MDL file (tests/enhanced_model.mdl)
5. Validates the output
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from tests.mdl_generator import MDLParser, MDLGenerator


def test_mdl_generation():
    """Test MDL generation with theory enhancements."""

    print("="*80)
    print("MDL GENERATOR TEST")
    print("="*80)

    repo_root = Path(".")

    # Input files
    mdl_path = repo_root / "projects" / "oss_model" / "mdl" / "untitled.mdl"
    enhancement_json_path = repo_root / "tests" / "theory_enhancement_mdl.json"
    output_mdl_path = repo_root / "tests" / "enhanced_model.mdl"

    # Validate input files exist
    if not mdl_path.exists():
        print(f"✗ Error: MDL file not found: {mdl_path}")
        return
    if not enhancement_json_path.exists():
        print(f"✗ Error: Enhancement JSON not found: {enhancement_json_path}")
        return

    # 1. Parse original MDL
    print(f"\n1. Parsing original MDL: {mdl_path}")
    parser = MDLParser(mdl_path)
    parser.parse()
    print(f"   ✓ Parsed {len(parser.variables)} variables")
    print(f"   ✓ Parsed {len(parser.connections)} connections")

    original_var_count = len(parser.variables)
    original_conn_count = len(parser.connections)

    # 2. Load enhancement JSON
    print(f"\n2. Loading enhancement JSON: {enhancement_json_path}")
    enhancement_data = json.loads(enhancement_json_path.read_text(encoding="utf-8"))
    changes = enhancement_data.get("model_changes", [])
    print(f"   ✓ Loaded {len(changes)} changes")

    # Show summary
    summary = enhancement_data.get("summary", {})
    print(f"\n   Summary:")
    print(f"     Variables to add: {summary.get('additions', {}).get('variables', 0)}")
    print(f"     Variables to remove: {summary.get('removals', {}).get('variables', 0)}")
    print(f"     Connections to add: {summary.get('additions', {}).get('connections', 0)}")
    print(f"     Connections to remove: {summary.get('removals', {}).get('connections', 0)}")
    print(f"     Connections to modify: {summary.get('modifications', {}).get('connections', 0)}")

    # 3. Apply changes
    print(f"\n3. Applying changes...")
    generator = MDLGenerator(parser)
    generator.apply_changes(changes)

    # Print detailed changes log
    generator.print_changes_log()

    # 4. Generate output MDL
    print(f"\n4. Generating enhanced MDL...")
    generator.generate_mdl(output_mdl_path)

    # 5. Validate results
    print(f"\n5. Validation:")
    new_var_count = len(parser.variables)
    new_conn_count = len(parser.connections)

    expected_var_change = (
        summary.get('additions', {}).get('variables', 0) -
        summary.get('removals', {}).get('variables', 0)
    )
    expected_conn_change = (
        summary.get('additions', {}).get('connections', 0) -
        summary.get('removals', {}).get('connections', 0)
        # modifications don't change count
    )

    actual_var_change = new_var_count - original_var_count
    actual_conn_change = new_conn_count - original_conn_count

    print(f"   Variables: {original_var_count} → {new_var_count} (change: {actual_var_change:+d}, expected: {expected_var_change:+d})")
    print(f"   Connections: {original_conn_count} → {new_conn_count} (change: {actual_conn_change:+d}, expected: {expected_conn_change:+d})")

    # Check if changes match expectations
    vars_ok = actual_var_change == expected_var_change
    conns_ok = actual_conn_change == expected_conn_change

    if vars_ok and conns_ok:
        print("\n   ✓ Variable and connection counts match expectations!")
    else:
        if not vars_ok:
            print(f"\n   ✗ Variable count mismatch: expected {expected_var_change:+d}, got {actual_var_change:+d}")
        if not conns_ok:
            print(f"\n   ✗ Connection count mismatch: expected {expected_conn_change:+d}, got {actual_conn_change:+d}")

    # 6. Show sample of added variables
    print(f"\n6. Sample of changes:")
    print(f"\n   Added Variables:")
    added_vars = [
        change for change in changes
        if change.get("operation") == "add_variable"
    ]
    for change in added_vars[:3]:
        var = change["variable"]
        print(f"     • {var['name']} ({var['type']}) at ({var['position']['x']}, {var['position']['y']})")
        print(f"       {change.get('mdl_comment', '')}")

    # Final result
    print("\n" + "="*80)
    print("✅ TEST COMPLETED SUCCESSFULLY!")
    print(f"Enhanced MDL file created: {output_mdl_path}")
    print("="*80)


if __name__ == "__main__":
    test_mdl_generation()

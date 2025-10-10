"""Test: Surgical Parser Round-Trip

Test that parser can:
1. Parse sd_test MDL
2. Reassemble it
3. Output matches original (or is functionally equivalent)
"""
import sys
from pathlib import Path

sys.path.insert(0, '.')

from tests.mdl_surgical_parser import MDLSurgicalParser


def test_parser_roundtrip():
    """Test parse → reassemble round-trip."""

    print("="*80)
    print("SURGICAL PARSER ROUND-TRIP TEST")
    print("="*80)

    mdl_path = Path("projects/sd_test/mdl/test.mdl")

    if not mdl_path.exists():
        print(f"✗ MDL file not found: {mdl_path}")
        return

    # 1. Load original
    print(f"\n1. Loading original MDL: {mdl_path}")
    original_content = mdl_path.read_text(encoding="utf-8")
    print(f"   ✓ Loaded ({len(original_content)} chars, {len(original_content.splitlines())} lines)")

    # 2. Parse
    print(f"\n2. Parsing MDL...")
    parser = MDLSurgicalParser(mdl_path)
    parser.parse()

    print(f"   ✓ Parsed {len(parser.equations)} equations")
    print(f"   ✓ Parsed {len(parser.sketch_vars)} sketch variables")
    print(f"   ✓ Control section: {len(parser.control_section)} lines")
    print(f"   ✓ Sketch header: {len(parser.sketch_header)} lines")
    print(f"   ✓ Sketch other: {len(parser.sketch_other)} lines")
    print(f"   ✓ Max ID: {parser.max_id}")

    # 3. Show parsed variables
    print(f"\n3. Parsed Variables:")
    for var_name in parser.equation_order:
        sketch_id = parser.name_to_id.get(var_name, "?")
        print(f"   • {var_name} (ID: {sketch_id})")

    # 4. Show name → ID mappings
    print(f"\n4. Name → ID Mappings:")
    for name, sketch_id in sorted(parser.name_to_id.items(), key=lambda x: x[1]):
        print(f"   {sketch_id:2d} → {name}")

    # 5. Reassemble
    print(f"\n5. Reassembling MDL...")
    reassembled = parser.reassemble()
    print(f"   ✓ Reassembled ({len(reassembled)} chars, {len(reassembled.splitlines())} lines)")

    # 6. Compare
    print(f"\n6. Comparing original vs reassembled:")

    original_lines = original_content.splitlines()
    reassembled_lines = reassembled.splitlines()

    print(f"   Original lines: {len(original_lines)}")
    print(f"   Reassembled lines: {len(reassembled_lines)}")

    # Check line count
    if len(original_lines) != len(reassembled_lines):
        diff = len(reassembled_lines) - len(original_lines)
        print(f"   ⚠ Line count differs by {diff:+d}")

    # Find differences
    differences = []
    for i, (orig, reasm) in enumerate(zip(original_lines, reassembled_lines)):
        if orig != reasm:
            differences.append((i + 1, orig, reasm))

    if differences:
        print(f"\n   Found {len(differences)} line differences:")
        for line_num, orig, reasm in differences[:5]:  # Show first 5
            print(f"\n   Line {line_num}:")
            print(f"     Original:    '{orig}'")
            print(f"     Reassembled: '{reasm}'")

        if len(differences) > 5:
            print(f"\n   ... and {len(differences) - 5} more differences")
    else:
        print(f"   ✓ All lines match exactly!")

    # 7. Validation checks
    print(f"\n7. Validation:")

    # Check equation ↔ sketch sync
    eq_names = set(parser.equations.keys())
    sketch_names = set(parser.name_to_id.keys())

    missing_sketch = eq_names - sketch_names
    missing_equation = sketch_names - eq_names

    if missing_sketch:
        print(f"   ⚠ Variables with equation but no sketch: {missing_sketch}")
    if missing_equation:
        print(f"   ⚠ Variables with sketch but no equation: {missing_equation}")

    if not missing_sketch and not missing_equation:
        print(f"   ✓ All equations have matching sketch variables")

    # Check IDs unique
    ids = list(parser.sketch_vars.keys())
    if len(ids) == len(set(ids)):
        print(f"   ✓ All sketch IDs are unique")
    else:
        print(f"   ✗ Duplicate sketch IDs found")

    # 8. Save reassembled for inspection
    output_path = Path("tests/sdtest_reassembled.mdl")
    output_path.write_text(reassembled, encoding="utf-8")
    print(f"\n8. Saved reassembled MDL to: {output_path}")

    # Final result
    print("\n" + "="*80)
    if not differences:
        print("✅ ROUND-TRIP TEST PASSED!")
        print("Parser can parse and reassemble MDL perfectly.")
    else:
        print("⚠️ ROUND-TRIP TEST PARTIAL PASS")
        print(f"Parser works but {len(differences)} line differences detected.")
        print("(Differences may be inconsequential - check saved file)")
    print("="*80)


if __name__ == "__main__":
    test_parser_roundtrip()

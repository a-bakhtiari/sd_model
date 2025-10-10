"""Test: Hybrid LLM-Based ADD_VARIABLE

Test adding a single variable using LLM surgical approach.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from tests.mdl_surgical_parser import MDLSurgicalParser
from tests.mdl_surgical_llm_generator import (
    load_mdl_rules,
    llm_add_variable
)
from tests.mdl_focused_fixers import (
    extract_sections,
    fix_sketch_section,
    reassemble_mdl
)
from src.sd_model.llm.client import LLMClient


def test_hybrid_add_variable():
    """Test adding a variable with hybrid LLM approach."""

    print("="*80)
    print("HYBRID ADD_VARIABLE TEST (sd_test)")
    print("="*80)

    # 1. Load original MDL
    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    print(f"\n1. Loading original MDL: {mdl_path}")

    original_mdl = mdl_path.read_text(encoding="utf-8")
    print(f"   ✓ Loaded ({len(original_mdl)} chars)")

    # 2. Parse to get context
    print(f"\n2. Parsing for context...")
    parser = MDLSurgicalParser(mdl_path)
    parser.parse()

    print(f"   ✓ Found {len(parser.equations)} equations")
    print(f"   ✓ Max sketch ID: {parser.max_id}")

    # 3. Load MDL rules
    print(f"\n3. Loading MDL rules...")
    mdl_rules = load_mdl_rules()
    print(f"   ✓ Loaded rules ({len(mdl_rules)} chars)")

    # 4. Define new variable
    print(f"\n4. Defining new variable...")
    new_var = {
        "name": "Knowledge Sharing Rate",
        "type": "Auxiliary",
        "description": "Rate of knowledge exchange among developers",
        "units": "knowledge/time",
        "position": {"x": 1400, "y": 300},
        "size": {"width": 60, "height": 26},
        "color": {"border": "0-255-0"}
    }
    print(f"   Variable: {new_var['name']} ({new_var['type']})")
    print(f"   Position: ({new_var['position']['x']}, {new_var['position']['y']})")

    # 5. Generate with LLM
    print(f"\n5. Generating code with LLM (DeepSeek)...")
    llm_client = LLMClient(provider="deepseek")

    result = llm_add_variable(
        var_spec=new_var,
        max_id=parser.max_id,
        mdl_rules=mdl_rules,
        llm_client=llm_client
    )

    print(f"   ✓ Generated equation block:")
    print(f"      {result['equation_block'][:80]}...")
    print(f"   ✓ Generated {len(result['sketch_lines'])} sketch lines")

    # 6. Insert into MDL
    print(f"\n6. Inserting into MDL...")

    # Find insertion points
    lines = original_mdl.split("\n")

    # Find last equation block (before control section)
    equation_insert_idx = -1
    for i, line in enumerate(lines):
        if "***" in line:
            equation_insert_idx = i
            break

    # Find sketch variable insertion point (AFTER $ style line)
    sketch_var_insert_idx = -1
    in_sketch = False
    for i, line in enumerate(lines):
        if "\\\\\\---///" in line:
            in_sketch = True
        elif in_sketch and line.startswith("$"):
            sketch_var_insert_idx = i + 1  # Insert AFTER $ line
            break

    if sketch_var_insert_idx == -1:
        raise ValueError("Could not find $ style line in sketch section")

    # Insert equation
    equation_lines = result['equation_block'].split("\n")
    num_eq_lines = len(equation_lines) + 1  # +1 for blank line
    for j, eq_line in enumerate(reversed(equation_lines)):
        lines.insert(equation_insert_idx, eq_line)

    # Add blank line after equation
    lines.insert(equation_insert_idx, "")

    # Adjust sketch insertion index (lines were inserted before it)
    if sketch_var_insert_idx > equation_insert_idx:
        sketch_var_insert_idx += num_eq_lines

    # Insert sketch lines
    for sketch_line in reversed(result['sketch_lines']):
        lines.insert(sketch_var_insert_idx, sketch_line)

    modified_mdl = "\n".join(lines)
    print(f"   ✓ Inserted equation at line {equation_insert_idx}")
    print(f"   ✓ Inserted sketch lines at line {sketch_var_insert_idx} (after $ style line)")

    # 7. Fix with focused LLM call (using original as template)
    print(f"\n7. Final validation with focused LLM fixer...")

    # Extract sections
    orig_equations, orig_sketch, orig_footer = extract_sections(original_mdl)
    mod_equations, mod_sketch, mod_footer = extract_sections(modified_mdl)

    # Fix sketch section (most likely to have issues)
    print(f"   Fixing sketch section...")
    fixed_sketch = fix_sketch_section(orig_sketch, mod_sketch, llm_client)

    # Reassemble
    final_mdl = reassemble_mdl(mod_equations, fixed_sketch, mod_footer)
    print(f"   ✓ Sketch section fixed and reassembled")

    # 8. Save result
    output_path = Path("tests/sdtest_hybrid_added_variable.mdl")
    output_path.write_text(final_mdl, encoding="utf-8")
    print(f"\n8. Saved to: {output_path}")

    # 9. Validation
    print(f"\n9. Validation:")

    final_lines = final_mdl.split("\n")
    original_lines = original_mdl.split("\n")

    print(f"   Original: {len(original_lines)} lines")
    print(f"   Modified: {len(final_lines)} lines")
    print(f"   Difference: {len(final_lines) - len(original_lines):+d} lines")

    # Check for new variable
    var_in_equations = new_var['name'] in final_mdl.split("\\\\\\---///")[0]
    var_in_sketch = new_var['name'] in final_mdl.split("\\\\\\---///")[1]

    print(f"\n   Variable '{new_var['name']}':")
    print(f"     In equations: {'✓' if var_in_equations else '✗'}")
    print(f"     In sketch: {'✓' if var_in_sketch else '✗'}")

    print("\n" + "="*80)
    print("✅ TEST COMPLETED!")
    print(f"Result saved to: {output_path}")
    print("Next: Open in Vensim to verify visual structure")
    print("="*80)


if __name__ == "__main__":
    test_hybrid_add_variable()

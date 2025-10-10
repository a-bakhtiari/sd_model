#!/usr/bin/env python3
"""
Test new theory enhancement format with sd_test project
"""
from pathlib import Path
import json
from src.sd_model.pipeline.theory_enhancement import run_theory_enhancement
from src.sd_model.mdl_text_patcher import apply_theory_enhancements
from src.sd_model.llm.client import LLMClient
from src.sd_model.knowledge.loader import load_theories
from src.sd_model.paths import for_project
from src.sd_model.config import load_config


def test_new_format_generation():
    """Test that new format is generated correctly."""
    print("=" * 80)
    print("Test: Generate New Theory Enhancement Format (sd_test)")
    print("=" * 80)

    # Setup paths
    cfg = load_config()
    paths = for_project(cfg, "sd_test")

    # Load theories
    theories_objs = load_theories(paths.theories_dir)
    theories = [{"name": t.theory_name, "description": t.description} for t in theories_objs]
    print(f"\n1. Loaded {len(theories)} theories")

    # Mock variables, connections, loops for testing
    variables = {
        "variables": [
            {"name": "Core Developer", "type": "Stock"},
            {"name": "New Contributors", "type": "Stock"},
            {"name": "Knowledge Base", "type": "Stock"}
        ]
    }

    connections = {
        "connections": [
            {"from_var": "Core Developer", "to_var": "Knowledge Base", "relationship": "positive"},
            {"from_var": "Knowledge Base", "to_var": "New Contributors", "relationship": "positive"}
        ]
    }

    loops = {
        "reinforcing": [],
        "balancing": [],
        "undetermined": []
    }

    # Generate enhancement
    print("\n2. Calling LLM to generate theory enhancement...")
    llm_client = LLMClient(provider="deepseek")

    enhancement = run_theory_enhancement(
        theories=theories,
        variables=variables,
        connections=connections,
        loops=loops
    )

    # Save to file
    output_path = paths.artifacts_dir / "theory_enhancement_new_format.json"
    output_path.write_text(json.dumps(enhancement, indent=2), encoding='utf-8')

    print(f"\n3. Generated: {output_path}")

    # Validate format
    if "theories" in enhancement:
        print(f"   ✅ New format detected: {len(enhancement['theories'])} theories")

        for theory in enhancement['theories']:
            print(f"\n   Theory: {theory['name']}")
            additions = theory.get('additions', {})
            print(f"     - Variables to add: {len(additions.get('variables', []))}")
            print(f"     - Connections to add: {len(additions.get('connections', []))}")

    elif "missing_from_theories" in enhancement:
        print("   ⚠️  Old format detected - prompt may need adjustment")
    else:
        print("   ❌ Unexpected format")

    print("\n" + "=" * 80)
    return enhancement


def test_apply_new_format():
    """Test applying new format to MDL."""
    print("\n" + "=" * 80)
    print("Test: Apply New Format to MDL (sd_test)")
    print("=" * 80)

    mdl_path = Path("projects/sd_test/mdl/test.mdl")
    enhancement_json_path = Path("projects/sd_test/artifacts/theory_enhancement_new_format.json")
    output_path = Path("tests/sd_test_new_format.mdl")

    if not enhancement_json_path.exists():
        print(f"❌ Enhancement file not found: {enhancement_json_path}")
        print("   Run test_new_format_generation() first")
        return

    # Load enhancement
    with open(enhancement_json_path) as f:
        enhancement_json = json.load(f)

    # Count additions
    total_vars = sum(len(t.get('additions', {}).get('variables', [])) for t in enhancement_json.get('theories', []))
    total_conns = sum(len(t.get('additions', {}).get('connections', [])) for t in enhancement_json.get('theories', []))

    print(f"\n1. Input: {mdl_path}")
    print(f"2. Enhancement: {enhancement_json_path}")
    print(f"3. Output: {output_path}")
    print(f"4. Variables to add: {total_vars}")
    print(f"5. Connections to add: {total_conns}")

    # Apply with LLM layout
    try:
        llm_client = LLMClient(provider="deepseek")
        print("\n6. Using LLM for intelligent positioning...")
    except RuntimeError as e:
        print(f"\n6. LLM not available: {e}")
        llm_client = None

    summary = apply_theory_enhancements(
        mdl_path,
        enhancement_json,
        output_path,
        add_colors=True,
        use_llm_layout=True,
        llm_client=llm_client
    )

    print(f"\n7. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")
    print(f"   Theories processed: {summary['theories_processed']}")

    print(f"\n8. File size: {output_path.stat().st_size} bytes")

    # Verify content
    content = output_path.read_text()
    valve_count = content.count('\n11,')
    print(f"   Valves preserved: {valve_count}")

    if '0-255-0' in content:
        print("   ✅ Green color applied to new variables")

    print("\n" + "=" * 80)
    print("✅ Test complete! Open in Vensim to verify:")
    print(f"   {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    # Run both tests
    enhancement = test_new_format_generation()

    if enhancement and "theories" in enhancement:
        test_apply_new_format()
    else:
        print("\n⚠️  Skipping application test due to format issue")

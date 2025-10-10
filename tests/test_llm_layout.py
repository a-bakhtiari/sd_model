#!/usr/bin/env python3
"""
Test LLM-based layout optimization
"""
from pathlib import Path
import json
from src.sd_model.mdl_text_patcher import apply_theory_enhancements
from src.sd_model.llm.client import LLMClient


def test_llm_layout_oss_model():
    """Test LLM layout on oss_model."""
    print("=" * 80)
    print("Test: LLM-Optimized Layout for oss_model")
    print("=" * 80)

    mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
    enhancement_json_path = Path("projects/oss_model/artifacts/theory_enhancement.json")
    output_path = Path("tests/oss_model_llm_layout.mdl")

    # Load enhancement JSON
    with open(enhancement_json_path) as f:
        enhancement_json = json.load(f)

    # Count variables and connections from new format
    total_vars = sum(len(t.get('additions', {}).get('variables', [])) for t in enhancement_json.get('theories', []))
    total_conns = sum(len(t.get('additions', {}).get('connections', [])) for t in enhancement_json.get('theories', []))

    print(f"\n1. Input: {mdl_path}")
    print(f"2. Output: {output_path}")
    print(f"3. Variables to position: {total_vars}")
    print(f"4. Connections: {total_conns}")

    # Try to create LLM client
    try:
        llm_client = LLMClient(provider="deepseek")
        print(f"5. Using LLM for intelligent positioning...")
    except RuntimeError as e:
        print(f"5. LLM not available: {e}")
        print("   Will use fallback grid positioning")
        llm_client = None

    # Apply enhancements with LLM layout
    summary = apply_theory_enhancements(
        mdl_path,
        enhancement_json,
        output_path,
        add_colors=True,
        use_llm_layout=True,
        llm_client=llm_client
    )

    print(f"\n6. Summary:")
    print(f"   Variables added: {summary['variables_added']}")
    print(f"   Connections added: {summary['connections_added']}")
    print(f"   Theories processed: {summary['theories_processed']}")

    print(f"\n7. File size: {output_path.stat().st_size} bytes")

    # Verify original preserved
    content = output_path.read_text()
    valve_count = content.count('\n11,')
    print(f"   Valves preserved: {valve_count}")

    print("\n" + "=" * 80)
    print("✅ Test complete! Open in Vensim to verify layout:")
    print(f"   {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    test_llm_layout_oss_model()

"""
Test archetype MDL generation directly in tests folder.
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.mdl_text_patcher import apply_theory_enhancements
from src.sd_model.pipeline.archetype_detection import detect_archetypes
from src.sd_model.llm.client import LLMClient
from src.sd_model.parsers import extract_variables, extract_connections


def test_archetype_mdl_generation():
    """Test creating archetype-enhanced MDL file in tests folder."""

    print("\n" + "="*60)
    print("Testing Archetype MDL Generation")
    print("="*60 + "\n")

    # Paths
    tests_dir = Path(__file__).parent
    mdl_path = Path("/Users/alibakhtiari/Desktop/Thesis/SD_model/projects/sd_test/mdl/test.mdl")
    output_mdl = tests_dir / "test_archetype_enhanced.mdl"
    output_json = tests_dir / "test_archetype_enhancement.json"

    if not mdl_path.exists():
        print(f"❌ MDL file not found: {mdl_path}")
        return

    print(f"📄 Input MDL: {mdl_path}")
    print(f"📄 Output MDL: {output_mdl}")
    print(f"📄 Output JSON: {output_json}\n")

    # Step 1: Extract variables and connections
    print("Step 1: Extracting variables and connections...")
    variables = extract_variables(mdl_path)
    connections = extract_connections(mdl_path, variables)
    print(f"✓ Found {len(variables.get('variables', []))} variables")
    print(f"✓ Found {len(connections.get('connections', []))} connections\n")

    # Step 2: Run archetype detection
    print("Step 2: Running archetype detection...")
    client = LLMClient(provider="deepseek")
    archetype_result = detect_archetypes(variables, connections, client)

    if "error" in archetype_result:
        print(f"❌ Archetype detection failed: {archetype_result['error']}")
        return

    archetypes = archetype_result.get('archetypes', [])
    print(f"✓ Detected {len(archetypes)} archetypes\n")

    for i, arch in enumerate(archetypes, 1):
        name = arch.get('name', 'Unknown')
        vars_count = len(arch.get('additions', {}).get('variables', []))
        conns_count = len(arch.get('additions', {}).get('connections', []))
        print(f"  {i}. {name}")
        print(f"     → {vars_count} variables, {conns_count} connections")

    # Save archetype JSON
    output_json.write_text(json.dumps(archetype_result, indent=2), encoding="utf-8")
    print(f"\n✓ Saved archetype data to: {output_json}\n")

    # Step 3: Generate enhanced MDL
    print("Step 3: Generating archetype-enhanced MDL...")

    # Format archetype data for MDL patcher (same format as theory enhancement)
    patcher_input = {
        "theories": archetype_result.get('archetypes', [])
    }

    try:
        summary = apply_theory_enhancements(
            mdl_path,
            patcher_input,
            output_mdl,
            add_colors=True,
            use_llm_layout=True,
            llm_client=client,
            color_scheme="archetype"
        )

        print(f"✓ Generated enhanced MDL!")
        print(f"  → Added {summary['variables_added']} variables")
        print(f"  → Added {summary['connections_added']} connections")
        print(f"  → Processed {summary['theories_processed']} archetypes")
        print(f"\n✓ Saved enhanced MDL to: {output_mdl}\n")

        # Verify purple colors
        mdl_content = output_mdl.read_text(encoding="utf-8")
        purple_vars = mdl_content.count("128-0-128")
        purple_conns = mdl_content.count("128,0,128")

        print(f"🎨 Color verification:")
        print(f"  → Purple variables (borders): {purple_vars}")
        print(f"  → Purple connections (arrows): {purple_conns}")

        if purple_vars > 0 or purple_conns > 0:
            print(f"\n✅ Success! Purple archetype colors are working!")
        else:
            print(f"\n⚠️  Warning: No purple colors found in MDL")

    except Exception as e:
        print(f"❌ MDL generation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_archetype_mdl_generation()

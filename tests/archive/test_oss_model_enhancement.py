#!/usr/bin/env python3
"""
Test: Apply theory enhancement to oss_model
"""
from pathlib import Path
from src.sd_model.mdl_enhancer import apply_enhancements

def main():
    print("=" * 80)
    print("Applying Theory Enhancement to oss_model")
    print("=" * 80)

    # Input files
    mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
    enhancement_json = Path("projects/oss_model/artifacts/theory_enhancement.json")

    # Output
    output_path = Path("tests/oss_model_enhanced_v2.mdl")

    if not mdl_path.exists():
        print(f"❌ Error: MDL file not found: {mdl_path}")
        return

    if not enhancement_json.exists():
        print(f"❌ Error: Enhancement JSON not found: {enhancement_json}")
        return

    print(f"\n1. Input MDL: {mdl_path}")
    print(f"2. Enhancement spec: {enhancement_json}")
    print(f"3. Output: {output_path}")

    # Apply enhancement
    print("\n4. Applying enhancements...")
    try:
        summary = apply_enhancements(
            mdl_path,
            enhancement_json,
            output_path,
            add_colors=True
        )

        print("\n5. Summary:")
        print(f"   Variables added: {summary['variables_added']}")
        print(f"   Connections added: {summary['connections_added']}")
        print(f"   Variables modified: {summary['variables_modified']}")
        print(f"   Variables removed: {summary['variables_removed']}")

        print(f"\n6. Generated: {output_path}")
        print(f"   Size: {output_path.stat().st_size} bytes")

        # Verify flow structure preserved
        with open(output_path) as f:
            content = f.read()
            # Check for valve structures
            valve_count = content.count('\n11,')
            print(f"   Valves preserved: {valve_count}")

        print("\n" + "=" * 80)
        print("✅ Enhancement complete! Check the file in Vensim:")
        print(f"   {output_path}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during enhancement: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

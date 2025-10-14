"""Generate MDL file from Step 2 test output and place in run artifacts."""
import sys
from pathlib import Path
import json
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sd_model.pipeline.theory_concretization import convert_to_legacy_format
from sd_model.mdl_creator import create_mdl_from_scratch

def main():
    # Paths
    test_output = Path(__file__).parent / "test_step2_output.json"
    run_dir = Path(__file__).parent.parent / "projects/oss_model/artifacts/runs/20251014_155310_comprehensive_planning"
    mdl_output_dir = run_dir / "mdl"
    project_mdl = Path(__file__).parent.parent / "projects/oss_model/mdl/untitled.mdl"

    print(f"Loading test output from: {test_output}")

    # Load Step 2 output
    with open(test_output) as f:
        step2_result = json.load(f)

    print(f"✓ Loaded Step 2 result: {len(step2_result.get('processes', []))} processes")

    # Convert to legacy format
    print("Converting to legacy theory_enhancement format...")
    legacy_format = convert_to_legacy_format(step2_result)

    # Save legacy format to run artifacts
    theory_enh_path = run_dir / "theory" / "theory_enhancement.json"
    with open(theory_enh_path, 'w') as f:
        json.dump(legacy_format, f, indent=2)
    print(f"✓ Saved theory_enhancement.json to: {theory_enh_path}")

    # Load original parsed MDL data
    parsed_path = run_dir / "parsing" / "parsed.json"
    with open(parsed_path) as f:
        parsed = json.load(f)

    print(f"✓ Loaded original model: {len(parsed.get('variables', []))} variables")

    # Create enhanced MDL
    print("\nGenerating enhanced MDL...")
    mdl_output_dir.mkdir(parents=True, exist_ok=True)

    enhanced_mdl_path = mdl_output_dir / "enhanced.mdl"

    create_mdl_from_scratch(
        theory_concretization=step2_result,
        output_path=enhanced_mdl_path,
        llm_client=None,
        clustering_scheme=step2_result.get('clustering_strategy'),
        template_mdl_path=Path(__file__).parent.parent / "projects/oss_model/mdl/untitled.mdl"
    )

    print(f"✓ Generated enhanced MDL: {enhanced_mdl_path}")

    # Copy to project mdl directory for next runs
    print(f"\nCopying enhanced MDL to project directory...")
    shutil.copy(enhanced_mdl_path, project_mdl)
    print(f"✓ Copied to: {project_mdl}")

    # Update run metadata
    metadata_path = run_dir / "run_metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)

    metadata['output_files']['enhanced_mdl'] = str(enhanced_mdl_path)

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Updated run metadata")

    # Count final statistics
    total_vars = sum(len(p.get('variables', [])) for p in step2_result.get('processes', []))
    total_conns = sum(len(p.get('connections', [])) for p in step2_result.get('processes', []))

    print(f"\n{'='*60}")
    print(f"✅ MDL Generation Complete!")
    print(f"{'='*60}")
    print(f"Processes: {len(step2_result.get('processes', []))}")
    print(f"Variables: {total_vars}")
    print(f"Connections: {total_conns}")
    print(f"\nEnhanced MDL saved to:")
    print(f"  Run artifacts: {enhanced_mdl_path}")
    print(f"  Project MDL: {project_mdl}")
    print(f"\nNext run will use this enhanced model.")

if __name__ == "__main__":
    main()

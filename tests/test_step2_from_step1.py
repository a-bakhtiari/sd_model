"""Test Step 2 (concretization) using Step 1 output from latest run."""
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sd_model.pipeline.theory_concretization import run_theory_concretization
from sd_model.llm.client import LLMClient

def main():
    # Load Step 1 output from latest run
    project_path = Path(__file__).parent.parent / "projects" / "oss_model"
    latest_run = project_path / "artifacts" / "runs" / "20251014_155310_comprehensive_planning"

    step1_path = latest_run / "theory" / "theory_planning_step1.json"
    variables_path = latest_run / "parsing" / "variables.json"
    connections_path = latest_run / "parsing" / "connections.json"

    print(f"Loading Step 1 output from: {step1_path}")

    with open(step1_path) as f:
        planning_result = json.load(f)

    with open(variables_path) as f:
        variables = json.load(f)

    with open(connections_path) as f:
        connections = json.load(f)

    print(f"✓ Loaded Step 1: {len(planning_result.get('clustering_strategy', {}).get('clusters', []))} clusters")
    print(f"✓ Current model: {len(variables.get('variables', []))} variables, {len(connections.get('connections', []))} connections")

    # Run Step 2
    print("\nRunning Step 2 (theory concretization)...")

    result = run_theory_concretization(
        planning_result=planning_result,
        variables=variables,
        connections=connections,
        plumbing=None,
        llm_client=None,  # Will create default
        recreate_mode=False
    )

    # Save result
    output_path = Path(__file__).parent / "test_step2_output.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✓ Step 2 complete!")
    print(f"Output saved to: {output_path}")
    print(f"Processes: {len(result.get('processes', []))}")

    # Count total variables and connections
    total_vars = sum(len(p.get('variables', [])) for p in result.get('processes', []))
    total_conns = sum(len(p.get('connections', [])) for p in result.get('processes', []))
    print(f"Total variables: {total_vars}")
    print(f"Total connections: {total_conns}")

    if 'error' in result:
        print(f"\n⚠️ Error: {result['error']}")
        print(f"Check raw response at: /tmp/step2_raw_response.txt")
    else:
        print("\n✅ Success! No errors detected.")

if __name__ == "__main__":
    main()

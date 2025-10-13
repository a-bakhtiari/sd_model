"""Test script to see what format_model_structure() outputs with clouds."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from sd_model.pipeline.theory_planning import format_model_structure

# Load test data
project_dir = Path(__file__).parent / "projects/oss_model/artifacts"
variables_path = project_dir / "parsing/variables.json"
connections_path = project_dir / "parsing/connections.json"
plumbing_path = project_dir / "parsing/plumbing.json"

variables = json.loads(variables_path.read_text())
connections = json.loads(connections_path.read_text())

# Check if plumbing exists
plumbing = None
if plumbing_path.exists():
    plumbing = json.loads(plumbing_path.read_text())
    print(f"✓ Found plumbing.json with {len(plumbing.get('clouds', []))} clouds")
else:
    print("✗ No plumbing.json found")

# Format the model structure
output = format_model_structure(variables, connections, plumbing)

print("=" * 80)
print("MODEL STRUCTURE OUTPUT (WITH CLOUDS)")
print("=" * 80)
print()
print(output)
print()
print("=" * 80)

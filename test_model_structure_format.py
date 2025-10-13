"""Test script to see what format_model_structure() outputs."""
import json
from pathlib import Path

# Import the function
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))
from sd_model.pipeline.theory_planning import format_model_structure

# Load test data
variables_path = Path(__file__).parent / "projects/sd_test/artifacts/parsing/variables.json"
connections_path = Path(__file__).parent / "projects/sd_test/artifacts/parsing/connections.json"

variables = json.loads(variables_path.read_text())
connections = json.loads(connections_path.read_text())

# Format the model structure
output = format_model_structure(variables, connections)

print("=" * 80)
print("MODEL STRUCTURE FORMAT TEST")
print("=" * 80)
print()
print(output)
print()
print("=" * 80)

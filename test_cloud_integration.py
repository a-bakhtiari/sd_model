"""Test cloud integration in model structure display."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from sd_model.pipeline.theory_planning import format_model_structure

# Load real data
project_dir = Path(__file__).parent / "projects/oss_model/artifacts"
variables_path = project_dir / "parsing/variables.json"
connections_path = project_dir / "parsing/connections.json"

variables = json.loads(variables_path.read_text())
connections = json.loads(connections_path.read_text())

# Create mock plumbing with clouds
mock_plumbing = {
    "clouds": [
        {"id": 10001, "x": 150, "y": 200, "w": 50, "h": 50},
        {"id": 10002, "x": 800, "y": 450, "w": 50, "h": 50},
        {"id": 10003, "x": 1200, "y": 600, "w": 50, "h": 50}
    ],
    "valves": [],
    "flows": []
}

print("=" * 80)
print("MODEL STRUCTURE WITH MOCK CLOUDS")
print("=" * 80)
print()

# Test with clouds
output = format_model_structure(variables, connections, mock_plumbing)
print(output)

print()
print("=" * 80)
print()

# Test without clouds (for comparison)
print("=" * 80)
print("MODEL STRUCTURE WITHOUT CLOUDS (for comparison)")
print("=" * 80)
print()
output_no_clouds = format_model_structure(variables, connections, None)
print(output_no_clouds)

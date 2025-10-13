"""Test cloud-flow connection display."""
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

# Find a flow variable to use in example
flow_vars = [v for v in variables['variables'] if v.get('type') == 'Flow']
stock_vars = [v for v in variables['variables'] if v.get('type') == 'Stock']

recruitment_flow = next((v for v in flow_vars if 'join' in v['name'].lower()), flow_vars[0])
attrition_flow = next((v for v in flow_vars if 'turn' in v['name'].lower() or 'churn' in v['name'].lower()), flow_vars[1])
target_stock = next((v for v in stock_vars if 'contributor' in v['name'].lower()), stock_vars[0])

print(f"Using flow: {recruitment_flow['name']} (ID: {recruitment_flow['id']})")
print(f"Using flow: {attrition_flow['name']} (ID: {attrition_flow['id']})")
print(f"Using stock: {target_stock['name']} (ID: {target_stock['id']})")

# Create complete plumbing with flows
mock_plumbing = {
    "clouds": [
        {"id": 10001, "x": 150, "y": 200, "w": 50, "h": 50},
        {"id": 10002, "x": 800, "y": 450, "w": 50, "h": 50}
    ],
    "valves": [
        {"id": 5001, "name": recruitment_flow['name']},
        {"id": 5002, "name": attrition_flow['name']}
    ],
    "flows": [
        {
            "valve_id": 5001,
            "from": {"kind": "cloud", "ref": 10001},
            "to": {"kind": "variable", "ref": target_stock['id']}
        },
        {
            "valve_id": 5002,
            "from": {"kind": "variable", "ref": target_stock['id']},
            "to": {"kind": "cloud", "ref": 10002}
        }
    ]
}

print("\n" + "=" * 80)
print("MODEL STRUCTURE WITH CLOUD-FLOW CONNECTIONS")
print("=" * 80)
print()

output = format_model_structure(variables, connections, mock_plumbing)
print(output)

print()
print("=" * 80)

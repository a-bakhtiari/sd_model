"""Analyze MDL file to establish ground truth for testing."""
import sys
from pathlib import Path

mdl_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("projects/oss_model/mdl/untitled.mdl")

lines = mdl_path.read_text().splitlines()

# Find variables, valves, and connections
variables = {}  # id -> name
valves = set()  # valve IDs
connections = []  # (from_id, to_id, field6)

for line in lines:
    if line.startswith("10,"):
        parts = line.split(",")
        var_id = int(parts[1])
        var_name = parts[2].strip('"')
        variables[var_id] = var_name
    elif line.startswith("11,"):
        parts = line.split(",")
        valve_id = int(parts[1])
        valves.add(valve_id)
    elif line.startswith("1,"):
        parts = line.split(",")
        if len(parts) >= 7:
            from_id = int(parts[2])
            to_id = int(parts[3])
            field6 = parts[6]
            connections.append((from_id, to_id, field6))

# Find stocks (variables that receive from valves)
# But exclude valve-to-valve connections
stocks = set()
for from_id, to_id, _ in connections:
    if from_id in valves and to_id not in valves:
        stocks.add(to_id)

# Find flows (valves that point to stocks)
flows = set()
for from_id, to_id, _ in connections:
    if from_id in valves and to_id in stocks:
        # The valve represents a flow variable
        # Try to match by position or name
        flows.add(from_id)

# Count variable→variable connections (exclude valves)
var_to_var_conns = [(f, t, p) for f, t, p in connections
                     if f not in valves and t not in valves]

print("="*80)
print(f"MDL GROUND TRUTH ANALYSIS: {mdl_path.name}")
print("="*80)
print(f"\nVariables (10, lines): {len(variables)}")
print(f"Valves (11, lines):    {len(valves)}")
print(f"Connections (1, lines): {len(connections)}")
print(f"\nStock IDs (receive from valves): {len(stocks)}")
print(f"Stock IDs: {sorted(stocks)}")
print(f"\nFlow valve IDs: {len(flows)}")
print(f"Flow IDs: {sorted(flows)}")
print(f"\nVariable→Variable connections: {len(var_to_var_conns)}")

# Show which variables are which type
print(f"\n{'VARIABLE TYPES':-^80}")
print(f"\nStocks ({len(stocks)}):")
for stock_id in sorted(stocks):
    print(f"  {stock_id:3d}: {variables.get(stock_id, 'UNKNOWN')}")

print(f"\nValve→Stock Connections:")
for from_id, to_id, field6 in connections:
    if from_id in valves and to_id in stocks:
        print(f"  Valve {from_id:3d} → Stock {to_id:3d}: {variables.get(to_id, 'UNKNOWN')}")

# Analyze field[6] for polarity markers
positive_markers = [(f, t) for f, t, p in connections if p == "43"]
print(f"\n{'POLARITY MARKERS':-^80}")
print(f"\nPositive markers (field[6]=43): {len(positive_markers)}")
for from_id, to_id in positive_markers[:10]:
    from_name = variables.get(from_id, f"Valve{from_id}" if from_id in valves else f"ID{from_id}")
    to_name = variables.get(to_id, f"Valve{to_id}" if to_id in valves else f"ID{to_id}")
    print(f"  {from_id:3d} → {to_id:3d}: {from_name} → {to_name}")

if len(positive_markers) > 10:
    print(f"  ... and {len(positive_markers) - 10} more")

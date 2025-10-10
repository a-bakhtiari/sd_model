"""Check which stock IDs have variable definitions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "archive"))
from mdl_surgical_parser import MDLSurgicalParser

mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
parser = MDLSurgicalParser(mdl_path)
parser.parse()

# Get all variable IDs (from 10, lines)
variable_ids = set(parser.sketch_vars.keys())
print(f"Variables with definitions (10, lines): {len(variable_ids)}")
print(f"Variable IDs: {sorted(variable_ids)}\n")

# Get all valve IDs
valve_ids = set()
for line in parser.sketch_other:
    if line.startswith("11,"):
        parts = line.split(",")
        valve_ids.add(int(parts[1]))

# Get all stock IDs (receive from valves, exclude valve-to-valve)
stock_ids = set()
for line in parser.sketch_other:
    if line.startswith("1,"):
        parts = line.split(",")
        if len(parts) >= 4:
            from_id = int(parts[2])
            to_id = int(parts[3])
            if from_id in valve_ids and to_id not in valve_ids:
                stock_ids.add(to_id)

print(f"Stock IDs (from connections): {len(stock_ids)}")
print(f"Stock IDs: {sorted(stock_ids)}\n")

# Which stocks have variable definitions?
stocks_with_vars = stock_ids & variable_ids
stocks_without_vars = stock_ids - variable_ids

print(f"Stocks WITH variable definitions: {len(stocks_with_vars)}")
print(f"IDs: {sorted(stocks_with_vars)}")

print(f"\nStocks WITHOUT variable definitions (orphaned): {len(stocks_without_vars)}")
print(f"IDs: {sorted(stocks_without_vars)}")

# Show names for stocks with definitions
print(f"\n{'Stocks with variables':-^80}")
for stock_id in sorted(stocks_with_vars):
    var_name = parser.sketch_vars[stock_id].name
    print(f"  ID {stock_id:3d}: {var_name}")

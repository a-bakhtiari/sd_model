"""Debug stock detection issue."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "archive"))
from mdl_surgical_parser import MDLSurgicalParser

mdl_path = Path("projects/oss_model/mdl/untitled.mdl")
parser = MDLSurgicalParser(mdl_path)
parser.parse()

print(f"Total sketch_other lines: {len(parser.sketch_other)}")

# First pass: Find all valves
valve_ids = set()
for line in parser.sketch_other:
    if line.startswith("11,"):
        parts = line.split(",")
        if len(parts) >= 2:
            valve_id = int(parts[1])
            valve_ids.add(valve_id)

print(f"Valve IDs found: {len(valve_ids)}")
print(f"Valve IDs: {sorted(valve_ids)}")

# Second pass: Find stocks (variables receiving from valves)
valve_to_stock = {}
stock_ids = set()

for line in parser.sketch_other:
    if line.startswith("1,"):
        parts = line.split(",")
        if len(parts) >= 4:
            from_id = int(parts[2])
            to_id = int(parts[3])

            if from_id in valve_ids:
                if from_id not in valve_to_stock:
                    valve_to_stock[from_id] = []
                valve_to_stock[from_id].append(to_id)
                # Only add to stock_ids if target is NOT a valve (valve-to-valve connections exist)
                if to_id not in valve_ids:
                    stock_ids.add(to_id)

print(f"\nStocks found: {len(stock_ids)}")
print(f"Stock IDs: {sorted(stock_ids)}")

print(f"\nValve → Stock mappings:")
for valve_id in sorted(valve_to_stock.keys()):
    stocks = valve_to_stock[valve_id]
    print(f"  Valve {valve_id:3d} → Stocks {stocks}")

# Compare with ground truth (29 stocks - excluding valve-to-valve ID 90)
expected_stocks = [1, 2, 4, 5, 6, 7, 12, 17, 22, 30, 31, 36, 42, 47, 48, 49, 50, 51, 56, 65, 72, 81, 87, 106, 113, 118, 128, 141, 142]
missing = set(expected_stocks) - stock_ids
extra = stock_ids - set(expected_stocks)

print(f"\n{'COMPARISON':-^80}")
print(f"Expected stocks: {len(expected_stocks)}")
print(f"Found stocks:    {len(stock_ids)}")
print(f"Missing:         {len(missing)} - {sorted(missing) if missing else 'None'}")
print(f"Extra:           {len(extra)} - {sorted(extra) if extra else 'None'}")

if stock_ids == set(expected_stocks):
    print("\n✅ PERFECT MATCH!")
else:
    print("\n❌ MISMATCH")

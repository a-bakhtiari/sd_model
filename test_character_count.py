"""Compare character counts between original JSON vs formatted output."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from sd_model.pipeline.theory_planning import format_model_structure

# Load test data
variables_path = Path(__file__).parent / "projects/sd_test/artifacts/parsing/variables.json"
connections_path = Path(__file__).parent / "projects/sd_test/artifacts/parsing/connections.json"

variables = json.loads(variables_path.read_text())
connections = json.loads(connections_path.read_text())

# METHOD 1: Original JSON format (as shown in prompt)
all_vars = variables.get("variables", [])
vars_text_original = "\n".join([
    f"- {v['name']} ({v.get('type', 'Unknown')})"
    for v in all_vars
])

all_conns = connections.get("connections", [])
# Convert to name-based for original format
id_to_name = {int(v["id"]): v["name"] for v in all_vars}
conns_text_original = []
for conn in all_conns:
    from_name = id_to_name.get(int(conn.get("from", -1)))
    to_name = id_to_name.get(int(conn.get("to", -1)))
    if not from_name or not to_name:
        continue
    polarity = str(conn.get("polarity", "UNDECLARED")).upper()
    if polarity == "POSITIVE":
        relationship = "positive"
    elif polarity == "NEGATIVE":
        relationship = "negative"
    else:
        relationship = "unknown"
    conns_text_original.append(f"- {from_name} → {to_name} ({relationship})")

conns_text_original = "\n".join(conns_text_original)

original_format = f"""## Variables ({len(all_vars)} total)
{vars_text_original}

## Connections ({len(all_conns)} total)
{conns_text_original}"""

# METHOD 2: Formatted causal chains
formatted_output = format_model_structure(variables, connections)

# Count characters
original_chars = len(original_format)
formatted_chars = len(formatted_output)

print("=" * 80)
print("CHARACTER COUNT COMPARISON")
print("=" * 80)
print()
print(f"ORIGINAL FORMAT (Variables + Connections lists):")
print(f"  Character count: {original_chars:,}")
print()
print(f"FORMATTED CAUSAL CHAINS:")
print(f"  Character count: {formatted_chars:,}")
print()
print(f"DIFFERENCE: {formatted_chars - original_chars:,} characters")
print(f"  ({((formatted_chars - original_chars) / original_chars * 100):.1f}% {'longer' if formatted_chars > original_chars else 'shorter'})")
print()
print("=" * 80)
print()
print("ORIGINAL FORMAT PREVIEW:")
print("=" * 80)
print(original_format[:500] + "..." if len(original_format) > 500 else original_format)
print()
print("=" * 80)
print()
print("FORMATTED FORMAT PREVIEW:")
print("=" * 80)
print(formatted_output[:500] + "..." if len(formatted_output) > 500 else formatted_output)
print()
print("=" * 80)

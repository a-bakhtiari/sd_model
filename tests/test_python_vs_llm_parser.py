"""Test Python parser vs LLM parser comparison.

Compares the deterministic Python-based MDL parser with the LLM-based parser
to validate that the Python approach can accurately extract all variables and
connections needed for the pipeline.
"""
import argparse
import json
import sys
from pathlib import Path

# Add archive to path to access the surgical parser
sys.path.insert(0, str(Path(__file__).parent / "archive"))

from mdl_surgical_parser import MDLSurgicalParser


def extract_python_parser_data(mdl_path: Path):
    """Extract variables and connections using Python surgical parser."""
    parser = MDLSurgicalParser(mdl_path)
    parser.parse()

    # Extract variables with their visual properties
    variables = []
    for sketch_id, var in sorted(parser.sketch_vars.items()):
        # Parse the sketch line to get visual properties
        line = var.full_line
        parts = []
        in_quotes = False
        current = ""

        # Parse CSV with quoted strings handling
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                parts.append(current)
                current = ""
                continue
            current += char
        parts.append(current)

        # Map shape codes to variable types
        # Format: 10,ID,Name,X,Y,Width,Height,ShapeCode,...
        # Based on Vensim MDL format:
        # - Shape 3 = Stock (rectangle)
        # - Shape 40 = Flow (valve)
        # - Shape 8, 27 = Auxiliary (cloud/circle)
        var_type_map = {
            "3": "Stock",      # Stock variables
            "40": "Flow",      # Flow/rate variables
            "8": "Auxiliary",  # Auxiliary variables
            "27": "Auxiliary", # Another auxiliary shape
        }

        shape_code = parts[7] if len(parts) > 7 else "3"
        var_type = var_type_map.get(shape_code, "Auxiliary")

        var_data = {
            "id": sketch_id,
            "name": var.name,
            "type": var_type,
            "x": int(parts[3]) if len(parts) > 3 else 0,
            "y": int(parts[4]) if len(parts) > 4 else 0,
            "width": int(parts[5]) if len(parts) > 5 else 0,
            "height": int(parts[6]) if len(parts) > 6 else 0
        }

        # Check for custom colors (fields 16-18)
        # Format: ...,TextColor,BorderColor,FillColor,...
        if len(parts) > 17:
            text_color = parts[15] if len(parts) > 15 else ""
            border_color = parts[16] if len(parts) > 16 else ""
            fill_color = parts[17] if len(parts) > 17 else ""

            # Only add colors if they're actually specified (not empty or default)
            if text_color or border_color or fill_color:
                colors = {}
                if text_color and text_color != "0-0-0" or True:  # Include all
                    colors["text"] = text_color
                if border_color:
                    colors["border"] = border_color
                if fill_color:
                    colors["fill"] = fill_color
                if colors:
                    var_data["colors"] = colors

        variables.append(var_data)

    # Variables are complete - type is determined solely by shape code
    final_variables = variables

    # Extract connections from both sketch arrows and equations
    # Sketch arrows show visual connections, equations show logical dependencies
    sketch_connections = extract_connections_from_sketch(parser)
    equation_connections = extract_connections_from_equations(parser)

    # Merge connections, prioritizing equation polarity over sketch polarity
    connections = merge_connections(sketch_connections, equation_connections)

    return final_variables, connections


def extract_connections_from_sketch(parser: MDLSurgicalParser):
    """Extract connections from sketch arrows (visual connections).

    Only includes arrows where both endpoints are actual variables,
    not intermediate objects like valves or clouds.
    """
    connections = []

    # Get set of actual variable IDs (defined with 10, lines)
    var_ids = set(parser.sketch_vars.keys())

    for line in parser.sketch_other:
        # Format: 1,ArrowID,FromID,ToID,?,?,Field6,...
        # Field6=43 indicates POSITIVE polarity
        if line.startswith("1,"):
            parts = line.split(",")
            if len(parts) >= 7:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Only include connections between actual variables
                    # Skip arrows to/from valves, clouds, and other intermediate objects
                    if from_id not in var_ids or to_id not in var_ids:
                        continue

                    field6 = parts[6]

                    # Determine polarity from field6
                    polarity = "POSITIVE" if field6 == "43" else "UNDECLARED"

                    connections.append({
                        "from": from_id,
                        "to": to_id,
                        "polarity": polarity
                    })
                except (ValueError, IndexError):
                    continue

    return connections


def merge_connections(sketch_conns, equation_conns):
    """Merge sketch and equation connections, prioritizing equation polarity."""
    # Create a dict indexed by (from, to) pair
    conn_dict = {}

    # First add sketch connections
    for conn in sketch_conns:
        key = (conn["from"], conn["to"])
        conn_dict[key] = conn

    # Then overlay equation connections (they override sketch polarity)
    for conn in equation_conns:
        key = (conn["from"], conn["to"])
        if key in conn_dict:
            # Connection exists in both - use equation polarity if more specific
            if conn["polarity"] != "UNDECLARED":
                conn_dict[key]["polarity"] = conn["polarity"]
        else:
            # New connection from equations only
            conn_dict[key] = conn

    # Convert back to list
    return list(conn_dict.values())


def extract_connections_from_equations(parser: MDLSurgicalParser):
    """Extract logical connections from equation dependencies."""
    connections = []

    # Build an improved name_to_id mapping that handles duplicates
    # When there are duplicate names, prioritize: Flow (40) > Stock (3) > Auxiliary (8, 27)
    name_to_id_improved = {}

    for sketch_id, var in parser.sketch_vars.items():
        name = var.name
        parts = var.full_line.split(',')
        shape_code = parts[7] if len(parts) > 7 else "0"

        # Type priority: 40 (Flow) = 3, 3 (Stock) = 2, others (Auxiliary) = 1
        priority_map = {"40": 3, "3": 2}
        priority = priority_map.get(shape_code, 1)

        if name not in name_to_id_improved:
            name_to_id_improved[name] = (sketch_id, priority)
        else:
            existing_id, existing_priority = name_to_id_improved[name]
            if priority > existing_priority:
                # Higher priority wins
                name_to_id_improved[name] = (sketch_id, priority)

    # Convert to simple dict
    name_to_id_final = {name: id_priority[0] for name, id_priority in name_to_id_improved.items()}

    for var_name in parser.equation_order:
        if var_name not in parser.equations:
            continue

        equation = parser.equations[var_name]
        equation_line = equation.equation_line

        # Find variable ID for this target (use improved mapping)
        target_id = name_to_id_final.get(var_name)
        if not target_id:
            continue

        # Parse "A FUNCTION OF(...)" to find dependencies
        # Format: VarName = A FUNCTION OF( Var1, Var2, -Var3, ...)
        if "A FUNCTION OF" in equation_line:
            # Extract content inside parentheses
            start = equation_line.find("(")
            end = equation_line.rfind(")")
            if start != -1 and end != -1:
                deps_str = equation_line[start+1:end]

                # Handle continuation lines first
                deps_str = deps_str.replace("\\\n", " ").replace("\\n", " ").replace("\n", " ")
                deps_str = deps_str.replace("\t", " ").strip()

                # Parse dependencies respecting quoted strings (CSV-style)
                dep_parts = []
                current = ""
                in_quotes = False

                for char in deps_str:
                    if char == '"':
                        in_quotes = not in_quotes
                    elif char == ',' and not in_quotes:
                        if current.strip():
                            dep_parts.append(current.strip())
                        current = ""
                        continue
                    current += char

                # Add last part
                if current.strip():
                    dep_parts.append(current.strip())

                for dep in dep_parts:
                    if not dep:
                        continue

                    # Check for negative polarity (starts with -)
                    is_negative = dep.startswith("-")
                    source_name = dep.lstrip("-").strip().strip('"')

                    # Find source ID (use improved mapping that handles duplicates)
                    source_id = name_to_id_final.get(source_name)
                    if source_id:
                        polarity = "NEGATIVE" if is_negative else "UNDECLARED"
                        connections.append({
                            "from": source_id,
                            "to": target_id,
                            "polarity": polarity
                        })

    return connections


def compare_results(llm_vars, llm_conns, python_vars, python_conns):
    """Compare LLM and Python parser results with detailed analysis."""
    print("\n" + "="*80)
    print("PYTHON PARSER VS LLM PARSER COMPARISON")
    print("="*80)

    # Compare variables
    print(f"\n{'VARIABLES':-^80}")
    print(f"LLM count:    {len(llm_vars)}")
    print(f"Python count: {len(python_vars)}")

    llm_var_ids = {v["id"] for v in llm_vars}
    python_var_ids = {v["id"] for v in python_vars}

    missing_in_python = llm_var_ids - python_var_ids
    extra_in_python = python_var_ids - llm_var_ids

    if missing_in_python:
        print(f"\n⚠️  Variables in LLM but MISSING in Python: {sorted(missing_in_python)}")
        for vid in sorted(missing_in_python):
            llm_var = next(v for v in llm_vars if v["id"] == vid)
            print(f"    ID {vid}: {llm_var['name']} ({llm_var['type']})")

    if extra_in_python:
        print(f"\n✓ Variables in Python but NOT in LLM: {sorted(extra_in_python)}")
        for vid in sorted(extra_in_python):
            python_var = next(v for v in python_vars if v["id"] == vid)
            print(f"    ID {vid}: {python_var['name']} ({python_var['type']})")

    # Detailed variable comparison
    print(f"\n{'Variable Details':-^80}")
    mismatches = []

    for llm_var in sorted(llm_vars, key=lambda v: v["id"]):
        python_var = next((v for v in python_vars if v["id"] == llm_var["id"]), None)
        if python_var:
            issues = []
            if llm_var["name"] != python_var["name"]:
                issues.append(f"name: '{llm_var['name']}' vs '{python_var['name']}'")
            if llm_var.get("type") != python_var.get("type"):
                issues.append(f"type: {llm_var.get('type')} vs {python_var.get('type')}")
            if llm_var.get("x") != python_var.get("x") or llm_var.get("y") != python_var.get("y"):
                issues.append(f"pos: ({llm_var.get('x')},{llm_var.get('y')}) vs ({python_var.get('x')},{python_var.get('y')})")

            if issues:
                mismatches.append((llm_var["id"], llm_var["name"], issues))

    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} variable mismatches:")
        for vid, name, issues in mismatches:
            print(f"\n  ID {vid} ({name}):")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("✅ All common variables match perfectly!")

    # Compare connections
    print(f"\n{'CONNECTIONS':-^80}")
    print(f"LLM count:    {len(llm_conns)}")
    print(f"Python count: {len(python_conns)}")

    # Create comparable sets
    llm_conn_set = {(c["from"], c["to"], c["polarity"]) for c in llm_conns}
    python_conn_set = {(c["from"], c["to"], c["polarity"]) for c in python_conns}

    # Also compare ignoring polarity
    llm_conn_pairs = {(c["from"], c["to"]) for c in llm_conns}
    python_conn_pairs = {(c["from"], c["to"]) for c in python_conns}

    missing_pairs = llm_conn_pairs - python_conn_pairs
    extra_pairs = python_conn_pairs - llm_conn_pairs

    if missing_pairs:
        print(f"\n⚠️  Connections in LLM but MISSING in Python ({len(missing_pairs)}):")
        for from_id, to_id in sorted(missing_pairs):
            llm_conn = next(c for c in llm_conns if c["from"] == from_id and c["to"] == to_id)
            from_name = next((v["name"] for v in llm_vars if v["id"] == from_id), f"ID{from_id}")
            to_name = next((v["name"] for v in llm_vars if v["id"] == to_id), f"ID{to_id}")
            print(f"    {from_id:2d} → {to_id:2d} ({llm_conn['polarity']:11s}) | {from_name} → {to_name}")

    if extra_pairs:
        print(f"\n✓ Connections in Python but NOT in LLM ({len(extra_pairs)}):")
        for from_id, to_id in sorted(extra_pairs):
            python_conn = next(c for c in python_conns if c["from"] == from_id and c["to"] == to_id)
            from_name = next((v["name"] for v in python_vars if v["id"] == from_id), f"ID{from_id}")
            to_name = next((v["name"] for v in python_vars if v["id"] == to_id), f"ID{to_id}")
            print(f"    {from_id:2d} → {to_id:2d} ({python_conn['polarity']:11s}) | {from_name} → {to_name}")

    # Check polarity differences for common connections
    common_pairs = llm_conn_pairs & python_conn_pairs
    polarity_diffs = []

    for from_id, to_id in common_pairs:
        llm_conn = next(c for c in llm_conns if c["from"] == from_id and c["to"] == to_id)
        python_conn = next(c for c in python_conns if c["from"] == from_id and c["to"] == to_id)

        if llm_conn["polarity"] != python_conn["polarity"]:
            polarity_diffs.append((from_id, to_id, llm_conn["polarity"], python_conn["polarity"]))

    if polarity_diffs:
        print(f"\n⚠️  Polarity differences ({len(polarity_diffs)}):")
        for from_id, to_id, llm_pol, py_pol in sorted(polarity_diffs):
            from_name = next((v["name"] for v in llm_vars if v["id"] == from_id), f"ID{from_id}")
            to_name = next((v["name"] for v in llm_vars if v["id"] == to_id), f"ID{to_id}")
            print(f"    {from_id:2d} → {to_id:2d} | LLM: {llm_pol:11s} | Python: {py_pol:11s} | {from_name} → {to_name}")

    # Overall assessment
    print(f"\n{'ASSESSMENT':-^80}")

    vars_complete = not missing_in_python
    conns_complete = not missing_pairs
    exact_match = (llm_var_ids == python_var_ids and
                   llm_conn_set == python_conn_set and
                   not mismatches)

    if exact_match:
        print("✅ PERFECT MATCH")
        print("   Python parser extracts exactly the same data as LLM parser")
        print("   Safe to replace LLM with Python parser")
        return "perfect"
    elif vars_complete and conns_complete:
        print("✅ STRUCTURALLY COMPLETE")
        print("   Python parser captures all variables and connections")
        if mismatches or polarity_diffs:
            print("   Minor differences in details (review above)")
        print("   Likely safe to replace LLM with Python parser")
        return "complete"
    else:
        print("⚠️  INCOMPLETE")
        print("   Python parser is missing some data from LLM")
        print("   Needs fixes before replacing LLM parser")
        return "incomplete"


def main():
    """Run comparison test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Compare Python parser vs LLM parser")
    parser.add_argument(
        "--project",
        type=str,
        default="sd_test",
        choices=["sd_test", "oss_model"],
        help="Project to test (default: sd_test)"
    )
    args = parser.parse_args()

    # Paths based on project
    project_root = Path(__file__).parent.parent
    project_name = args.project

    # Configure paths for each project
    if project_name == "sd_test":
        mdl_path = project_root / "projects/sd_test/artifacts/test_enhanced.mdl"
    elif project_name == "oss_model":
        mdl_path = project_root / "projects/oss_model/mdl/untitled.mdl"
    else:
        print(f"Unknown project: {project_name}")
        return 1

    # Common paths
    llm_vars_path = project_root / f"projects/{project_name}/artifacts/parsing/variables_llm.json"
    llm_conns_path = project_root / f"projects/{project_name}/artifacts/parsing/connections_llm.json"

    print(f"Testing Python parser against LLM parser")
    print(f"Project: {project_name}")
    print(f"MDL file: {mdl_path}")
    print(f"LLM results: {llm_vars_path.parent}")

    # Check if files exist
    if not mdl_path.exists():
        print(f"❌ MDL file not found: {mdl_path}")
        return 1
    if not llm_vars_path.exists():
        print(f"❌ LLM variables file not found: {llm_vars_path}")
        return 1
    if not llm_conns_path.exists():
        print(f"❌ LLM connections file not found: {llm_conns_path}")
        return 1

    # Load LLM results
    with open(llm_vars_path) as f:
        llm_data = json.load(f)
        llm_vars = llm_data["variables"]

    with open(llm_conns_path) as f:
        llm_data = json.load(f)
        llm_conns = llm_data["connections"]

    # Run Python parser
    print("\nRunning Python parser...")
    python_vars, python_conns = extract_python_parser_data(mdl_path)

    # Save Python results for inspection (project-specific names)
    python_vars_path = project_root / f"tests/{project_name}_python_parser_variables.json"
    python_conns_path = project_root / f"tests/{project_name}_python_parser_connections.json"

    with open(python_vars_path, "w") as f:
        json.dump({"variables": python_vars}, f, indent=2)

    with open(python_conns_path, "w") as f:
        json.dump({"connections": python_conns}, f, indent=2)

    print(f"✓ Python parser results saved:")
    print(f"  - {python_vars_path}")
    print(f"  - {python_conns_path}")

    # Compare
    result = compare_results(llm_vars, llm_conns, python_vars, python_conns)

    print("\n" + "="*80)

    return 0 if result in ["perfect", "complete"] else 1


if __name__ == "__main__":
    sys.exit(main())

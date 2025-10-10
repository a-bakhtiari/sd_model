"""Python-based MDL parser for extracting variables and connections.

This module provides deterministic parsing of Vensim MDL files, extracting:
- Variables with IDs, names, types, positions
- Connections with polarities from visual diagram structure

Replaces LLM-based extraction with ~100x faster and more accurate parsing.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Dict, List

from .mdl_surgical_parser import MDLSurgicalParser


def extract_variables(mdl_path: Path) -> Dict:
    """Extract variables from MDL file using Python parser.

    Args:
        mdl_path: Path to .mdl file

    Returns:
        Dict with format matching LLM output:
        {
            "variables": [
                {
                    "id": int,
                    "name": str,
                    "type": "Stock" | "Flow" | "Auxiliary",
                    "x": int,
                    "y": int,
                    "width": int,
                    "height": int,
                    "colors": {...}  # optional
                }
            ]
        }
    """
    parser = MDLSurgicalParser(mdl_path)
    parser.parse()  # Parse the MDL file
    variables = []

    for var_id, var in parser.sketch_vars.items():
        # Use CSV parser to handle quoted fields properly
        reader = csv.reader(io.StringIO(var.full_line))
        parts = next(reader)

        # Extract shape code (field 7) to determine type
        shape_code = parts[7] if len(parts) > 7 else "0"

        # Map shape codes to types
        if shape_code == "3":
            var_type = "Stock"
        elif shape_code == "40":
            var_type = "Flow"
        else:  # 8, 27, or others
            var_type = "Auxiliary"

        # Extract position and size
        x = int(parts[3]) if len(parts) > 3 else 0
        y = int(parts[4]) if len(parts) > 4 else 0
        width = int(parts[5]) if len(parts) > 5 else 46
        height = int(parts[6]) if len(parts) > 6 else 26

        variable = {
            "id": var_id,
            "name": var.name,
            "type": var_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }

        # Extract colors if present (fields 16-18)
        if len(parts) >= 18:
            # Check for color patterns like "0-0-0"
            colors = {}
            for i, field_name in [(15, "text"), (16, "border"), (17, "fill")]:
                if i < len(parts) and "-" in parts[i]:
                    colors[field_name] = parts[i]
            if colors:
                variable["colors"] = colors

        variables.append(variable)

    return {"variables": variables}


def extract_connections(mdl_path: Path, variables_data: Dict) -> Dict:
    """Extract connections from MDL file using Python parser.

    Args:
        mdl_path: Path to .mdl file
        variables_data: Variables data from extract_variables() (for compatibility)

    Returns:
        Dict with format matching LLM output:
        {
            "connections": [
                {
                    "from": int,
                    "to": int,
                    "polarity": "POSITIVE" | "NEGATIVE" | "UNDECLARED"
                }
            ]
        }
    """
    parser = MDLSurgicalParser(mdl_path)
    parser.parse()  # Parse the MDL file

    # Extract connections from two sources:
    # 1. Sketch arrows (visual connections with valve resolution)
    # 2. Stock-flow relationships (from equations)
    sketch_conns = _extract_connections_from_sketch(parser)
    stock_flow_conns = _extract_stock_flow_connections(parser)

    # Merge and deduplicate
    connections = _merge_connections(sketch_conns, stock_flow_conns)

    return {"connections": connections}


def _extract_connections_from_sketch(parser: MDLSurgicalParser) -> List[Dict]:
    """Extract connections from sketch arrows (visual connections).

    Resolves valve-mediated connections to flow variables.
    In SD diagrams: Stock → Valve → Stock becomes Stock → Flow → Stock

    Valve resolution:
    - If valve ID = flow variable ID: direct mapping
    - If valve ID ≠ flow variable ID: find which stock valve feeds,
      check stock's equation to identify the flow
    """
    connections = []

    # Get set of actual variable IDs (defined with 10, lines)
    var_ids = set(parser.sketch_vars.keys())

    # Get set of valve IDs (defined with 11, lines)
    valve_ids = set()
    for line in parser.sketch_other:
        if line.startswith("11,"):
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    valve_ids.add(int(parts[1]))
                except ValueError:
                    continue

    # Build valve → flow variable mapping
    # Method 1: Direct mapping (valve ID = flow variable ID)
    valve_to_flow = {}
    for var_id, var in parser.sketch_vars.items():
        parts = var.full_line.split(",")
        shape_code = parts[7] if len(parts) > 7 else "0"
        if shape_code == "40":  # Flow variable
            # If there's a valve with same ID, map it
            if var_id in valve_ids:
                valve_to_flow[var_id] = var_id

    # Get valve positions for proximity matching
    valve_positions = {}
    for line in parser.sketch_other:
        if line.startswith("11,"):
            parts = line.split(",")
            if len(parts) >= 5:
                try:
                    valve_id = int(parts[1])
                    x = int(parts[3])
                    y = int(parts[4])
                    valve_positions[valve_id] = (x, y)
                except ValueError:
                    continue

    # Method 2: Find valves that feed stocks, match to flows in stock equations
    # Build: valve → stock mapping
    valve_to_stock = {}
    for line in parser.sketch_other:
        if line.startswith("1,"):
            parts = line.split(",")
            if len(parts) >= 4:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])
                    # Valve → Stock
                    if from_id in valve_ids and to_id in var_ids:
                        if from_id not in valve_to_stock:
                            valve_to_stock[from_id] = []
                        valve_to_stock[from_id].append(to_id)
                except (ValueError, IndexError):
                    continue

    # For each valve that feeds stocks, find the flow from stock equations
    # Strategy: Find the flow that appears in ALL stocks (common flow)
    for valve_id, stock_ids in valve_to_stock.items():
        if valve_id in valve_to_flow:  # Already mapped
            continue

        # Find flows mentioned in each stock's equation
        flows_per_stock = []
        for stock_id in stock_ids:
            stock_var = parser.sketch_vars.get(stock_id)
            if not stock_var or stock_var.name not in parser.equations:
                continue

            equation = parser.equations[stock_var.name]
            equation_line = equation.equation_line

            # Find all flow variables in this stock's equation
            stock_flows = []
            for flow_id, flow_var in parser.sketch_vars.items():
                parts = flow_var.full_line.split(",")
                shape_code = parts[7] if len(parts) > 7 else "0"
                if shape_code == "40":  # Flow variable
                    flow_name = flow_var.name
                    if flow_name in equation_line or f'"{flow_name}"' in equation_line:
                        stock_flows.append(flow_id)

            if stock_flows:
                flows_per_stock.append(set(stock_flows))

        # Find common flow across all stocks
        if flows_per_stock:
            common_flows = flows_per_stock[0]
            for stock_flows in flows_per_stock[1:]:
                common_flows = common_flows & stock_flows

            candidate_flows = common_flows if common_flows else flows_per_stock[0]

            if candidate_flows:
                # Match valve to flow by proximity (handles both horizontal and vertical valves)
                if valve_id in valve_positions:
                    valve_x, valve_y = valve_positions[valve_id]
                    best_flow = None
                    min_distance = float('inf')

                    for flow_id in candidate_flows:
                        flow_var = parser.sketch_vars.get(flow_id)
                        if flow_var:
                            parts = flow_var.full_line.split(",")
                            if len(parts) >= 5:
                                flow_x = int(parts[3])
                                flow_y = int(parts[4])
                                # Calculate distance - handles both horizontal and vertical valves
                                # by prioritizing whichever axis is better aligned
                                dx = abs(valve_x - flow_x)
                                dy = abs(valve_y - flow_y)
                                # Weight the worse-aligned axis more heavily
                                distance = min(dx, dy) + max(dx, dy) * 2
                                if distance < min_distance:
                                    min_distance = distance
                                    best_flow = flow_id

                    if best_flow:
                        valve_to_flow[valve_id] = best_flow
                else:
                    # No position info, fall back to lowest ID
                    valve_to_flow[valve_id] = min(candidate_flows)

    # Process arrows and resolve valve endpoints
    for line in parser.sketch_other:
        # Format: 1,ArrowID,FromID,ToID,?,?,Field6,...
        # Field6=43 indicates POSITIVE polarity
        if line.startswith("1,"):
            parts = line.split(",")
            if len(parts) >= 7:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Resolve valve IDs to flow variable IDs
                    resolved_from = valve_to_flow.get(from_id, from_id)
                    resolved_to = valve_to_flow.get(to_id, to_id)

                    # Only include if at least one endpoint is a variable
                    # This captures Stock→Valve→Stock patterns
                    from_is_var = resolved_from in var_ids
                    to_is_var = resolved_to in var_ids

                    if not (from_is_var or to_is_var):
                        # Both are non-variables (clouds, etc.), skip
                        continue

                    # If one endpoint is still not a variable, skip this arrow
                    # (we only want variable-to-variable connections)
                    if not (from_is_var and to_is_var):
                        continue

                    field6 = parts[6]

                    # Determine polarity from field6
                    polarity = "POSITIVE" if field6 == "43" else "UNDECLARED"

                    connections.append({
                        "from": resolved_from,
                        "to": resolved_to,
                        "polarity": polarity
                    })
                except (ValueError, IndexError):
                    continue

    return connections


def _extract_stock_flow_connections(parser: MDLSurgicalParser) -> List[Dict]:
    """Extract stock-flow relationships from stock equations.

    In SD models, stocks accumulate flows. Direction depends on sign:
    - Negative flow (-Flow): Stock → Flow (outflow)
    - Positive flow (Flow): Flow → Stock (inflow)

    Example: "PR = f(-Merge, ...)" creates: PR → Merge (Stock → Flow, outflow)
    Example: "Source = f(Merge)" creates: Merge → Source (Flow → Stock, inflow)
    """
    connections = []

    # Build mapping of variable names to IDs and types
    # Handle duplicates: prioritize Flow (40) > Stock (3) > Auxiliary (8, 27)
    var_info = {}
    for var_id, var in parser.sketch_vars.items():
        parts = var.full_line.split(",")
        shape_code = parts[7] if len(parts) > 7 else "0"
        var_type = {"3": "Stock", "40": "Flow", "8": "Auxiliary", "27": "Auxiliary"}.get(shape_code, "Auxiliary")

        name = var.name
        if name not in var_info:
            var_info[name] = {"id": var_id, "type": var_type}
        else:
            # Handle duplicates: prefer Flow > Stock > Auxiliary
            priority_current = {"Flow": 3, "Stock": 2, "Auxiliary": 1}.get(var_type, 1)
            priority_existing = {"Flow": 3, "Stock": 2, "Auxiliary": 1}.get(var_info[name]["type"], 1)
            if priority_current > priority_existing:
                var_info[name] = {"id": var_id, "type": var_type}

    # Process stock equations
    for var_name in parser.equation_order:
        if var_name not in parser.equations or var_name not in var_info:
            continue

        # Only process stocks
        if var_info[var_name]["type"] != "Stock":
            continue

        stock_id = var_info[var_name]["id"]
        equation = parser.equations[var_name]
        equation_line = equation.equation_line

        # Parse "A FUNCTION OF(...)" to find flows and their signs
        if "A FUNCTION OF" in equation_line:
            start = equation_line.find("(")
            end = equation_line.rfind(")")
            if start != -1 and end != -1:
                deps_str = equation_line[start+1:end]

                # Clean up continuation lines
                deps_str = deps_str.replace("\\\n", " ").replace("\\n", " ").replace("\n", " ")
                deps_str = deps_str.replace("\t", " ").strip()

                # Parse dependencies respecting quotes
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

                if current.strip():
                    dep_parts.append(current.strip())

                # Check each dependency
                for dep in dep_parts:
                    if not dep:
                        continue

                    # Check for negative sign
                    is_negative = dep.startswith("-")
                    dep_name = dep.lstrip("-").strip().strip('"')

                    # Check if this is a flow variable
                    if dep_name in var_info and var_info[dep_name]["type"] == "Flow":
                        flow_id = var_info[dep_name]["id"]

                        if is_negative:
                            # Outflow: Stock → Flow
                            connections.append({
                                "from": stock_id,
                                "to": flow_id,
                                "polarity": "UNDECLARED"
                            })
                        else:
                            # Inflow: Flow → Stock
                            connections.append({
                                "from": flow_id,
                                "to": stock_id,
                                "polarity": "UNDECLARED"
                            })

    return connections


def _merge_connections(sketch_conns: List[Dict], stock_flow_conns: List[Dict]) -> List[Dict]:
    """Merge sketch and stock-flow connections (visual elements only).

    Deduplicates connections that appear in both sources.
    """
    # Create a dict indexed by (from, to) pair
    conn_dict = {}

    # Add sketch connections first
    for conn in sketch_conns:
        key = (conn["from"], conn["to"])
        conn_dict[key] = conn.copy()

    # Add stock-flow connections (may overlap with sketch)
    for conn in stock_flow_conns:
        key = (conn["from"], conn["to"])
        if key not in conn_dict:
            conn_dict[key] = conn.copy()

    return list(conn_dict.values())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON → Vensim MDL Generator (precise, rule-driven)

Based on GPT5's design with enhancements for color coding and theory enhancement workflow.

Inputs
------
variables.json:
  { "variables": [
      {"id": int, "name": str, "type": "Stock"|"Flow"|"Auxiliary",
       "x": int, "y": int, "width": int, "height": int,
       "color": {"border": "R-G-B"} (optional)}
  ]}

connections.json:
  { "connections": [
      {"id": str, "from_var": str, "to_var": str,
       "relationship": "positive"|"negative"|"undeclared",
       "color": {"line": "R-G-B"} (optional)}
  ]}

plumbing.json (optional):
  { "valves": [...], "clouds": [...], "flows": [...], "link_points": [...] }

Usage
-----
python generate_mdl.py --vars variables.json --conns connections.json --out model.mdl \
    [--plumbing plumbing.json] [--with-control] [--markers std|alt]
"""

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any


EQ_INDENT = "\t"  # Tab for equations

HEADER_STD = "\\\\\\---/// Sketch information - do not modify anything except names\n"
HEADER_ALT = "--/// Sketch information - do not modify anything except names\n"
FOOTER_STD = "///---\\\\\\\n"
FOOTER_ALT = "///---\\\n"

VIEW_HEADER_COMMON = (
    "V300  Do not put anything below this section - it will be ignored\n"
    "*View 1\n"
    "$-1--1--1,0,|12||-1--1--1|-1--1--1|-1--1--1|-1--1--1|-1--1--1|96,96,67,2\n"
)

CONTROL_BLOCK = (
    "********************************************************\n"
    "\t.Control\n"
    "********************************************************~\n"
    "\t\tSimulation Control Parameters\n"
    "\t|\n\n"
    "FINAL TIME  = 100\n"
    "\t~\tMonth\n"
    "\t~\tThe final time for the simulation.\n"
    "\t|\n\n"
    "INITIAL TIME  = 0\n"
    "\t~\tMonth\n"
    "\t~\tThe initial time for the simulation.\n"
    "\t|\n\n"
    "SAVEPER  = \n"
    "        TIME STEP\n"
    "\t~\tMonth [0,?]\n"
    "\t~\tThe frequency with which output is stored.\n"
    "\t|\n\n"
    "TIME STEP  = 1\n"
    "\t~\tMonth [0,?]\n"
    "\t~\tThe time step for the simulation.\n"
    "\t|\n\n"
)


def quote_name(name: str) -> str:
    """Quote variable name if it contains special characters."""
    needs = any(c in name for c in [',', '(', ')', '|', '"']) or (name != name.strip()) or ('\n' in name)
    if needs:
        return '"' + name.replace('"', '""') + '"'
    return name


def load_json(path: str) -> Dict[str, Any]:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_var_maps(vars_json) -> Tuple[Dict[str, int], Dict[int, str]]:
    """Build name ↔ ID mappings."""
    names = [v["name"] for v in vars_json["variables"]]
    ids = [v["id"] for v in vars_json["variables"]]

    if len(names) != len(set(names)):
        dups = sorted({n for n in names if names.count(n) > 1})
        raise ValueError(f"Duplicate variable names: {dups}")

    if len(ids) != len(set(ids)):
        dups = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"Duplicate variable ids: {dups}")

    name2id = {v["name"]: v["id"] for v in vars_json["variables"]}
    id2name = {v["id"]: v["name"] for v in vars_json["variables"]}
    return name2id, id2name


def deps_for(var_name: str, conns: Dict) -> str:
    """Get dependencies for a variable from connections."""
    inbound = [c for c in conns["connections"] if c["to_var"] == var_name]
    items = []
    for c in inbound:
        rel = c.get("relationship", "undeclared")
        sign = '-' if rel == "negative" else ''  # No + for positive
        items.append(f"{sign}{quote_name(c['from_var'])}")
    return ",".join(items) if items else ""


def build_equations(vars_json: Dict, conns_json: Dict) -> str:
    """Build equation section."""
    out = []
    for v in sorted(vars_json["variables"], key=lambda x: (x.get("name", ""))):
        lhs = quote_name(v["name"])
        rhs = deps_for(v["name"], conns_json)

        # Get units and description if provided
        units = v.get("units", "")
        desc = v.get("description", "")

        out.append(f"{lhs}  = A FUNCTION OF( {rhs})\n")
        out.append(f"{EQ_INDENT}~\t{units}\n")
        out.append(f"{EQ_INDENT}~\t{desc}\t|\n\n")

    return "".join(out)


def get_type_code(var_type: str) -> int:
    """Get Vensim type code for variable type."""
    if var_type == "Stock":
        return 3
    elif var_type == "Flow":
        return 40
    else:  # Auxiliary
        return 8


def build_type10(v: Dict) -> str:
    """Build Type 10 variable line."""
    type_code = get_type_code(v.get("type", "Auxiliary"))

    # Check for color
    color = v.get("color", {}).get("border")

    if color:
        # Extended format with color (27 fields)
        # Fields: 10,id,name,x,y,width,height,type,3,0,1,-1,1,0,0,border_color,fill_color,|||text_color,0,0,0,0,0,0
        return (
            f"10,{v['id']},{quote_name(v['name'])},"
            f"{v['x']},{v['y']},{v['width']},{v['height']},"
            f"{type_code},3,0,1,-1,1,0,0,{color},0-0-0,|||0-0-0,0,0,0,0,0,0\n"
        )
    else:
        # Standard format (20 fields)
        return (
            f"10,{v['id']},{quote_name(v['name'])},"
            f"{v['x']},{v['y']},{v['width']},{v['height']},"
            f"{type_code},3,0,0,-1,0,0,0,0,0,0,0,0,0\n"
        )


def build_type11(valve: Dict) -> str:
    """Build Type 11 flow valve line."""
    return (
        f"11,{valve['id']},0,"
        f"{valve['x']},{valve['y']},{valve['w']},{valve['h']},"
        "34,3,0,0,1,0,0,0,0,0,0,0,0,0\n"
    )


def build_type12(cloud: Dict) -> str:
    """Build Type 12 cloud line."""
    code = cloud.get("code", 48)
    return (
        f"12,{cloud['id']},{code},"
        f"{cloud['x']},{cloud['y']},{cloud['w']},{cloud['h']},"
        "0,3,0,0,-1,0,0,0,0,0,0,0,0,0\n"
    )


def link_poly(points: List) -> str:
    """Format link polyline points."""
    if points and len(points) > 0:
        coords = "".join(f"({x},{y})" for (x, y) in points)
        return f"|{coords}|"
    return "|(0,0)|"  # Default if no points provided


def build_type1(conn_id: str, from_id: int, to_id: int, points=None, color=None) -> str:
    """Build Type 1 connection line."""
    if color:
        # Connection with color - field 8=1 to enable color, field 9=64 for colored lines
        # Fields: 1,id,from,to,f4,f5,f6,f7,color_enable,style,f10,color,|||label,polarity|points|
        return (
            f"1,{conn_id},{from_id},{to_id},0,0,0,0,1,64,0,{color},|||0-0-0,1{link_poly(points)}\n"
        )
    else:
        # Standard connection
        return (
            f"1,{conn_id},{from_id},{to_id},0,0,0,22,0,192,0,-1--1--1,,1{link_poly(points)}\n"
        )


def resolve_endpoint(ep: Dict, name2id: Dict, valves_by_id: Dict, clouds_by_id: Dict) -> int:
    """Resolve endpoint reference to ID."""
    kind = ep["kind"]
    ref = ep["ref"]

    if kind == "stock" or kind == "aux":
        if isinstance(ref, int):
            return ref
        else:
            # Name reference
            return name2id[ref]
    elif kind == "valve":
        if isinstance(ref, int):
            return ref
        else:
            # Map by var_name
            for v in valves_by_id.values():
                if v["var_name"] == ref:
                    return v["id"]
            raise KeyError(f"Unknown valve by var_name: {ref}")
    elif kind == "cloud":
        if isinstance(ref, int):
            return ref
        else:
            raise KeyError("cloud endpoints must use numeric id")
    else:
        raise KeyError(f"Unknown endpoint kind: {kind}")


def compile_link_points(geo_list: List) -> Dict:
    """Return dict[(from_id, to_id)] -> points list."""
    d = {}
    if not geo_list:
        return d
    for item in geo_list:
        key = (item["from_id"], item["to_id"])
        d[key] = [tuple(p) for p in item.get("points", [])]
    return d


def generate_mdl(vars_json: Dict, conns_json: Dict, plumbing_json: Dict,
                 with_control: bool, markers: str) -> str:
    """Generate MDL from JSON inputs."""
    name2id, id2name = build_var_maps(vars_json)

    mdl = []
    mdl.append("{UTF-8}\n")
    mdl.append(build_equations(vars_json, conns_json))

    if with_control:
        mdl.append(CONTROL_BLOCK)

    # Sketch header
    header = HEADER_STD if markers == "std" else HEADER_ALT
    footer = FOOTER_STD if markers == "std" else FOOTER_ALT
    mdl.append(header)
    mdl.append(VIEW_HEADER_COMMON)

    # Collect all sketch elements with their IDs
    sketch_elements = []

    # Add variables (Type 10)
    for v in vars_json["variables"]:
        sketch_elements.append({
            'id': v['id'],
            'type': 10,
            'content': build_type10(v)
        })

    valves = []
    clouds = []
    flows = []
    link_geom = {}
    valves_by_id = {}
    clouds_by_id = {}

    if plumbing_json:
        valves = plumbing_json.get("valves", [])
        clouds = plumbing_json.get("clouds", [])
        flows = plumbing_json.get("flows", [])
        link_geom = compile_link_points(plumbing_json.get("link_points", []))

        # Add valves (Type 11)
        for valve in valves:
            valves_by_id[valve["id"]] = valve
            sketch_elements.append({
                'id': valve['id'],
                'type': 11,
                'content': build_type11(valve)
            })

        # Add clouds (Type 12)
        for cloud in clouds:
            clouds_by_id[cloud["id"]] = cloud
            sketch_elements.append({
                'id': cloud['id'],
                'type': 12,
                'content': build_type12(cloud)
            })

    # Build map of valve_id -> flow_connections for that valve
    # Only include connections where field3 is 100 or 4 (actual flow pipes, not influence arrows)
    valve_flow_map = {}
    if plumbing_json:
        raw_flow_conns = plumbing_json.get('flow_connections', [])
        for conn in raw_flow_conns:
            from_id = conn['from_id']
            # Flow pipes have the valve as from_id and field3=100 or 4
            params = conn.get('params', {})
            field3 = params.get('field3', '0')
            if field3 in ['100', '4']:
                # This is a flow pipe from a valve
                if from_id not in valve_flow_map:
                    valve_flow_map[from_id] = []
                valve_flow_map[from_id].append(conn)

    # Sort all sketch elements by ID and emit them
    # For valves (type 11), emit their flow connections BEFORE the valve
    for element in sorted(sketch_elements, key=lambda x: x['id']):
        # If this is a valve, emit its flow connections BEFORE the valve
        if element['type'] == 11 and element['id'] in valve_flow_map:
            for conn in valve_flow_map[element['id']]:
                from_id = conn['from_id']
                to_id = conn['to_id']
                conn_id = conn.get('id', str(element['id'] * 100))  # Temp ID
                points = conn.get('points') or link_geom.get((from_id, to_id))

                # Use preserved parameters
                if 'params' in conn:
                    params = conn['params']
                    mdl.append(f"1,{conn_id},{from_id},{to_id},{params['field3']},{params['field4']},{params['field5']},{params['field6']},0,192,0,-1--1--1,,1{link_poly(points)}\n")

        # Now emit the element itself
        mdl.append(element['content'])

    # Collect all used IDs for connection numbering
    used_ids = {elem['id'] for elem in sketch_elements}

    # Assign connection ids after max used id
    next_conn_id = max(used_ids) + 1 if used_ids else 1

    # Influence links (node→node)
    for c in conns_json["connections"]:
        # Skip equation-sourced connections (they're in equations already)
        if c.get("source") == "equation":
            continue

        f_id = name2id[c["from_var"]]
        t_id = name2id[c["to_var"]]

        # Use points from connection if available, otherwise check link_geom
        points = c.get('points') or link_geom.get((f_id, t_id))

        # Check for custom color first
        color = c.get("color", {}).get("line")

        if color:
            # If there's a color, use special color format
            # Field 8 (color_enable) must be 1, field 9 must be 64 for colored lines
            mdl.append(f"1,{c.get('id', str(next_conn_id))},{f_id},{t_id},0,0,0,0,1,64,0,{color},|||0-0-0,1{link_poly(points)}\n")
        elif 'params' in c:
            # Use preserved parameters if no color override
            params = c['params']
            mdl.append(f"1,{c.get('id', str(next_conn_id))},{f_id},{t_id},{params['field3']},{params['field4']},{params['field5']},{params['field6']},0,192,0,-1--1--1,,1{link_poly(points)}\n")
        else:
            # Default connection
            mdl.append(build_type1(c.get("id", str(next_conn_id)), f_id, t_id, points, color))
        next_conn_id += 1

    # Emit non-flow connections from flow_connections (valve-to-valve influence arrows)
    if plumbing_json:
        raw_flow_conns = plumbing_json.get('flow_connections', [])
        for conn in raw_flow_conns:
            params = conn.get('params', {})
            field3 = params.get('field3', '0')
            # Only emit if NOT a true flow pipe (field3 not 100 or 4)
            if field3 not in ['100', '4']:
                from_id = conn['from_id']
                to_id = conn['to_id']
                conn_id = conn.get('id', str(next_conn_id))
                points = conn.get('points') or link_geom.get((from_id, to_id))

                mdl.append(f"1,{conn_id},{from_id},{to_id},{params['field3']},{params['field4']},{params['field5']},{params['field6']},0,192,0,-1--1--1,,1{link_poly(points)}\n")
                if 'id' not in conn:
                    next_conn_id += 1

    mdl.append(footer)

    # Footer section (minimal Vensim footer)
    mdl.append(":L<%^E!@\n")
    mdl.append("5:Time\n")
    mdl.append("19:67,0\n")
    mdl.append("24:0\n")
    mdl.append("25:0\n")
    mdl.append("26:0\n")

    return "".join(mdl)


def main():
    """CLI entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--vars", required=True, help="variables.json")
    ap.add_argument("--conns", required=True, help="connections.json")
    ap.add_argument("--out", required=True, help="output .mdl path")
    ap.add_argument("--plumbing", required=False, help="plumbing.json with valves/clouds/flows/geometry")
    ap.add_argument("--with-control", action="store_true", help="emit control banner")
    ap.add_argument("--markers", choices=["std", "alt"], default="std", help="sketch header/footer pair")
    args = ap.parse_args()

    vars_json = load_json(args.vars)
    conns_json = load_json(args.conns)
    plumbing_json = load_json(args.plumbing) if args.plumbing else None

    mdl_text = generate_mdl(vars_json, conns_json, plumbing_json, args.with_control, args.markers)
    Path(args.out).write_text(mdl_text, encoding="utf-8")
    print(f"Generated MDL: {args.out}")


if __name__ == "__main__":
    main()
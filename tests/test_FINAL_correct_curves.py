#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FINAL SOLUTION: Generate curves with the correct Vensim format.

Key discovery: Field 10 must be 64 for curves!
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.edge_routing import route_all_connections


def extract_variables_from_mdl(mdl_path):
    """Extract variables with positions from MDL file."""
    content = Path(mdl_path).read_text(encoding='utf-8')
    lines = content.split('\n')

    variables = []
    for line in lines:
        if line.startswith('10,'):
            parts = line.split(',')
            if len(parts) > 7:
                try:
                    var_id = int(parts[1])
                    var_name = parts[2].strip()
                    if var_name.startswith('"') and var_name.endswith('"'):
                        var_name = var_name[1:-1].replace('""', '"')
                    x = int(parts[3])
                    y = int(parts[4])
                    width = int(parts[5])
                    height = int(parts[6])

                    variables.append({
                        'id': var_id,
                        'name': var_name,
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    })
                except (ValueError, IndexError):
                    pass

    return variables


def extract_connections_from_mdl(mdl_path):
    """Extract connections from MDL file."""
    content = Path(mdl_path).read_text(encoding='utf-8')
    lines = content.split('\n')

    connections = []
    for line in lines:
        if line.startswith('1,'):
            parts = line.split(',')
            if len(parts) > 3:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])
                    connections.append({
                        'from_id': from_id,
                        'to_id': to_id
                    })
                except (ValueError, IndexError):
                    pass

    return connections


def update_arrow_waypoints_FINAL(lines, waypoint_map):
    """
    FINAL CORRECT VERSION: Generate curves that actually work in Vensim.

    Key changes:
    1. Set field 5 to 1 for curved lines
    2. Set field 10 to 64 (THIS IS THE CRITICAL FIX!)
    3. Use SINGLE control point
    """
    new_lines = []
    arrows_curved = 0
    arrows_straight = 0

    for line in lines:
        if line.startswith('1,'):  # Arrow line
            parts = line.split(',')

            if len(parts) > 10:  # Need at least 11 fields to set field 10
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Look up waypoints
                    conn_key = f"{from_id}_{to_id}"
                    waypoints = waypoint_map.get(conn_key, [])

                    # Find where waypoints start
                    waypoint_start_idx = None
                    for i, part in enumerate(parts):
                        if '1|(' in part:
                            waypoint_start_idx = i
                            break

                    if waypoint_start_idx is not None:
                        # Keep everything before waypoints
                        parts = parts[:waypoint_start_idx]

                        if waypoints:
                            # FINAL CORRECT FORMAT for curved line:

                            # 1. Set field 5 (index 4) to 1
                            if len(parts) > 4:
                                parts[4] = '1'

                            # 2. Set field 10 (index 9) to 64 - THIS IS THE KEY!
                            if len(parts) > 9:
                                parts[9] = '64'

                            # 3. Use middle waypoint (more offset from straight line)
                            if len(waypoints) >= 2:
                                control_x, control_y = waypoints[len(waypoints) // 2]
                            else:
                                control_x, control_y = waypoints[0]

                            # 4. Format as SINGLE control point
                            control_point = f"1|({int(control_x)},{int(control_y)})|"
                            parts.append(control_point)

                            arrows_curved += 1
                            print(f"    ✓ CURVED arrow {from_id}→{to_id}: field10=64, control point ({int(control_x)}, {int(control_y)})")
                        else:
                            # Straight line: field 5 = 0, field 10 = 192, waypoint = (0,0)
                            if len(parts) > 4:
                                parts[4] = '0'
                            if len(parts) > 9:
                                parts[9] = '192'
                            waypoint_str = '1|(0,0)|'
                            parts.append(waypoint_str)
                            arrows_straight += 1

                        line = ','.join(parts)

                except (ValueError, IndexError) as e:
                    print(f"    ✗ Error parsing arrow line: {e}")
                    pass

        new_lines.append(line)

    return new_lines, arrows_curved, arrows_straight


def test_final_solution():
    """Test curve generation with FINAL CORRECT Vensim format."""
    print("="*60)
    print("FINAL SOLUTION: CORRECT VENSIM CURVE FORMAT")
    print("Field 10 = 64 is the KEY!")
    print("="*60)

    mdl_path = Path("projects/sd_test/mdl/enhanced/latest/test_enhanced.mdl")

    if not mdl_path.exists():
        print(f"\n✗ MDL file not found: {mdl_path}")
        return False

    print(f"\n1. Reading MDL file: {mdl_path}")

    # Extract variables and connections
    variables = extract_variables_from_mdl(mdl_path)
    connections = extract_connections_from_mdl(mdl_path)

    print(f"   Variables: {len(variables)}")
    print(f"   Connections: {len(connections)}")

    # Calculate waypoints
    print(f"\n2. Calculating waypoints using edge routing...")
    waypoint_map = route_all_connections(variables, connections)

    with_waypoints = sum(1 for w in waypoint_map.values() if len(w) > 0)
    print(f"   Connections needing curves: {with_waypoints}")

    # Apply waypoints in FINAL CORRECT format
    print(f"\n3. Applying waypoints in FINAL CORRECT format...")
    print(f"   (Field 5 = 1, Field 10 = 64, single control point)\n")

    content = mdl_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    new_lines, curved, straight = update_arrow_waypoints_FINAL(lines, waypoint_map)

    print(f"\n   Arrows with curves: {curved}")
    print(f"   Arrows left straight: {straight}")

    # Write output
    output_path = Path("tests/test_output_FINAL_WORKING.mdl")
    output_path.write_text('\n'.join(new_lines), encoding='utf-8')

    print(f"\n4. Wrote output to: {output_path}")

    print(f"\n" + "="*60)
    print("RESULT:")
    print("="*60)
    print(f"✅ Generated {curved} curved arrows with field 10 = 64")
    print(f"\n🎯 This should FINALLY show curves in Vensim!")
    print(f"\nFile: {output_path}")
    print(f"\nPlease open in Vensim to verify all {curved} arrows are curved!")

    return True


if __name__ == '__main__':
    test_final_solution()

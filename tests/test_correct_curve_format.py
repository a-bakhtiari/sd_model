#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test generating curves in the CORRECT Vensim format.

Based on user's manual edit, we now know:
- Field 5 must be set to 1 for curved lines
- Use a SINGLE control point, not multiple waypoints
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


def update_arrow_waypoints_CORRECT_FORMAT(lines, waypoint_map):
    """
    CORRECTED VERSION: Generate curves in Vensim's actual format.

    Key changes:
    1. Set field 5 to 1 for curved lines
    2. Use SINGLE control point, not multiple waypoints
    """
    new_lines = []
    arrows_curved = 0
    arrows_straight = 0

    for line in lines:
        if line.startswith('1,'):  # Arrow line
            parts = line.split(',')

            if len(parts) > 3:
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
                            # CORRECT FORMAT for curved line:
                            # 1. Set field 5 (index 4) to 1
                            parts[4] = '1'

                            # 2. Calculate SINGLE control point
                            # Use the middle waypoint or midpoint of path
                            if len(waypoints) == 1:
                                control_x, control_y = waypoints[0]
                            else:
                                # Use midpoint between first and last waypoint
                                control_x = (waypoints[0][0] + waypoints[-1][0]) / 2
                                control_y = (waypoints[0][1] + waypoints[-1][1]) / 2

                            # 3. Format as SINGLE control point
                            control_point = f"1|({int(control_x)},{int(control_y)})|"
                            parts.append(control_point)

                            arrows_curved += 1
                            print(f"    ✓ CURVED arrow {from_id}→{to_id}: control point at ({int(control_x)}, {int(control_y)})")
                        else:
                            # Straight line: field 5 = 0, waypoint = (0,0)
                            if len(parts) > 4:
                                parts[4] = '0'
                            waypoint_str = '1|(0,0)|'
                            parts.append(waypoint_str)
                            arrows_straight += 1

                        line = ','.join(parts)

                except (ValueError, IndexError) as e:
                    print(f"    ✗ Error parsing arrow line: {e}")
                    pass

        new_lines.append(line)

    return new_lines, arrows_curved, arrows_straight


def test_correct_format():
    """Test curve generation with CORRECT Vensim format."""
    print("="*60)
    print("TESTING CORRECT VENSIM CURVE FORMAT")
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

    # Apply waypoints in CORRECT format
    print(f"\n3. Applying waypoints in CORRECT Vensim format...")
    print(f"   (Field 5 = 1, single control point)\n")

    content = mdl_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    new_lines, curved, straight = update_arrow_waypoints_CORRECT_FORMAT(lines, waypoint_map)

    print(f"\n   Arrows with curves: {curved}")
    print(f"   Arrows left straight: {straight}")

    # Write output
    output_path = Path("tests/test_output_CORRECT_FORMAT.mdl")
    output_path.write_text('\n'.join(new_lines), encoding='utf-8')

    print(f"\n4. Wrote output to: {output_path}")

    print(f"\n" + "="*60)
    print("RESULT:")
    print("="*60)
    print(f"✓ Generated {curved} curved arrows")
    print(f"  - Field 5 set to 1 (curve flag)")
    print(f"  - Single control point (not multiple waypoints)")
    print(f"\nNow open this file in Vensim to verify curves appear!")
    print(f"File: {output_path}")

    return True


if __name__ == '__main__':
    test_correct_format()

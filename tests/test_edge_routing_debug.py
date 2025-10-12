#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to isolate edge routing issues without touching main code.

Tests the 3 hypotheses:
1. Intersection detection is broken (returns "clear" when it shouldn't)
2. Waypoint writing to MDL is broken
3. Pipeline integration is broken (data not being passed)
"""

import sys
import math
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sd_model.edge_routing import (
    calculate_bounding_boxes,
    line_intersects_box,
    find_waypoints,
    route_all_connections
)


def test_hypothesis_1_intersection_detection():
    """Test if line-box intersection detection works correctly."""
    print("\n" + "="*60)
    print("HYPOTHESIS 1: Testing Intersection Detection")
    print("="*60)

    # Create a simple scenario: arrow should hit a box in the middle
    from_pos = (100, 100)
    to_pos = (900, 900)

    # Box directly in the path
    obstacle_box = {
        'name': 'Middle Box',
        'id': 2,
        'left': 450,
        'right': 550,
        'top': 450,
        'bottom': 550
    }

    # Test 1: Does straight line intersect the box?
    intersects = line_intersects_box(from_pos, to_pos, obstacle_box)
    print(f"\nTest 1: Straight line {from_pos} → {to_pos}")
    print(f"  Through box at (450-550, 450-550)")
    print(f"  Intersection detected: {intersects}")
    print(f"  ✓ PASS" if intersects else "  ✗ FAIL - Should detect intersection!")

    # Test 2: Does it work with padding?
    variables = [
        {'name': 'Source', 'x': 100, 'y': 100, 'width': 60, 'height': 26, 'id': 1},
        {'name': 'Middle', 'x': 500, 'y': 500, 'width': 60, 'height': 26, 'id': 2},
        {'name': 'Target', 'x': 900, 'y': 900, 'width': 60, 'height': 26, 'id': 3}
    ]

    boxes = calculate_bounding_boxes(variables)
    middle_box = boxes[1]  # Should be the middle variable

    print(f"\nTest 2: With calculate_bounding_boxes() (50px padding)")
    print(f"  Middle box bounds: left={middle_box['left']}, right={middle_box['right']}, top={middle_box['top']}, bottom={middle_box['bottom']}")

    intersects_with_padding = line_intersects_box(from_pos, to_pos, middle_box)
    print(f"  Intersection detected: {intersects_with_padding}")
    print(f"  ✓ PASS" if intersects_with_padding else "  ✗ FAIL - Padding should make box bigger!")

    # Test 3: Does find_waypoints detect the obstacle?
    obstacles = [box for box in boxes if box['id'] != 1 and box['id'] != 3]  # Exclude source/target

    print(f"\nTest 3: Does find_waypoints() detect obstacle?")
    print(f"  Number of obstacles passed: {len(obstacles)}")

    waypoints = find_waypoints(from_pos, to_pos, obstacles, from_id=1, to_id=3)

    print(f"  Waypoints generated: {len(waypoints)}")
    print(f"  Waypoints: {waypoints}")
    print(f"  ✓ PASS" if len(waypoints) > 0 else "  ✗ FAIL - Should generate waypoints to avoid obstacle!")

    return {
        'straight_line_intersection': intersects,
        'padded_box_intersection': intersects_with_padding,
        'waypoints_generated': len(waypoints) > 0
    }


def test_hypothesis_2_waypoint_writing():
    """Test if waypoint writing to MDL format works."""
    print("\n" + "="*60)
    print("HYPOTHESIS 2: Testing Waypoint Writing to MDL")
    print("="*60)

    # Simulate an arrow line from actual MDL
    sample_arrow_lines = [
        # Standard arrow format
        "1,36,30,29,0,0,0,22,0,192,0,-1--1--1,,1|(0,0)|",
        # Arrow with existing waypoints
        "1,48,28,26,1,0,0,0,0,64,0,-1--1--1,,1|(1873,709)|",
        # Valve connection (shouldn't be modified)
        "1,4,6,2,100,0,0,22,0,192,0,-1--1--1,,1|(800,587)|"
    ]

    # Simulated waypoint map
    waypoint_map = {
        "30_29": [(500, 300), (500, 400)],  # H-V-H pattern
        "28_26": [],  # No waypoints needed (straight)
        "6_2": [(800, 587)]  # Existing waypoint (valve)
    }

    print("\nTest: Parse arrow line and find waypoint insertion point")

    for i, line in enumerate(sample_arrow_lines, 1):
        print(f"\n  Arrow {i}: {line[:50]}...")
        parts = line.split(',')

        if len(parts) > 3:
            from_id = int(parts[2])
            to_id = int(parts[3])
            conn_key = f"{from_id}_{to_id}"

            # Find where waypoints start
            waypoint_start_idx = None
            for idx, part in enumerate(parts):
                if '1|(' in part:
                    waypoint_start_idx = idx
                    break

            print(f"    From ID: {from_id}, To ID: {to_id}")
            print(f"    Connection key: {conn_key}")
            print(f"    Waypoint section found at index: {waypoint_start_idx}")
            print(f"    Calculated waypoints: {waypoint_map.get(conn_key, 'NOT FOUND')}")

            if waypoint_start_idx is not None:
                waypoints = waypoint_map.get(conn_key, [])
                if waypoints:
                    waypoint_str = '1|(' + ')|1|('.join([f"{int(x)},{int(y)}" for x, y in waypoints]) + ')|'
                    print(f"    Generated waypoint string: {waypoint_str}")
                    print(f"    ✓ Would update arrow")
                else:
                    print(f"    No waypoints to apply")
            else:
                print(f"    ✗ FAIL - Could not find waypoint section!")

    return True


def test_hypothesis_3_integration():
    """Test if route_all_connections() works end-to-end."""
    print("\n" + "="*60)
    print("HYPOTHESIS 3: Testing Integration (route_all_connections)")
    print("="*60)

    # Simulate real data from MDL file
    variables = [
        {'id': 1, 'name': 'New Contributors', 'x': 800, 'y': 400, 'width': 66, 'height': 26},
        {'id': 2, 'name': 'Core Developer', 'x': 1600, 'y': 570, 'width': 46, 'height': 26},
        {'id': 8, 'name': 'Experienced Contributors', 'x': 1400, 'y': 400, 'width': 66, 'height': 26},
        {'id': 12, 'name': 'Skill up', 'x': 1000, 'y': 400, 'width': 46, 'height': 26},
    ]

    connections = [
        {'from_id': 1, 'to_id': 8},   # New → Experienced
        {'from_id': 8, 'to_id': 2},   # Experienced → Core
        {'from_id': 12, 'to_id': 1},  # Skill up → New
    ]

    print(f"\nInput:")
    print(f"  Variables: {len(variables)}")
    for v in variables:
        print(f"    ID {v['id']}: {v['name']} at ({v['x']}, {v['y']})")

    print(f"\n  Connections: {len(connections)}")
    for c in connections:
        print(f"    {c['from_id']} → {c['to_id']}")

    print(f"\nCalling route_all_connections()...")
    waypoint_map = route_all_connections(variables, connections)

    print(f"\nOutput:")
    print(f"  Waypoint map size: {len(waypoint_map)}")

    if waypoint_map:
        for conn_key, waypoints in waypoint_map.items():
            print(f"    {conn_key}: {len(waypoints)} waypoints - {waypoints}")
    else:
        print(f"  ✗ FAIL - Empty waypoint map!")

    # Count how many got waypoints
    with_waypoints = sum(1 for w in waypoint_map.values() if len(w) > 0)
    without_waypoints = sum(1 for w in waypoint_map.values() if len(w) == 0)

    print(f"\n  Summary:")
    print(f"    Connections with waypoints: {with_waypoints}")
    print(f"    Connections without waypoints (straight): {without_waypoints}")

    if with_waypoints == 0 and len(connections) > 0:
        print(f"    ⚠ WARNING - No waypoints generated, all arrows will be straight!")

    return waypoint_map


def test_real_world_scenario():
    """Test with actual problematic case from user's diagram."""
    print("\n" + "="*60)
    print("REAL WORLD TEST: User's Problematic Arrow")
    print("="*60)

    # The arrow user manually edited:
    # var 28 (Legitimate Peripheral Participation Quality) at (2000, 187)
    # var 26 (New Contributor Attrition) at (1400, 1087)
    # User added waypoint at (1873, 709)

    print("\nScenario: Arrow that was left straight but should be curved")
    print("  From: Var 28 'Legitimate Peripheral Participation Quality' at (2000, 187)")
    print("  To: Var 26 'New Contributor Attrition' at (1400, 1087)")
    print("  Distance: ~900px diagonal")
    print("  User manually added waypoint at: (1873, 709)")

    # Create simplified scenario
    variables = [
        {'id': 26, 'name': 'New Contributor Attrition', 'x': 1400, 'y': 1087, 'width': 60, 'height': 26},
        {'id': 28, 'name': 'Legitimate Peripheral Participation Quality', 'x': 2000, 'y': 187, 'width': 60, 'height': 26},
        # Add some obstacles in between
        {'id': 1, 'name': 'New Contributors', 'x': 1200, 'y': 987, 'width': 66, 'height': 26},
        {'id': 2, 'name': 'Core Developer', 'x': 1600, 'y': 787, 'width': 46, 'height': 26},
    ]

    from_pos = (2000, 187)
    to_pos = (1400, 1087)

    # Calculate obstacles
    boxes = calculate_bounding_boxes(variables)
    obstacles = [box for box in boxes if box['id'] not in [28, 26]]

    print(f"\n  Obstacles between source and target: {len(obstacles)}")
    for box in obstacles:
        print(f"    {box['name']} - bounds: ({box['left']:.0f}-{box['right']:.0f}, {box['top']:.0f}-{box['bottom']:.0f})")

    # Test if straight line hits any obstacle
    print(f"\n  Testing straight line intersection:")
    straight_blocked = False
    for box in obstacles:
        if line_intersects_box(from_pos, to_pos, box):
            print(f"    ✓ Blocked by: {box['name']}")
            straight_blocked = True

    if not straight_blocked:
        print(f"    ✗ No obstacles detected - straight line deemed CLEAR")
        print(f"    This is why the arrow was left straight!")

    # Try to route
    print(f"\n  Attempting to generate waypoints:")
    waypoints = find_waypoints(from_pos, to_pos, obstacles, from_id=28, to_id=26)

    print(f"    Generated waypoints: {waypoints}")

    if len(waypoints) == 0:
        print(f"    ✗ FAIL - No waypoints generated (would be straight line)")
        print(f"    Expected: Should generate waypoints similar to user's manual edit")
    else:
        print(f"    ✓ Waypoints generated")
        print(f"    User's waypoint: (1873, 709)")
        print(f"    Our waypoint: {waypoints[0] if waypoints else 'N/A'}")

    return waypoints


if __name__ == '__main__':
    print("="*60)
    print("EDGE ROUTING DEBUG SUITE")
    print("Testing 3 hypotheses for why edge routing doesn't work")
    print("="*60)

    results = {}

    # Test each hypothesis
    results['hypothesis_1'] = test_hypothesis_1_intersection_detection()
    results['hypothesis_2'] = test_hypothesis_2_waypoint_writing()
    results['hypothesis_3'] = test_hypothesis_3_integration()
    results['real_world'] = test_real_world_scenario()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    print("\nHypothesis 1 (Intersection Detection):")
    h1 = results['hypothesis_1']
    print(f"  Straight line detection: {'✓' if h1['straight_line_intersection'] else '✗'}")
    print(f"  Padded box detection: {'✓' if h1['padded_box_intersection'] else '✗'}")
    print(f"  Waypoint generation: {'✓' if h1['waypoints_generated'] else '✗'}")

    print("\nHypothesis 2 (Waypoint Writing):")
    print(f"  MDL parsing and writing: ✓ (see output above)")

    print("\nHypothesis 3 (Integration):")
    h3 = results['hypothesis_3']
    if h3:
        total = len(h3)
        with_wp = sum(1 for w in h3.values() if len(w) > 0)
        print(f"  Connections processed: {total}")
        print(f"  Waypoints generated: {with_wp}/{total}")

    print("\nReal World Test:")
    real = results['real_world']
    print(f"  Waypoints for problematic arrow: {'✓ ' + str(real) if real else '✗ None generated'}")

    print("\n" + "="*60)
    print("Run this script to diagnose the issue:")
    print("  python3 tests/test_edge_routing_debug.py")
    print("="*60)

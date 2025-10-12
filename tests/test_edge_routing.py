#!/usr/bin/env python3
"""
Test edge routing module
"""

from src.sd_model.edge_routing import (
    calculate_bounding_boxes,
    line_intersects_box,
    find_waypoints,
    route_all_connections
)


def test_bounding_boxes():
    """Test bounding box calculation."""
    variables = [
        {'id': 1, 'name': 'Var1', 'x': 100, 'y': 100, 'width': 60, 'height': 26},
        {'id': 2, 'name': 'Var2', 'x': 300, 'y': 100, 'width': 60, 'height': 26},
    ]

    boxes = calculate_bounding_boxes(variables)

    assert len(boxes) == 2
    assert boxes[0]['left'] == 100 - 30 - 30  # x - width/2 - padding
    assert boxes[0]['right'] == 100 + 30 + 30  # x + width/2 + padding
    print("✓ Bounding box calculation works")


def test_line_intersection():
    """Test line-box intersection detection."""
    box = {
        'left': 90,
        'right': 110,
        'top': 90,
        'bottom': 110
    }

    # Line passes through box
    assert line_intersects_box((50, 100), (150, 100), box) == True

    # Line misses box
    assert line_intersects_box((50, 50), (150, 50), box) == False

    print("✓ Line intersection detection works")


def test_waypoint_calculation():
    """Test waypoint calculation with obstacle."""
    # Variable at (100, 100) blocking straight path from (50, 100) to (150, 100)
    from_xy = (50, 100)
    to_xy = (150, 100)

    obstacles = [{
        'id': 99,
        'left': 70,
        'right': 130,
        'top': 80,
        'bottom': 120
    }]

    waypoints = find_waypoints(from_xy, to_xy, obstacles)

    # Should have waypoints to route around obstacle
    assert len(waypoints) > 0
    print(f"✓ Waypoint calculation works, generated {len(waypoints)} waypoints")


def test_clear_path():
    """Test that clear paths don't get waypoints."""
    from_xy = (50, 100)
    to_xy = (150, 100)

    # No obstacles
    obstacles = []

    waypoints = find_waypoints(from_xy, to_xy, obstacles)

    # Should have no waypoints (straight line is clear)
    assert len(waypoints) == 0
    print("✓ Clear path correctly uses no waypoints")


def test_route_all_connections():
    """Test batch routing of all connections."""
    variables = [
        {'id': 1, 'name': 'Var1', 'x': 100, 'y': 100, 'width': 60, 'height': 26},
        {'id': 2, 'name': 'Var2', 'x': 300, 'y': 100, 'width': 60, 'height': 26},
        {'id': 3, 'name': 'Var3', 'x': 200, 'y': 200, 'width': 60, 'height': 26},
    ]

    connections = [
        {'from_id': 1, 'to_id': 2},  # Should be clear
        {'from_id': 1, 'to_id': 3},  # Should be clear
    ]

    waypoint_map = route_all_connections(variables, connections)

    assert '1_2' in waypoint_map
    assert '1_3' in waypoint_map
    print(f"✓ Batch routing works, routed {len(waypoint_map)} connections")


if __name__ == '__main__':
    print("Running edge routing tests...\n")

    test_bounding_boxes()
    test_line_intersection()
    test_waypoint_calculation()
    test_clear_path()
    test_route_all_connections()

    print("\n✅ All tests passed!")

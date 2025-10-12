#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Edge Routing with Obstacle Avoidance

Routes connection arrows around variable bounding boxes using orthogonal
(Manhattan-style) routing to create clean, professional diagrams.
"""

from typing import List, Dict, Tuple, Optional
import math


def calculate_bounding_boxes(variables: List[Dict]) -> List[Dict]:
    """
    Calculate bounding boxes for all variables with padding.

    Args:
        variables: List of variable dicts with 'name', 'x', 'y', 'width', 'height'

    Returns:
        List of bounding box dicts with 'name', 'left', 'right', 'top', 'bottom'
    """
    boxes = []

    for var in variables:
        x = var.get('x', 0)
        y = var.get('y', 0)
        w = var.get('width', 60)
        h = var.get('height', 26)

        # Add padding for visual clearance around variables
        padding = 50

        boxes.append({
            'name': var.get('name', ''),
            'id': var.get('id'),
            'center_x': x,
            'center_y': y,
            'left': x - w/2 - padding,
            'right': x + w/2 + padding,
            'top': y - h/2 - padding,
            'bottom': y + h/2 + padding
        })

    return boxes


def line_intersects_box(p1: Tuple[float, float], p2: Tuple[float, float], box: Dict) -> bool:
    """
    Check if line segment from p1 to p2 intersects with bounding box.

    Uses Cohen-Sutherland line clipping algorithm concept.

    Args:
        p1: Start point (x, y)
        p2: End point (x, y)
        box: Bounding box dict with 'left', 'right', 'top', 'bottom'

    Returns:
        True if line intersects box
    """
    x1, y1 = p1
    x2, y2 = p2

    # Check if either endpoint is inside the box
    if (box['left'] <= x1 <= box['right'] and box['top'] <= y1 <= box['bottom']):
        return True
    if (box['left'] <= x2 <= box['right'] and box['top'] <= y2 <= box['bottom']):
        return True

    # Check if line intersects any of the four edges
    # Left edge
    if line_segments_intersect(p1, p2, (box['left'], box['top']), (box['left'], box['bottom'])):
        return True
    # Right edge
    if line_segments_intersect(p1, p2, (box['right'], box['top']), (box['right'], box['bottom'])):
        return True
    # Top edge
    if line_segments_intersect(p1, p2, (box['left'], box['top']), (box['right'], box['top'])):
        return True
    # Bottom edge
    if line_segments_intersect(p1, p2, (box['left'], box['bottom']), (box['right'], box['bottom'])):
        return True

    return False


def line_segments_intersect(p1: Tuple[float, float], p2: Tuple[float, float],
                            p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    """
    Check if two line segments (p1-p2) and (p3-p4) intersect.

    Uses parametric line equation and cross products.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denom) < 1e-10:  # Parallel lines
        return False

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    return 0 <= t <= 1 and 0 <= u <= 1


def route_is_clear(path: List[Tuple[float, float]], obstacles: List[Dict]) -> bool:
    """
    Check if a multi-segment path is clear of obstacles.

    Args:
        path: List of points defining the path
        obstacles: List of bounding boxes

    Returns:
        True if entire path is clear
    """
    for i in range(len(path) - 1):
        segment_start = path[i]
        segment_end = path[i + 1]

        for box in obstacles:
            if line_intersects_box(segment_start, segment_end, box):
                return False

    return True


def find_waypoints(from_xy: Tuple[float, float], to_xy: Tuple[float, float],
                   obstacles: List[Dict], from_id: int = None, to_id: int = None) -> List[Tuple[int, int]]:
    """
    Calculate waypoints for routing from source to target avoiding obstacles.

    Uses orthogonal (Manhattan) routing with H-V-H or V-H-V patterns.

    Args:
        from_xy: Source position (x, y)
        to_xy: Target position (x, y)
        obstacles: List of bounding box obstacles
        from_id: Source variable ID (to exclude from obstacle check)
        to_id: Target variable ID (to exclude from obstacle check)

    Returns:
        List of waypoints (as integer tuples for MDL format)
    """
    # Filter out source and target from obstacles
    filtered_obstacles = [
        box for box in obstacles
        if box.get('id') not in [from_id, to_id]
    ]

    # If straight line is clear, use it (no waypoints needed)
    straight_clear = not any(line_intersects_box(from_xy, to_xy, box) for box in filtered_obstacles)
    if straight_clear:
        print(f"[Edge Routing] Connection {from_id}→{to_id}: Straight path clear, no waypoints needed")
        return []

    print(f"[Edge Routing] Connection {from_id}→{to_id}: Straight path blocked by {len([b for b in filtered_obstacles if line_intersects_box(from_xy, to_xy, b)])} obstacles, trying alternative routes...")

    # Try H-V-H pattern (Horizontal-Vertical-Horizontal)
    # Go horizontally to midpoint, then vertically, then horizontally to target
    midpoint_x = (from_xy[0] + to_xy[0]) / 2

    waypoint1 = (midpoint_x, from_xy[1])
    waypoint2 = (midpoint_x, to_xy[1])

    path_hvh = [from_xy, waypoint1, waypoint2, to_xy]
    if route_is_clear(path_hvh, filtered_obstacles):
        return [(int(waypoint1[0]), int(waypoint1[1])),
                (int(waypoint2[0]), int(waypoint2[1]))]

    # Try V-H-V pattern (Vertical-Horizontal-Vertical)
    # Go vertically to midpoint, then horizontally, then vertically to target
    midpoint_y = (from_xy[1] + to_xy[1]) / 2

    waypoint1 = (from_xy[0], midpoint_y)
    waypoint2 = (to_xy[0], midpoint_y)

    path_vhv = [from_xy, waypoint1, waypoint2, to_xy]
    if route_is_clear(path_vhv, filtered_obstacles):
        return [(int(waypoint1[0]), int(waypoint1[1])),
                (int(waypoint2[0]), int(waypoint2[1]))]

    # Try offset H-V-H patterns (shift midpoint left/right)
    for offset in [200, -200, 400, -400]:
        offset_x = midpoint_x + offset
        waypoint1 = (offset_x, from_xy[1])
        waypoint2 = (offset_x, to_xy[1])

        path = [from_xy, waypoint1, waypoint2, to_xy]
        if route_is_clear(path, filtered_obstacles):
            return [(int(waypoint1[0]), int(waypoint1[1])),
                    (int(waypoint2[0]), int(waypoint2[1]))]

    # Try offset V-H-V patterns (shift midpoint up/down)
    for offset in [150, -150, 300, -300]:
        offset_y = midpoint_y + offset
        waypoint1 = (from_xy[0], offset_y)
        waypoint2 = (to_xy[0], offset_y)

        path = [from_xy, waypoint1, waypoint2, to_xy]
        if route_is_clear(path, filtered_obstacles):
            return [(int(waypoint1[0]), int(waypoint1[1])),
                    (int(waypoint2[0]), int(waypoint2[1]))]

    # Fallback: use simple offset from straight line
    # Calculate perpendicular offset
    dx = to_xy[0] - from_xy[0]
    dy = to_xy[1] - from_xy[1]
    length = math.sqrt(dx*dx + dy*dy)

    if length > 0:
        # Perpendicular vector
        perp_x = -dy / length
        perp_y = dx / length

        # Try offset to the side
        for offset_dist in [100, -100, 200, -200]:
            mid_x = (from_xy[0] + to_xy[0]) / 2
            mid_y = (from_xy[1] + to_xy[1]) / 2

            waypoint = (mid_x + perp_x * offset_dist, mid_y + perp_y * offset_dist)

            path = [from_xy, waypoint, to_xy]
            if route_is_clear(path, filtered_obstacles):
                print(f"[Edge Routing] Connection {from_id}→{to_id}: Using perpendicular offset waypoint")
                return [(int(waypoint[0]), int(waypoint[1]))]

    # Last resort: Force a waypoint using H-V-H pattern even if not perfect
    # This prevents straight lines through obstacles
    print(f"[Edge Routing] Connection {from_id}→{to_id}: All patterns blocked, forcing H-V-H waypoint as last resort")
    midpoint_x = (from_xy[0] + to_xy[0]) / 2
    waypoint1 = (midpoint_x, from_xy[1])
    waypoint2 = (midpoint_x, to_xy[1])
    return [(int(waypoint1[0]), int(waypoint1[1])),
            (int(waypoint2[0]), int(waypoint2[1]))]


def route_all_connections(variables: List[Dict], connections: List[Dict]) -> Dict[str, List[Tuple[int, int]]]:
    """
    Calculate waypoints for all connections in the diagram.

    Args:
        variables: List of all variables with positions
        connections: List of all connections (arrows)

    Returns:
        Dict mapping connection key to list of waypoints
        Key format: "from_id_to_id" (e.g., "5_12" for arrow from var 5 to var 12)
    """
    # Calculate all bounding boxes
    obstacles = calculate_bounding_boxes(variables)

    # Build ID to position mapping
    id_to_pos = {
        var['id']: (var['x'], var['y'])
        for var in variables
        if 'id' in var and 'x' in var and 'y' in var
    }

    waypoint_map = {}

    for conn in connections:
        from_id = conn.get('from_id')
        to_id = conn.get('to_id')

        if from_id not in id_to_pos or to_id not in id_to_pos:
            continue

        from_xy = id_to_pos[from_id]
        to_xy = id_to_pos[to_id]

        # Calculate waypoints
        waypoints = find_waypoints(from_xy, to_xy, obstacles, from_id, to_id)

        # Store with connection key
        conn_key = f"{from_id}_{to_id}"
        waypoint_map[conn_key] = waypoints

    return waypoint_map

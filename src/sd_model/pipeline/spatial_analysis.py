"""
Spatial Analysis Utilities

Analyzes MDL spatial layout to provide context for theory enhancement.
Identifies crowded regions, available space, and spatial constraints.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import math


def extract_variable_positions(mdl_path: Path) -> List[Dict]:
    """Extract variable positions from MDL file.

    Args:
        mdl_path: Path to MDL file

    Returns:
        List of dicts with variable spatial info:
        [{"id": 1, "name": "Var", "x": 100, "y": 200, "width": 60, "height": 26}, ...]
    """
    content = mdl_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    variables = []
    for line in lines:
        if line.startswith('10,'):  # Variable line (Type 10)
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


def identify_crowded_regions(variables: List[Dict], grid_size: int = 300) -> List[Dict]:
    """Identify regions with high variable density.

    Divides canvas into grid and counts variables per cell.

    Args:
        variables: List of variable position dicts
        grid_size: Size of grid cells (default 300px)

    Returns:
        List of crowded region dicts:
        [{"bounds": "(600-900, 400-700)", "variable_count": 8, "density": "high"}, ...]
    """
    if not variables:
        return []

    # Find canvas extent
    min_x = min(v['x'] - v['width']//2 for v in variables)
    max_x = max(v['x'] + v['width']//2 for v in variables)
    min_y = min(v['y'] - v['height']//2 for v in variables)
    max_y = max(v['y'] + v['height']//2 for v in variables)

    # Create grid
    grid = {}
    for v in variables:
        grid_x = (v['x'] - min_x) // grid_size
        grid_y = (v['y'] - min_y) // grid_size
        key = (grid_x, grid_y)
        if key not in grid:
            grid[key] = []
        grid[key].append(v)

    # Identify crowded cells (> 4 variables per cell is crowded)
    crowded_regions = []
    for (gx, gy), vars_in_cell in grid.items():
        if len(vars_in_cell) > 4:
            x_start = min_x + gx * grid_size
            x_end = x_start + grid_size
            y_start = min_y + gy * grid_size
            y_end = y_start + grid_size

            density = "very high" if len(vars_in_cell) > 8 else "high"

            crowded_regions.append({
                'bounds': f"({x_start}-{x_end}, {y_start}-{y_end})",
                'variable_count': len(vars_in_cell),
                'density': density,
                'variable_names': [v['name'] for v in vars_in_cell]
            })

    return crowded_regions


def find_available_space(variables: List[Dict], grid_size: int = 300, margin: int = 100) -> List[Dict]:
    """Find empty or sparse regions suitable for new variables.

    Args:
        variables: List of variable position dicts
        grid_size: Size of grid cells (default 300px)
        margin: Minimum distance from existing variables (default 100px)

    Returns:
        List of available space dicts:
        [{"bounds": "(200-500, 200-500)", "estimated_capacity": 6, "proximity": "near Knowledge cluster"}, ...]
    """
    if not variables:
        return [{
            'bounds': "(400-700, 300-600)",
            'estimated_capacity': 10,
            'proximity': "center of empty canvas"
        }]

    # Find canvas extent with margin
    min_x = min(v['x'] - v['width']//2 for v in variables) - margin
    max_x = max(v['x'] + v['width']//2 for v in variables) + margin
    min_y = min(v['y'] - v['height']//2 for v in variables) - margin
    max_y = max(v['y'] + v['height']//2 for v in variables) + margin

    # Expand canvas bounds to give room for growth
    min_x = min(min_x, 200)
    max_x = max(max_x, 2000)
    min_y = min(min_y, 200)
    max_y = max(max_y, 1200)

    # Create grid and check for empty cells
    grid = {}
    for v in variables:
        grid_x = (v['x'] - min_x) // grid_size
        grid_y = (v['y'] - min_y) // grid_size
        key = (grid_x, grid_y)
        if key not in grid:
            grid[key] = []
        grid[key].append(v)

    # Find empty or sparse cells
    available_spaces = []
    num_cells_x = (max_x - min_x) // grid_size + 1
    num_cells_y = (max_y - min_y) // grid_size + 1

    for gx in range(num_cells_x):
        for gy in range(num_cells_y):
            key = (gx, gy)
            var_count = len(grid.get(key, []))

            # Empty or very sparse cells are available
            if var_count <= 2:
                x_start = min_x + gx * grid_size
                x_end = x_start + grid_size
                y_start = min_y + gy * grid_size
                y_end = y_start + grid_size

                # Estimate capacity based on grid size
                # Assume ~100x100 per variable with spacing
                estimated_capacity = ((grid_size * grid_size) // (100 * 100)) - var_count
                estimated_capacity = max(1, estimated_capacity)

                # Find nearest variable cluster for proximity description
                nearby_vars = []
                for neighbor_key in [(gx-1, gy), (gx+1, gy), (gx, gy-1), (gx, gy+1)]:
                    nearby_vars.extend(grid.get(neighbor_key, []))

                if nearby_vars:
                    proximity = f"adjacent to {len(nearby_vars)} variables"
                else:
                    proximity = "isolated region"

                available_spaces.append({
                    'bounds': f"({x_start}-{x_end}, {y_start}-{y_end})",
                    'estimated_capacity': estimated_capacity,
                    'proximity': proximity,
                    'current_occupancy': var_count
                })

    # Sort by capacity (best spaces first)
    available_spaces.sort(key=lambda s: s['estimated_capacity'], reverse=True)

    return available_spaces[:10]  # Return top 10 available spaces


def calculate_canvas_extent(variables: List[Dict]) -> Dict:
    """Calculate current canvas dimensions.

    Args:
        variables: List of variable position dicts

    Returns:
        Dict with extent info: {"width": 2200, "height": 1200, "center": (1100, 600)}
    """
    if not variables:
        return {'width': 2000, 'height': 1200, 'center': (1000, 600)}

    min_x = min(v['x'] - v['width']//2 for v in variables)
    max_x = max(v['x'] + v['width']//2 for v in variables)
    min_y = min(v['y'] - v['height']//2 for v in variables)
    max_y = max(v['y'] + v['height']//2 for v in variables)

    width = max_x - min_x
    height = max_y - min_y
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2

    return {
        'width': width,
        'height': height,
        'center': (center_x, center_y),
        'bounds': {
            'x_min': min_x,
            'x_max': max_x,
            'y_min': min_y,
            'y_max': max_y
        }
    }


def analyze_spatial_layout(mdl_path: Path) -> Dict:
    """Comprehensive spatial analysis of MDL layout.

    Main entry point that combines all spatial analysis functions.

    Args:
        mdl_path: Path to MDL file

    Returns:
        Dict with complete spatial analysis:
        {
            "crowded_regions": [...],
            "available_space": [...],
            "canvas_extent": {...},
            "total_variables": 24
        }
    """
    variables = extract_variable_positions(mdl_path)

    crowded_regions = identify_crowded_regions(variables)
    available_space = find_available_space(variables)
    canvas_extent = calculate_canvas_extent(variables)

    return {
        'total_variables': len(variables),
        'canvas_extent': canvas_extent,
        'crowded_regions': crowded_regions,
        'available_space': available_space,
        'spatial_summary': _generate_spatial_summary(crowded_regions, available_space, canvas_extent)
    }


def _generate_spatial_summary(crowded_regions: List[Dict], available_space: List[Dict], extent: Dict) -> str:
    """Generate human-readable spatial summary for LLM prompt."""
    summary_parts = []

    summary_parts.append(f"Canvas size: {extent['width']}×{extent['height']} pixels")

    if crowded_regions:
        summary_parts.append(f"⚠️  {len(crowded_regions)} crowded regions detected:")
        for region in crowded_regions[:3]:  # Top 3 most crowded
            summary_parts.append(f"  - {region['bounds']}: {region['variable_count']} variables ({region['density']} density)")
    else:
        summary_parts.append("✓ No crowded regions - layout has good spacing")

    if available_space:
        summary_parts.append(f"✓ {len(available_space)} regions available for new variables:")
        for space in available_space[:5]:  # Top 5 best spaces
            summary_parts.append(f"  - {space['bounds']}: capacity ~{space['estimated_capacity']} variables ({space['proximity']})")
    else:
        summary_parts.append("⚠️  Canvas is densely packed - consider expanding canvas or reorganizing")

    return "\n".join(summary_parts)

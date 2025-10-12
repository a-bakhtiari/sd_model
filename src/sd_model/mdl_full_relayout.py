#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full MDL Diagram Relayout

Repositions ALL variables (both existing and new) to create a clean,
clustered layout that makes conceptual sense.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
import math
from .llm.client import LLMClient


FULL_RELAYOUT_PROMPT = """You are a System Dynamics expert creating a professional, publication-quality diagram layout.

## CRITICAL: YOU ARE ONLY REPOSITIONING VARIABLES
- You are ONLY changing the X,Y coordinates of variables
- ALL other properties (name, type, equations, connections) remain UNCHANGED
- This is purely a visual layout optimization task

## TASK
Reposition ALL {total_vars} variables (existing + new) into a clean, clustered layout that tells a clear story.

## ALL VARIABLES (existing and new)
{all_vars_json}

## ALL CONNECTIONS
{all_connections_json}

## LAYOUT PHILOSOPHY: Create Visual Narrative Clusters

### CLUSTER-BASED ORGANIZATION
Instead of placing things close because they connect, create DISTINCT THEMATIC ZONES:

1. **Identify 3-5 major conceptual clusters** (e.g., "Knowledge Management", "Community Dynamics", "Contributor Pipeline")
2. **Assign each variable to ONE cluster** based on its semantic meaning
3. **Place each cluster in a distinct canvas region** (400-800px apart from other clusters)
4. **Within each cluster**: arrange variables logically, with ~200px spacing

### SPATIAL LAYOUT STRATEGY

#### Cluster Positioning (Macro-level)
- **Cluster centers should be 400-800px apart** (create clear visual separation)
- Example cluster positions:
  - Cluster 1: centered around (500, 300)
  - Cluster 2: centered around (1200, 300)
  - Cluster 3: centered around (1900, 300)
  - Cluster 4: centered around (800, 700)
  - Cluster 5: centered around (1500, 700)

#### Within-Cluster Layout (Micro-level)
- **Stocks**: Horizontal line through cluster center
- **Flows**: On paths between stocks
- **Auxiliaries**: Above/below stocks in same cluster
- **Variables in same cluster**: 200-300px apart
- **Maintain vertical layering**: Auxiliaries on top (y=100-200), Stocks middle (y=300-600), Auxiliaries bottom (y=700-900)

### CRITICAL SPATIAL RULES - FOLLOW STRICTLY

1. **MANDATORY SPACING**: Minimum 200px between ANY two variable centers (formula: distance = sqrt((x2-x1)² + (y2-y1)²) ≥ 200)
   - Variable widths are ~60-90px, heights ~26px
   - Check EVERY variable against ALL other variables
   - This is NON-NEGOTIABLE - positions will be validated programmatically

2. **CROSS-CLUSTER CONNECTIONS ARE OK**: Long lines between clusters are acceptable - they show relationships

3. **WITHIN-CLUSTER SPACING**: Variables in same cluster should be 200-300px apart for readability

4. **CANVAS BOUNDS**: x: 100-2400, y: 50-950 (stay within bounds with margin)

### STEP-BY-STEP PROCESS

**Step 1: Identify Clusters**
Group variables into 3-5 thematic clusters based on meaning (NOT just connections).

**Step 2: Assign Cluster Positions**
Choose distinct canvas regions for each cluster (400-800px apart).

**Step 3: Position Variables Within Clusters**
For EACH variable (process ONE AT A TIME):
- Place it in its cluster region
- Maintain type-based vertical layering
- Check distance to ALL previously positioned variables (must be ≥200px)
- If too close to any variable, adjust position and recheck
- Keep 200-300px from other variables in same cluster

**Step 4: Final Verification**
Before outputting, verify:
- All clusters are visually separated (400-800px between cluster centers)
- NO overlaps anywhere (all variables ≥200px apart)
- Variables are clearly grouped by theme
- All positions are within canvas bounds

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown):
{{
  "clusters": [
    {{
      "name": "Cluster Name",
      "description": "What this cluster represents",
      "center_x": 500,
      "center_y": 300,
      "variables": ["Var1", "Var2", "Var3"]
    }},
    ...
  ],
  "positions": [
    {{
      "name": "Variable Name",
      "x": 520,
      "y": 280,
      "cluster": "Cluster Name",
      "reasoning": "Stock in [cluster], 220px from [nearby var]"
    }},
    ...
  ]
}}

IMPORTANT:
- Create 3-5 distinct clusters with meaningful themes
- Spread clusters across canvas (not all in one area)
- Clear visual separation between clusters
- Variables within cluster should be cohesive

Now create the clustered layout:"""


def _validate_and_fix_overlaps(
    position_map: Dict[str, Tuple[int, int]],
    min_spacing: int = 200,
    canvas_bounds: Tuple[int, int, int, int] = (100, 2400, 50, 950)
) -> Dict[str, Tuple[int, int]]:
    """
    Validate positions and fix any overlaps.

    Args:
        position_map: Dict mapping variable names to (x, y) tuples
        min_spacing: Minimum distance between variable centers
        canvas_bounds: (min_x, max_x, min_y, max_y)

    Returns:
        Updated position_map with overlaps fixed
    """
    min_x, max_x, min_y, max_y = canvas_bounds
    var_names = list(position_map.keys())
    fixed_positions = position_map.copy()

    max_iterations = 100
    iteration = 0

    while iteration < max_iterations:
        has_overlap = False

        # Check each pair of variables
        for i, var1 in enumerate(var_names):
            x1, y1 = fixed_positions[var1]

            for var2 in var_names[i+1:]:
                x2, y2 = fixed_positions[var2]

                # Calculate distance
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                if distance < min_spacing:
                    has_overlap = True

                    # Move var2 away from var1
                    # Calculate direction vector
                    if distance > 0:
                        dx = (x2 - x1) / distance
                        dy = (y2 - y1) / distance
                    else:
                        # Variables at exact same position, move right
                        dx, dy = 1, 0

                    # Push var2 to minimum spacing distance
                    needed_distance = min_spacing - distance + 10  # +10 for safety margin
                    new_x2 = x2 + dx * needed_distance
                    new_y2 = y2 + dy * needed_distance

                    # Keep within bounds
                    new_x2 = max(min_x, min(max_x, new_x2))
                    new_y2 = max(min_y, min(max_y, new_y2))

                    fixed_positions[var2] = (int(new_x2), int(new_y2))

        if not has_overlap:
            break

        iteration += 1

    if iteration >= max_iterations:
        print(f"Warning: Could not fully resolve all overlaps after {max_iterations} iterations")
    else:
        print(f"Overlap validation complete: fixed overlaps in {iteration} iterations")

    return fixed_positions


def _reposition_valves(
    lines: List[str],
    position_map: Dict[str, Tuple[int, int]]
) -> Tuple[List[str], int]:
    """
    Reposition valve elements (Type 11) based on connected stock positions.

    Valves are flow control symbols that sit on arrows between stocks.
    When stocks move, valves need to move to stay on the path.

    Args:
        lines: MDL file lines
        position_map: Variable name → (x, y) position mapping

    Returns:
        (updated_lines, valves_updated_count)
    """
    # Build variable ID to name mapping
    var_id_to_name = {}
    var_name_to_id = {}
    for line in lines:
        if line.startswith('10,'):
            parts = line.split(',')
            if len(parts) > 2:
                try:
                    var_id = int(parts[1])
                    var_name = parts[2].strip()
                    if var_name.startswith('"') and var_name.endswith('"'):
                        var_name = var_name[1:-1].replace('""', '"')
                    var_id_to_name[var_id] = var_name
                    var_name_to_id[var_name] = var_id
                except (ValueError, IndexError):
                    pass

    # Build valve ID to connected variables mapping
    valve_connections = {}  # valve_id → (from_var_id, to_var_id)

    # Parse arrows to find valve connections
    for line in lines:
        if line.startswith('1,'):
            parts = line.split(',')
            if len(parts) > 3:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Check if either endpoint is a valve (Type 11)
                    # We need to look at the actual lines to determine this
                    # For now, we'll handle valve-to-variable connections

                    # If from or to is a valve, store the connection
                    # (This is simplified - in real MDL, valves have specific IDs)

                except (ValueError, IndexError):
                    pass

    # Update valve positions
    new_lines = []
    valves_updated = 0

    for line in lines:
        if line.startswith('11,'):  # Valve line
            parts = line.split(',')
            if len(parts) > 4:
                try:
                    valve_id = int(parts[1])
                    old_x = int(parts[3])
                    old_y = int(parts[4])

                    # Find stocks connected by this valve
                    # Strategy: Look for arrows involving this valve
                    # Then calculate midpoint between the connected stocks

                    # For simplicity, we'll find the two closest stocks to this valve
                    # and position the valve at their midpoint
                    connected_stocks = []
                    for var_name, (var_x, var_y) in position_map.items():
                        # Check if this is a stock (we'd need type info, but let's check distance)
                        dist = math.sqrt((var_x - old_x)**2 + (var_y - old_y)**2)
                        if dist < 300:  # Within reasonable range
                            connected_stocks.append((var_name, var_x, var_y, dist))

                    # Sort by distance and take two closest
                    connected_stocks.sort(key=lambda x: x[3])

                    if len(connected_stocks) >= 2:
                        stock1 = connected_stocks[0]
                        stock2 = connected_stocks[1]

                        # Calculate midpoint
                        new_x = int((stock1[1] + stock2[1]) / 2)
                        new_y = int((stock1[2] + stock2[2]) / 2)

                        # Update position
                        parts[3] = str(new_x)
                        parts[4] = str(new_y)
                        line = ','.join(parts)
                        valves_updated += 1

                except (ValueError, IndexError):
                    pass

        new_lines.append(line)

    return new_lines, valves_updated


def _strip_arrow_waypoints(lines: List[str]) -> Tuple[List[str], int]:
    """
    Strip waypoints from arrow lines (Type 1).

    Arrows can have waypoints for routing: 1|(x1,y1)|,(x2,y2)|...
    When variables move, these become obsolete. Strip them to let
    Vensim auto-route with straight lines.

    Args:
        lines: MDL file lines

    Returns:
        (updated_lines, arrows_updated_count)
    """
    new_lines = []
    arrows_updated = 0

    for line in lines:
        if line.startswith('1,'):  # Arrow line
            # Check if it has waypoints (contains pattern like "1|(x,y)|")
            if '|(' in line:
                # Find the waypoint section (after last comma before waypoints)
                # Format: ...,color,-1--1--1,,1|(x1,y1)|,(x2,y2)|
                parts = line.split(',')

                # Find where waypoints start (look for the ",1|(" pattern)
                waypoint_start_idx = None
                for i, part in enumerate(parts):
                    if '1|(' in part:
                        waypoint_start_idx = i
                        break

                if waypoint_start_idx is not None:
                    # Keep everything before waypoints, add simple waypoint
                    parts = parts[:waypoint_start_idx]
                    # Add simple waypoint
                    parts.append('1|(0,0)|')
                    line = ','.join(parts)
                    arrows_updated += 1

        new_lines.append(line)

    return new_lines, arrows_updated


def reposition_entire_diagram(
    mdl_path: Path,
    new_variables: List[Dict],
    new_connections: List[Dict],
    output_path: Path,
    llm_client: Optional[LLMClient] = None
) -> Dict:
    """
    Reposition ENTIRE diagram (all variables) with new additions.

    Updates ALL position-related elements:
    - Variables (Type 10): Repositioned using LLM clustering + overlap validation
    - Valves (Type 11): Repositioned to midpoint between connected stocks
    - Arrows (Type 1): Waypoints stripped for clean routing

    Args:
        mdl_path: Original MDL file
        new_variables: New variables to add
        new_connections: New connections to add
        output_path: Where to save relayouted MDL
        llm_client: LLM client for layout optimization

    Returns:
        Summary dict with counts: variables_repositioned, clusters,
        valves_repositioned, arrows_simplified
    """
    # Read original MDL
    content = mdl_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # Extract all existing variables
    existing_vars = []
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
                    type_code = int(parts[7])
                    var_type = 'Stock' if type_code == 3 else ('Flow' if type_code == 40 else 'Auxiliary')

                    existing_vars.append({
                        'id': var_id,
                        'name': var_name,
                        'x': x,
                        'y': y,
                        'type': var_type,
                        'original_line': line
                    })
                except (ValueError, IndexError):
                    pass

    # Extract all existing connections
    existing_conns = []
    for line in lines:
        if line.startswith('1,') and ',0,0,0,22,0,192,' in line:  # Influence arrows
            parts = line.split(',')
            if len(parts) > 3:
                try:
                    from_id = int(parts[2])
                    to_id = int(parts[3])
                    # Find variable names
                    from_name = next((v['name'] for v in existing_vars if v['id'] == from_id), None)
                    to_name = next((v['name'] for v in existing_vars if v['id'] == to_id), None)
                    if from_name and to_name:
                        existing_conns.append({
                            'from': from_name,
                            'to': to_name
                        })
                except (ValueError, IndexError):
                    pass

    # Combine all variables and connections
    all_vars = existing_vars + [{'name': v['name'], 'type': v['type']} for v in new_variables]
    all_conns = existing_conns + new_connections

    # Get LLM layout
    if not llm_client:
        try:
            llm_client = LLMClient(provider="deepseek")
        except RuntimeError:
            llm_client = None

    if not llm_client or not llm_client.enabled:
        print("Warning: LLM not available, cannot reposition entire diagram")
        return {'error': 'LLM required for full relayout'}

    # Build prompt
    all_vars_summary = [{'name': v['name'], 'type': v.get('type', 'Auxiliary')} for v in all_vars]
    all_conns_summary = [{'from': c['from'], 'to': c['to']} for c in all_conns]

    prompt = FULL_RELAYOUT_PROMPT.format(
        total_vars=len(all_vars),
        all_vars_json=json.dumps(all_vars_summary, indent=2),
        all_connections_json=json.dumps(all_conns_summary, indent=2)
    )

    print(f"\nAsking LLM to create clustered layout for {len(all_vars)} variables...")

    try:
        response = llm_client.complete(
            prompt,
            temperature=0.3,
            max_tokens=8000,
            timeout=120
        )

        # Parse response
        response = response.strip()
        if response.startswith('```'):
            lines_resp = response.split('\n')
            json_lines = []
            in_block = False
            for line in lines_resp:
                if line.startswith('```'):
                    in_block = not in_block
                    continue
                if in_block or not line.startswith('```'):
                    json_lines.append(line)
            response = '\n'.join(json_lines)

        layout_data = json.loads(response)

        # Print cluster info
        print("\nClusters created:")
        for cluster in layout_data.get('clusters', []):
            print(f"  {cluster['name']}: {cluster['description']}")
            print(f"    Center: ({cluster['center_x']}, {cluster['center_y']})")
            print(f"    Variables: {len(cluster['variables'])}")

        # Build position map
        position_map = {}
        for pos in layout_data.get('positions', []):
            position_map[pos['name']] = (pos['x'], pos['y'])
            print(f"  {pos['name']}: ({pos['x']}, {pos['y']}) in {pos.get('cluster', '?')}")

        # Validate and fix overlaps
        print("\nValidating positions and fixing any overlaps...")
        position_map = _validate_and_fix_overlaps(position_map)

        # Step 1: Update variable positions (Type 10)
        new_lines = []
        for line in lines:
            if line.startswith('10,'):
                parts = line.split(',')
                if len(parts) > 7:
                    var_name = parts[2].strip()
                    if var_name.startswith('"') and var_name.endswith('"'):
                        var_name = var_name[1:-1].replace('""', '"')

                    if var_name in position_map:
                        new_x, new_y = position_map[var_name]
                        parts[3] = str(new_x)
                        parts[4] = str(new_y)
                        line = ','.join(parts)

            new_lines.append(line)

        # Step 2: Reposition valves (Type 11)
        print("\nRepositioning flow valves...")
        new_lines, valves_updated = _reposition_valves(new_lines, position_map)
        if valves_updated > 0:
            print(f"✓ Repositioned {valves_updated} flow valves")

        # Step 3: Strip arrow waypoints (Type 1)
        print("\nSimplifying arrow routing...")
        new_lines, arrows_updated = _strip_arrow_waypoints(new_lines)
        if arrows_updated > 0:
            print(f"✓ Simplified {arrows_updated} arrow routes (stripped waypoints)")

        # Write relayouted MDL
        output_path.write_text('\n'.join(new_lines), encoding='utf-8')

        return {
            'variables_repositioned': len(position_map),
            'clusters': len(layout_data.get('clusters', [])),
            'valves_repositioned': valves_updated,
            'arrows_simplified': arrows_updated
        }

    except Exception as e:
        print(f"Error during relayout: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

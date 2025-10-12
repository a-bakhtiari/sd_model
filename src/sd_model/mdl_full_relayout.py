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
from .edge_routing import route_all_connections


FULL_RELAYOUT_PROMPT = """You are a System Dynamics expert creating a professional, publication-quality diagram layout.

## CRITICAL: YOU ARE ONLY REPOSITIONING VARIABLES
- You are ONLY changing the X,Y coordinates of variables
- ALL other properties (name, type, equations, connections) remain UNCHANGED
- This is purely a visual layout optimization task

## TASK
Reposition ALL {total_vars} variables into a clean, clustered layout using ASCII VISUALIZATION.

## VARIABLES TO POSITION
{all_vars_json}

## CONNECTIONS
{all_connections_json}

## LAYOUT APPROACH: VISUALIZE FIRST, THEN POSITION

We'll use a TWO-STEP process to ensure good spatial layout:
1. **STEP 1**: Create an ASCII visualization sketch showing variable placement
2. **STEP 2**: Convert the ASCII sketch to exact (x, y) coordinates

---

# STEP 1: CREATE ASCII VISUALIZATION

## Canvas Grid Reference
```
X-axis: 0────500───1000───1500───2000───2400
Y-axis: 0, 200, 400, 600, 800, 1000

Canvas dimensions: 2400px wide × 1000px tall
Each '─' in the grid ≈ 100px
```

## Instructions for ASCII Sketch:

1. **Identify 3-5 thematic clusters** (e.g., "Knowledge Management", "Community Dynamics", "Contributor Pipeline")

2. **Draw a rough layout** using abbreviated variable names (3-5 characters each)
   - Use `[ABC]` to represent variables
   - Place cluster groups together
   - Space variables apart (at least 2-3 characters between them)
   - Mark cluster boundaries with comments

3. **Follow type-based vertical layering**:
   - **Stocks (type: Stock)**: Middle rows (y ≈ 400-600)
   - **Auxiliaries (type: Auxiliary)**: Top rows (y ≈ 100-300) or Bottom (y ≈ 700-900)
   - **Flows (type: Flow)**: Between stocks (y ≈ 300-700)

## Example ASCII Layout (for reference):

```
0────500───1000───1500───2000───2400
│                                       │
100   [DOC]  [QUA]        ← Cluster 1: Knowledge
│                                       │
300               [NEW]  [EXP]         ← Cluster 2: Contributors
│     [KNW]                   [COR]    │
500                     [MEN]          │
│                                       │
700            [ENG]        [SKL]      ← Cluster 3: Community
│                                       │
900                                     │

Legend:
[DOC] = Documentation
[QUA] = Quality
[KNW] = Knowledge Stock
[NEW] = New Contributors
[EXP] = Experienced
[COR] = Core Developers
[MEN] = Mentoring
[ENG] = Engagement
[SKL] = Skill Level
```

## Your ASCII Sketch:
Create your ASCII visualization here, using the grid reference above.

---

# STEP 2: CONVERT TO EXACT COORDINATES

## Conversion Guidelines:

1. **Horizontal positioning**:
   - Each character position ≈ 50px
   - If variable is at column 10, x ≈ 500px
   - If variable is at column 30, x ≈ 1500px

2. **Vertical positioning**:
   - Each line ≈ 100-150px
   - Line 1 (near top) → y ≈ 150
   - Line 3 (middle) → y ≈ 400
   - Line 7 (lower) → y ≈ 700

3. **Spacing verification**:
   - Ensure minimum 200px between ANY two variable centers
   - Formula: distance = sqrt((x2-x1)² + (y2-y1)²) ≥ 200
   - Our Python validator will auto-fix minor overlaps

4. **Cluster-based organization**:
   - Place each cluster 400-800px apart (cluster centers)
   - Variables within cluster: 200-300px apart

---

## OUTPUT FORMAT

Return JSON with BOTH the ASCII visualization AND the coordinate positions:

```json
{{
  "ascii_layout": "Your complete ASCII sketch here (as multiline string)",
  "clusters": [
    {{
      "name": "Cluster Name",
      "description": "What this cluster represents",
      "center_x": 500,
      "center_y": 300,
      "variables": ["Var1", "Var2", "Var3"]
    }}
  ],
  "positions": [
    {{
      "name": "Variable Name (full name)",
      "x": 520,
      "y": 280,
      "cluster": "Cluster Name",
      "reasoning": "In [cluster] at ASCII position [row, col]; 220px from [nearby var]"
    }}
  ]
}}
```

---

## WORKED EXAMPLE (showing full process)

**Given 6 variables:**
- "Project Knowledge" (Stock)
- "Knowledge Creation" (Flow)
- "Documentation" (Auxiliary)
- "Team Size" (Stock)
- "Hiring Rate" (Flow)
- "Skill Level" (Auxiliary)

**STEP 1: ASCII Sketch**
```
0────500───1000───1500───2000
│
200     [DOC]            [SKL]        ← Auxiliaries top
│
400   [PKN]            [TEM]          ← Stocks middle
│       ↑                ↑
500    [KCR]           [HIR]          ← Flows
│
700

Cluster 1 (Knowledge): PKN, KCR, DOC - centered ~500
Cluster 2 (Team): TEM, HIR, SKL - centered ~1500
```

**STEP 2: Convert to Coordinates**
- [DOC] at col ~8, row ~2 → (400, 200)
- [PKN] at col ~6, row ~4 → (300, 400)
- [KCR] at col ~8, row ~5 → (400, 500)
- [TEM] at col ~28, row ~4 → (1400, 400)
- [HIR] at col ~28, row ~5 → (1400, 500)
- [SKL] at col ~30, row ~2 → (1500, 200)

Check spacing: all pairs >200px ✓

**Output JSON:**
```json
{{
  "ascii_layout": "[Full ASCII sketch here]",
  "clusters": [
    {{"name": "Knowledge Management", "center_x": 400, "center_y": 350, "variables": ["Project Knowledge", "Knowledge Creation", "Documentation"]}},
    {{"name": "Team Dynamics", "center_x": 1450, "center_y": 350, "variables": ["Team Size", "Hiring Rate", "Skill Level"]}}
  ],
  "positions": [
    {{"name": "Documentation", "x": 400, "y": 200, "cluster": "Knowledge Management", "reasoning": "Auxiliary in Knowledge cluster"}},
    {{"name": "Project Knowledge", "x": 300, "y": 400, "cluster": "Knowledge Management", "reasoning": "Stock at cluster center"}},
    ...
  ]
}}
```

---

## YOUR TURN

Now create:
1. Your ASCII visualization showing all {total_vars} variables
2. The JSON with clusters and exact coordinates

REMEMBER:
- Think visually first (ASCII), then convert to coordinates
- Cluster by meaning/theme (3-5 clusters)
- Our Python validator will fix minor overlaps - focus on good clustering
- Return valid JSON only (no markdown code blocks)

Begin:"""


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


def _update_arrow_waypoints(lines: List[str], waypoint_map: Dict[str, List[Tuple[int, int]]]) -> Tuple[List[str], int]:
    """
    Update arrow lines with calculated waypoints for obstacle avoidance.

    Arrows can have waypoints for routing: 1|(x1,y1)|1|(x2,y2)|...
    We calculate optimal waypoints to route around variables using edge routing.

    Args:
        lines: MDL file lines
        waypoint_map: Dict mapping "from_id_to_id" to list of waypoints

    Returns:
        (updated_lines, arrows_updated_count)
    """
    new_lines = []
    arrows_updated = 0

    for line in lines:
        if line.startswith('1,'):  # Arrow line
            parts = line.split(',')

            # Extract from_id and to_id
            if len(parts) > 3:
                try:
                    arrow_id = int(parts[1])
                    from_id = int(parts[2])
                    to_id = int(parts[3])

                    # Look up waypoints
                    conn_key = f"{from_id}_{to_id}"
                    waypoints = waypoint_map.get(conn_key, [])

                    # Find where waypoints start (look for the ",1|(" pattern)
                    waypoint_start_idx = None
                    for i, part in enumerate(parts):
                        if '1|(' in part:
                            waypoint_start_idx = i
                            break

                    if waypoint_start_idx is not None:
                        # Keep everything before waypoints
                        parts = parts[:waypoint_start_idx]

                        # Add calculated waypoints
                        if waypoints:
                            # Format: 1|(x1,y1)|1|(x2,y2)|...
                            waypoint_str = '1|(' + ')|1|('.join([f"{int(x)},{int(y)}" for x, y in waypoints]) + ')|'
                            parts.append(waypoint_str)
                            arrows_updated += 1
                        else:
                            # No waypoints needed (straight line is clear)
                            parts.append('1|(0,0)|')

                        line = ','.join(parts)

                except (ValueError, IndexError):
                    # If parsing fails, keep original line
                    pass

        new_lines.append(line)

    return new_lines, arrows_updated


def reposition_entire_diagram(
    mdl_path: Path,
    new_variables: List[Dict],
    new_connections: List[Dict],
    output_path: Path,
    llm_client: Optional[LLMClient] = None,
    clustering_scheme: Optional[Dict] = None
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
        clustering_scheme: Optional clustering scheme from theory enhancement

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
        if line.startswith('1,'):  # All arrow types (Type 1 = arrows/connections)
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

    # Build clustering section if provided
    clustering_section = ""
    if clustering_scheme:
        clusters = clustering_scheme.get('clusters', [])
        layout_hints = clustering_scheme.get('layout_hints', [])
        rationale = clustering_scheme.get('rationale', '')

        clustering_section = "\n## IMPORTANT: USE PROVIDED CLUSTERING SCHEME\n\n"
        clustering_section += f"**Clustering Rationale**: {rationale}\n\n"
        clustering_section += "You MUST use the following cluster organization:\n\n"

        for cluster in clusters:
            cluster_name = cluster.get('name', 'Unnamed')
            theme = cluster.get('theme', '')
            variables = cluster.get('variables', [])
            connections_to = cluster.get('connections_to_other_clusters', {})

            clustering_section += f"### {cluster_name}\n"
            clustering_section += f"- **Theme**: {theme}\n"
            clustering_section += f"- **Variables ({len(variables)})**: {', '.join(variables)}\n"
            if connections_to:
                clustering_section += f"- **Inter-cluster connections**: {dict(connections_to)}\n"
            clustering_section += "\n"

        if layout_hints:
            clustering_section += "**Layout Hints from Theory Enhancement**:\n"
            for hint in layout_hints:
                clustering_section += f"- {hint}\n"
            clustering_section += "\n"

        clustering_section += "**Your Task**: Position variables according to these clusters while following the ASCII visualization approach below.\n\n"

    prompt = FULL_RELAYOUT_PROMPT.format(
        total_vars=len(all_vars),
        all_vars_json=json.dumps(all_vars_summary, indent=2),
        all_connections_json=json.dumps(all_conns_summary, indent=2)
    )

    # Insert clustering section after CONNECTIONS if provided
    if clustering_section:
        # Find the position after CONNECTIONS section
        insert_pos = prompt.find("## LAYOUT APPROACH:")
        if insert_pos != -1:
            prompt = prompt[:insert_pos] + clustering_section + prompt[insert_pos:]

    if clustering_scheme:
        num_clusters = len(clustering_scheme.get('clusters', []))
        print(f"\nAsking LLM to create layout for {len(all_vars)} variables using {num_clusters} predefined clusters...")
    else:
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

        # Print ASCII visualization if present
        if 'ascii_layout' in layout_data and layout_data['ascii_layout']:
            print("\n" + "=" * 60)
            print("LLM's ASCII Visualization:")
            print("=" * 60)
            print(layout_data['ascii_layout'])
            print("=" * 60)

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

        # Step 3: Calculate smart waypoints for arrows (Type 1)
        print("\nCalculating smart arrow routes to avoid overlaps...")

        # Build list of variables with IDs and updated positions
        vars_with_positions = []
        for line in new_lines:
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

                        vars_with_positions.append({
                            'id': var_id,
                            'name': var_name,
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height
                        })
                    except (ValueError, IndexError):
                        pass

        # Build list of connections with IDs
        connections_with_ids = []
        for line in new_lines:
            if line.startswith('1,'):  # All arrow types (Type 1 = arrows/connections)
                parts = line.split(',')
                if len(parts) > 3:
                    try:
                        from_id = int(parts[2])
                        to_id = int(parts[3])
                        connections_with_ids.append({
                            'from_id': from_id,
                            'to_id': to_id
                        })
                    except (ValueError, IndexError):
                        pass

        # Calculate waypoints using edge routing
        waypoint_map = route_all_connections(vars_with_positions, connections_with_ids)

        # Update arrows with calculated waypoints
        new_lines, arrows_updated = _update_arrow_waypoints(new_lines, waypoint_map)
        if arrows_updated > 0:
            print(f"✓ Routed {arrows_updated} arrows with smart waypoints to avoid overlaps")

        # Write relayouted MDL
        output_path.write_text('\n'.join(new_lines), encoding='utf-8')

        return {
            'variables_repositioned': len(position_map),
            'clusters': len(layout_data.get('clusters', [])),
            'valves_repositioned': valves_updated,
            'arrows_routed': arrows_updated
        }

    except Exception as e:
        print(f"Error during relayout: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

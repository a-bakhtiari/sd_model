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
from collections import Counter, defaultdict
from .llm.client import LLMClient
from .edge_routing import route_all_connections


def analyze_connection_complexity(connections: List[Dict], variables: List[Dict]) -> Dict:
    """
    Analyze connection patterns to help LLM make better positioning decisions.

    Returns dict with:
    - high_connectivity_vars: Variables with most connections (should be central)
    - long_connections: Connections that span large distances (minimize in layout)
    - connection_count_by_var: Dict mapping var name to connection count
    """
    # Count connections per variable
    connection_count = Counter()

    for conn in connections:
        from_var = conn.get('from')
        to_var = conn.get('to')
        if from_var:
            connection_count[from_var] += 1
        if to_var:
            connection_count[to_var] += 1

    # Get high-connectivity variables (top 20% or at least 5 connections)
    high_connectivity = [
        (var, count) for var, count in connection_count.most_common()
        if count >= 5 or count >= max(connection_count.values(), default=1) * 0.8
    ]

    # Build variable position map (if available)
    var_positions = {}
    for var in variables:
        if 'x' in var and 'y' in var:
            var_positions[var['name']] = (var['x'], var['y'])

    # Calculate connection lengths if positions available
    long_connections = []
    if var_positions:
        for conn in connections:
            from_var = conn.get('from')
            to_var = conn.get('to')
            if from_var in var_positions and to_var in var_positions:
                x1, y1 = var_positions[from_var]
                x2, y2 = var_positions[to_var]
                distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                if distance > 600:  # Long connection threshold
                    long_connections.append({
                        'from': from_var,
                        'to': to_var,
                        'distance': int(distance)
                    })

    long_connections.sort(key=lambda x: x['distance'], reverse=True)

    return {
        'high_connectivity_vars': high_connectivity[:8],  # Top 8
        'long_connections': long_connections[:5],  # Top 5 longest
        'connection_count_by_var': dict(connection_count)
    }


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

**Your Goal:** Create a clean, readable diagram by:
1. Grouping process modules spatially
2. Positioning high-connectivity hubs centrally
3. Keeping connected variables close together
4. Avoiding variables in arrow paths and minimizing arrow crossings (details below)

## CRITICAL: ARROW ROUTING AND VARIABLE PLACEMENT

**Understanding Arrow Paths:**
- Arrows connect the CENTER of one variable to the CENTER of another variable
- These arrow paths should remain clear - avoid placing other variables directly in the arrow's path
- You don't need to avoid the entire rectangular area between variables, just the direct arrow line

**Good vs Bad Placement:**

```
GOOD - Variable C is offset from arrow path:
[A] ────────────────→ [B]
        [C]
Arrow from A→B is clear (C is below the path)

ALSO GOOD - Horizontal offset works too:
[A] ────────────────→ [B]

[C]
Variables can be near connected pairs, just not ON the arrow line

BAD - Variable C directly blocks arrow path:
[A] ──────[C]──────→ [B]
Arrow from A→B has to route around C

ALSO BAD - Variable in middle of long connection:
[A] ───────────────── [D] ────────────────→ [B]
If A connects to B, arrow has to route around D

GOOD - Multiple connections with clear paths:
[A] ────→ [B] ────→ [C]

         [D]
A→B→C chain is clear, D is offset below and doesn't block

ALSO GOOD - Star pattern with hub:
        [A]
         │
[B] ←─ [HUB] ─→ [C]
         │
        [D]
Hub connects to A, B, C, D - all arrows radiate cleanly

ALSO GOOD - Triangle arrangement:
        [A]
       ↙  ↘
    [B]    [C]
A connects to both B and C, arrows don't overlap

ALSO GOOD - Grid pattern:
[A] ─→ [B]
 │      │
 ↓      ↓
[C] ─→ [D]
Multiple connections (A→B, A→C, B→D, C→D) all clear

ALSO GOOD - Branching chain:
        [B]
       ↗
[A] ─→ [C]
       ↘
        [D]
A branches to B, C, D without arrows crossing

BAD - Variable blocking multiple arrow paths:
[A] ─────[E]────→ [B]
          ↓
          ↓
[C] ─────────────→ [D]
E is in the path of A→B arrow, forces arrow to route around it

BETTER - Offset the blocking variable:
[A] ───────────→ [B]

    [E]

[C] ───────────→ [D]
Now E is offset and doesn't block either arrow path
```

**Key Principle**: When placing a variable, check if any existing connections would pass through its position. If so, offset the variable vertically or horizontally to keep the arrow path clear. The layout doesn't need to follow any specific pattern (like triangles) - just avoid placing variables directly in arrow paths. With multiple connections, think about all the arrow paths and position variables in the spaces between them.

## AVOIDING ARROW OVERLAPS

**Arrow Crossing Issue:**
- When two arrows cross each other, the diagram becomes harder to read
- Ideally, minimize the number of arrow crossings in your layout

**Good vs Bad Arrow Routing:**

```
GOOD - Parallel arrows don't cross:
[A] ────→ [B]

[C] ────→ [D]
Two horizontal arrows running parallel

ALSO GOOD - Vertical parallel arrows:
    [A]     [B]
     │       │
     ↓       ↓
    [C]     [D]
A→C and B→D run parallel vertically

BAD - Diagonal crossing:
[A]         [D]
  ╲       ╱
   ╲     ╱
    ╲   ╱
     ╲ ╱
      X
     ╱ ╲
    ╱   ╲
   ╱     ╲
[C]         [B]
A→B and D→C cross in the middle

BETTER - Same connections, no crossing:
[A]         [D]
 │           │
 │           │
 ↓           ↓
[B]         [C]
A→B and D→C now run parallel (swapped B and C positions)
```

**Strategy**: When you have many connections, try to group variables so that their connections run in similar directions (parallel) rather than crossing paths. If process A connects to process B, and process C connects to process D, position them so A-B and C-D arrows don't intersect.

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

1. **Use provided process-based clusters** (if provided above) - Each process is a mini-model with inputs/outputs
   - If no clusters provided, identify 3-5 thematic groupings
   - Process outputs are hub connections - position them to link multiple processes

2. **Draw a rough layout** using abbreviated variable names (3-5 characters each)
   - Use `[ABC]` to represent variables
   - Group each process's variables together
   - Space variables apart (at least 2-3 characters between them)
   - Mark process boundaries with comments
   - Position hub outputs (variables connecting multiple processes) centrally
   - **Apply arrow routing principles**: avoid blocking paths, minimize crossings (see detailed examples above)

3. **Follow type-based vertical layering**:
   - **Stocks (type: Stock)**: Middle rows (y ≈ 400-600)
   - **Auxiliaries (type: Auxiliary)**: Top rows (y ≈ 100-300) or Bottom (y ≈ 700-900)
   - **Flows (type: Flow)**: Between stocks (y ≈ 300-700)

## Example ASCII Layout (for reference):

```
     0        500      1000     1500     2000
     |         |         |         |         |
100  [QC]
     │
200  [INP]─────────────────→[CAP]
     │                      │ ↓
300  [MAT]            [WIP][RAT]
                       ↓    ↓
400                   [OUT]────────────→[DEM]
                                         ↓
500                                     [SHP]

Process 1: QC→INP→MAT (vertical, left)
Process 2: CAP→WIP,RAT→OUT (grid, center) - CAP is hub
Process 3: DEM→SHP (vertical, right)
Inter-process: INP→CAP, OUT→DEM
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

4. **Process-based organization**:
   - Place each process module 400-800px apart (process centers)
   - Variables within process: 200-300px apart
   - Position hub outputs (connecting multiple processes) between their connected processes

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
      "variables": ["Var1", "Var2", "Var3"]
    }}
  ],
  "positions": [
    {{
      "name": "Variable Name (full name)",
      "x": 520,
      "y": 280,
      "cluster": "Cluster Name"
    }}
  ]
}}
```

---

## WORKED EXAMPLE (showing full process)

**Given 6 variables in 2 processes:**

Process 1 (Material Intake):
- "Raw Materials" (Stock)
- "Intake Rate" (Flow)
- "Quality Standard" (Auxiliary)

Process 2 (Production):
- "Work In Progress" (Stock)
- "Production Rate" (Flow)
- "Capacity" (Auxiliary) - hub output

**STEP 1: ASCII Sketch**
```
0────500───1000───1500───2000
│
200     [QS]             [CAP]        ← Auxiliaries (CAP is hub)
│
400   [RM]             [WIP]          ← Stocks middle
│       ↑                ↑
500    [IR]            [PR]           ← Flows
│
700

Process 1 (Material Intake): RM, IR, QS - centered ~400
Process 2 (Production): WIP, PR, CAP - centered ~1500
Note: CAP connects to multiple processes
```

**STEP 2: Convert to Coordinates**
- [QS] at col ~8, row ~2 → (400, 200)
- [RM] at col ~6, row ~4 → (300, 400)
- [IR] at col ~8, row ~5 → (400, 500)
- [CAP] at col ~30, row ~2 → (1500, 200) - hub positioned centrally
- [WIP] at col ~28, row ~4 → (1400, 400)
- [PR] at col ~28, row ~5 → (1400, 500)

Check spacing: all pairs >200px ✓

**Output JSON:**
```json
{{
  "ascii_layout": "[Full ASCII sketch here]",
  "clusters": [
    {{"name": "Material Intake", "description": "Material sourcing and quality control", "variables": ["Raw Materials", "Intake Rate", "Quality Standard"]}},
    {{"name": "Production", "description": "Assembly and production capacity", "variables": ["Work In Progress", "Production Rate", "Capacity"]}}
  ],
  "positions": [
    {{"name": "Quality Standard", "x": 400, "y": 200, "cluster": "Material Intake"}},
    {{"name": "Raw Materials", "x": 300, "y": 400, "cluster": "Material Intake"}},
    {{"name": "Capacity", "x": 1500, "y": 200, "cluster": "Production"}},
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
- Apply the arrow routing principles from above (avoid blocking paths, minimize crossings)
- Use process-based clusters if provided (hub outputs connect multiple processes)
- Our Python validator will fix minor overlaps - focus on good clustering and clear routing
- Return valid JSON only (no markdown code blocks)

Begin:"""


RECREATION_LAYOUT_PROMPT = """You are a System Dynamics expert creating a professional diagram layout from scratch.

## TASK
Position {total_vars} theory-generated variables into a clean, clustered layout.

These variables were generated from theoretical frameworks and organized into
process-based modules. Your goal is to create a clear, readable spatial layout.

## VARIABLES TO POSITION
{all_vars_json}

## CONNECTIONS
{all_connections_json}

**Your Goal:** Create a clean, readable diagram by:
1. Grouping process modules spatially
2. Positioning high-connectivity hubs centrally
3. Keeping connected variables close together
4. Avoiding variables in arrow paths and minimizing arrow crossings (details below)

## CRITICAL: ARROW ROUTING AND VARIABLE PLACEMENT

**Understanding Arrow Paths:**
- Arrows connect the CENTER of one variable to the CENTER of another variable
- These arrow paths should remain clear - avoid placing other variables directly in the arrow's path
- You don't need to avoid the entire rectangular area between variables, just the direct arrow line

**Good vs Bad Placement:**

```
GOOD - Variable C is offset from arrow path:
[A] ────────────────→ [B]
        [C]
Arrow from A→B is clear (C is below the path)

ALSO GOOD - Horizontal offset works too:
[A] ────────────────→ [B]

[C]
Variables can be near connected pairs, just not ON the arrow line

BAD - Variable C directly blocks arrow path:
[A] ──────[C]──────→ [B]
Arrow from A→B has to route around C

ALSO BAD - Variable in middle of long connection:
[A] ───────────────── [D] ────────────────→ [B]
If A connects to B, arrow has to route around D

GOOD - Multiple connections with clear paths:
[A] ────→ [B] ────→ [C]

         [D]
A→B→C chain is clear, D is offset below and doesn't block

ALSO GOOD - Star pattern with hub:
        [A]
         │
[B] ←─ [HUB] ─→ [C]
         │
        [D]
Hub connects to A, B, C, D - all arrows radiate cleanly

ALSO GOOD - Triangle arrangement:
        [A]
       ↙  ↘
    [B]    [C]
A connects to both B and C, arrows don't overlap

ALSO GOOD - Grid pattern:
[A] ─→ [B]
 │      │
 ↓      ↓
[C] ─→ [D]
Multiple connections (A→B, A→C, B→D, C→D) all clear

ALSO GOOD - Branching chain:
        [B]
       ↗
[A] ─→ [C]
       ↘
        [D]
A branches to B, C, D without arrows crossing

BAD - Variable blocking multiple arrow paths:
[A] ─────[E]────→ [B]
          ↓
          ↓
[C] ─────────────→ [D]
E is in the path of A→B arrow, forces arrow to route around it

BETTER - Offset the blocking variable:
[A] ───────────→ [B]

    [E]

[C] ───────────→ [D]
Now E is offset and doesn't block either arrow path
```

**Key Principle**: When placing a variable, check if any existing connections would pass through its position. If so, offset the variable vertically or horizontally to keep the arrow path clear. The layout doesn't need to follow any specific pattern (like triangles) - just avoid placing variables directly in arrow paths. With multiple connections, think about all the arrow paths and position variables in the spaces between them.

## AVOIDING ARROW OVERLAPS

**Arrow Crossing Issue:**
- When two arrows cross each other, the diagram becomes harder to read
- Ideally, minimize the number of arrow crossings in your layout

**Good vs Bad Arrow Routing:**

```
GOOD - Parallel arrows don't cross:
[A] ────→ [B]

[C] ────→ [D]
Two horizontal arrows running parallel

ALSO GOOD - Vertical parallel arrows:
    [A]     [B]
     │       │
     ↓       ↓
    [C]     [D]
A→C and B→D run parallel vertically

BAD - Diagonal crossing:
[A]         [D]
  ╲       ╱
   ╲     ╱
    ╲   ╱
     ╲ ╱
      X
     ╱ ╲
    ╱   ╲
   ╱     ╲
[C]         [B]
A→B and D→C cross in the middle

BETTER - Same connections, no crossing:
[A]         [D]
 │           │
 │           │
 ↓           ↓
[B]         [C]
A→B and D→C now run parallel (swapped B and C positions)
```

**Strategy**: When you have many connections, try to group variables so that their connections run in similar directions (parallel) rather than crossing paths. If process A connects to process B, and process C connects to process D, position them so A-B and C-D arrows don't intersect.

## LAYOUT APPROACH: VISUALIZE FIRST, THEN POSITION

We'll use a TWO-STEP process to ensure good spatial layout:
1. **STEP 1**: Create an ASCII visualization sketch showing variable placement
2. **STEP 2**: Convert the ASCII sketch to exact (x, y) coordinates

---

# STEP 1: CREATE ASCII VISUALIZATION

## Canvas Grid Reference
```
X-axis: 0────{canvas_x1}───{canvas_x2}───{canvas_x3}───{canvas_x4}
Y-axis: 0, {canvas_y1}, {canvas_y2}, {canvas_y3}, {canvas_y4}

Canvas dimensions: {canvas_width}px wide × {canvas_height}px tall
Each '─' in the grid ≈ 100px
```

## Instructions for ASCII Sketch:

1. **Use provided process-based clusters** (if provided above) - Each process is a mini-model with inputs/outputs
   - If no clusters provided, identify 3-5 thematic groupings
   - Process outputs are hub connections - position them to link multiple processes

2. **Draw a rough layout** using abbreviated variable names (3-5 characters each)
   - Use `[ABC]` to represent variables
   - Group each process's variables together
   - Space variables apart (at least 2-3 characters between them)
   - Mark process boundaries with comments
   - Position hub outputs (variables connecting multiple processes) centrally
   - **Apply arrow routing principles**: avoid blocking paths, minimize crossings (see detailed examples above)

3. **Follow type-based vertical layering**:
   - **Stocks (type: Stock)**: Middle rows (y ≈ {stock_y_min}-{stock_y_max})
   - **Auxiliaries (type: Auxiliary)**: Top rows (y ≈ {aux_y_top_min}-{aux_y_top_max}) or Bottom (y ≈ {aux_y_bot_min}-{aux_y_bot_max})
   - **Flows (type: Flow)**: Between stocks (y ≈ {flow_y_min}-{flow_y_max})

## Example ASCII Layout (for reference):

```
     0        500      1000     1500     2000
     |         |         |         |         |
100  [QC]
     │
200  [INP]─────────────────→[CAP]
     │                      │ ↓
300  [MAT]            [WIP][RAT]
                       ↓    ↓
400                   [OUT]────────────→[DEM]
                                         ↓
500                                     [SHP]

Process 1: QC→INP→MAT (vertical, left)
Process 2: CAP→WIP,RAT→OUT (grid, center) - CAP is hub
Process 3: DEM→SHP (vertical, right)
Inter-process: INP→CAP, OUT→DEM
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

4. **Process-based organization**:
   - Place each process module 400-800px apart (process centers)
   - Variables within process: 200-300px apart
   - Position hub outputs (connecting multiple processes) between their connected processes

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
      "variables": ["Var1", "Var2", "Var3"]
    }}
  ],
  "positions": [
    {{
      "name": "Variable Name (full name)",
      "x": 520,
      "y": 280,
      "cluster": "Cluster Name"
    }}
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
- Apply the arrow routing principles from above (avoid blocking paths, minimize crossings)
- Use process-based clusters if provided (hub outputs connect multiple processes)
- Our Python validator will fix minor overlaps - focus on good clustering and clear routing
- Return valid JSON only (no markdown code blocks)

Begin:"""


def _get_layout_prompt(
    is_recreation: bool,
    total_vars: int,
    all_vars_json: str,
    all_connections_json: str
) -> str:
    """
    Select and format the appropriate layout prompt based on mode.

    Args:
        is_recreation: True if creating fresh layout (recreation mode),
                      False if repositioning existing model (full relayout)
        total_vars: Number of variables to position
        all_vars_json: JSON string of variables
        all_connections_json: JSON string of connections

    Returns:
        Formatted prompt string ready for LLM
    """
    # Calculate adaptive canvas size based on number of variables
    canvas_width = max(2400, total_vars * 150)
    canvas_height = max(1000, total_vars * 50)

    # Canvas grid points for visualization
    canvas_x1 = canvas_width // 6
    canvas_x2 = canvas_width // 3
    canvas_x3 = canvas_width // 2
    canvas_x4 = canvas_width

    canvas_y1 = canvas_height // 5
    canvas_y2 = canvas_height // 3
    canvas_y3 = canvas_height // 2
    canvas_y4 = canvas_height

    # Type-based layering coordinates
    stock_y_min = int(canvas_height * 0.4)
    stock_y_max = int(canvas_height * 0.6)

    aux_y_top_min = int(canvas_height * 0.1)
    aux_y_top_max = int(canvas_height * 0.3)
    aux_y_bot_min = int(canvas_height * 0.7)
    aux_y_bot_max = int(canvas_height * 0.9)

    flow_y_min = int(canvas_height * 0.3)
    flow_y_max = int(canvas_height * 0.7)

    # Select prompt based on mode
    if is_recreation:
        prompt_template = RECREATION_LAYOUT_PROMPT
    else:
        prompt_template = FULL_RELAYOUT_PROMPT

    # Format with all parameters
    return prompt_template.format(
        total_vars=total_vars,
        all_vars_json=all_vars_json,
        all_connections_json=all_connections_json,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        canvas_x1=canvas_x1,
        canvas_x2=canvas_x2,
        canvas_x3=canvas_x3,
        canvas_x4=canvas_x4,
        canvas_y1=canvas_y1,
        canvas_y2=canvas_y2,
        canvas_y3=canvas_y3,
        canvas_y4=canvas_y4,
        stock_y_min=stock_y_min,
        stock_y_max=stock_y_max,
        aux_y_top_min=aux_y_top_min,
        aux_y_top_max=aux_y_top_max,
        aux_y_bot_min=aux_y_bot_min,
        aux_y_bot_max=aux_y_bot_max,
        flow_y_min=flow_y_min,
        flow_y_max=flow_y_max
    )


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


def _reposition_clouds(
    lines: List[str],
    position_map: Dict[str, Tuple[int, int]]
) -> Tuple[List[str], int]:
    """
    Reposition cloud elements (Type 12) relative to moved stocks.

    Clouds represent model boundaries (sources/sinks). When stocks move,
    clouds should maintain their relative offset from connected stocks.

    Args:
        lines: MDL file lines
        position_map: Variable name -> (x, y) new positions

    Returns:
        (updated_lines, clouds_updated_count)
    """
    new_lines = []
    clouds_updated = 0

    # Build variable name to position lookup
    var_positions = position_map.copy()

    for line in lines:
        if line.startswith('12,'):  # Type 12 = cloud
            parts = line.split(',')
            if len(parts) > 6:
                try:
                    cloud_id = int(parts[1])
                    old_x = int(parts[3])
                    old_y = int(parts[4])

                    # Find closest stock (within 400px)
                    closest_stock = None
                    min_dist = 400
                    original_offset = None

                    for var_name, (var_x, var_y) in var_positions.items():
                        dist = ((var_x - old_x)**2 + (var_y - old_y)**2)**0.5
                        if dist < min_dist:
                            min_dist = dist
                            closest_stock = (var_x, var_y)
                            original_offset = (old_x - var_x, old_y - var_y)

                    if closest_stock and original_offset:
                        # Maintain relative offset from stock
                        new_x = closest_stock[0] + original_offset[0]
                        new_y = closest_stock[1] + original_offset[1]

                        # Update cloud position
                        parts[3] = str(new_x)
                        parts[4] = str(new_y)
                        line = ','.join(parts)
                        clouds_updated += 1

                except (ValueError, IndexError):
                    pass

        new_lines.append(line)

    return new_lines, clouds_updated


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

                        # Arrow curving disabled - keep all arrows straight
                        # Just reset waypoints to (0,0)
                        if len(parts) > 9:
                            parts[9] = '192'  # Field 10: straight line
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
        valves_repositioned, clouds_repositioned, arrows_simplified
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
            from .config import should_use_gpt
            provider, model = should_use_gpt("full_relayout")
            llm_client = LLMClient(provider=provider, model=model)
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
        overall_narrative = clustering_scheme.get('overall_narrative', '')
        layout_hints = clustering_scheme.get('layout_hints', [])

        clustering_section = "\n## IMPORTANT: USE PROVIDED PROCESS-BASED CLUSTERING\n\n"

        # Add overall narrative showing system-wide connections
        if overall_narrative:
            clustering_section += "**Overall System Flow**:\n"
            clustering_section += f"{overall_narrative}\n\n"

        clustering_section += "You MUST use the following process-based organization:\n\n"
        clustering_section += "**Key Principle**: Each process is a self-contained mini-model. Process outputs act as connection hubs linking multiple processes. Position hub variables centrally to minimize arrow length.\n\n"

        for cluster in clusters:
            cluster_name = cluster.get('name', 'Unnamed')
            narrative = cluster.get('narrative', cluster.get('theme', ''))  # Fallback to theme for backwards compat
            inputs_desc = cluster.get('inputs', 'N/A')
            outputs_desc = cluster.get('outputs', 'N/A')
            variables = cluster.get('variables', [])
            connections_to = cluster.get('connections_to_other_clusters', {})

            clustering_section += f"### {cluster_name}\n"
            clustering_section += f"- **Process Description**: {narrative}\n"
            clustering_section += f"- **Inputs**: {inputs_desc}\n"
            clustering_section += f"- **Outputs** (hub connections): {outputs_desc}\n"
            clustering_section += f"- **Variables ({len(variables)})**: {', '.join(variables) if variables else '[Generated by Step 2]'}\n"
            if connections_to:
                clustering_section += f"- **Inter-process connections**: {dict(connections_to)}\n"
            clustering_section += "\n"

        if layout_hints:
            clustering_section += "**Layout Hints**:\n"
            for hint in layout_hints:
                clustering_section += f"- {hint}\n"
            clustering_section += "\n"

        clustering_section += "**Your Task**: Position variables according to these process modules while following the ASCII visualization approach below. Group each process's variables spatially, then connect modules via their output hubs.\n\n"

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

        try:
            layout_data = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"\n{'='*60}")
            print("ERROR: LLM returned invalid JSON")
            print(f"{'='*60}")
            print(f"Parse error: {e}")
            print(f"\nLLM Response (first 2000 chars):")
            print(response[:2000])
            print(f"{'='*60}\n")
            raise

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

        # Step 2b: Reposition clouds (Type 12)
        print("\nRepositioning boundary clouds...")
        new_lines, clouds_updated = _reposition_clouds(new_lines, position_map)
        if clouds_updated > 0:
            print(f"✓ Repositioned {clouds_updated} boundary clouds")

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
            'clouds_repositioned': clouds_updated,
            'arrows_routed': arrows_updated
        }

    except Exception as e:
        print(f"Error during relayout: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

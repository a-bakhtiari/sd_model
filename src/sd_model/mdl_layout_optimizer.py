#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDL Layout Optimizer using LLM

Uses an LLM to intelligently position new variables in the diagram based on:
- Semantic relationships (what connects to what)
- Variable types (Stock, Flow, Auxiliary)
- Existing layout structure
- Avoiding overlaps and crossing lines
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from .llm.client import LLMClient


LAYOUT_PROMPT_TEMPLATE = """You are an expert System Dynamics modeler creating a clean, professional Vensim diagram layout.

## TASK
Position {num_new_vars} new variables in an existing diagram to minimize visual clutter and maximize readability.

## EXISTING DIAGRAM STATE
Variables currently placed:
{existing_vars_json}

## NEW VARIABLES TO POSITION
Variables that need positions:
{new_vars_json}

## CONNECTIONS (both existing and new)
{connections_json}

## CRITICAL LAYOUT RULES (follow strictly)

### 1. SPATIAL AWARENESS - Prevent Overlaps
- **Minimum spacing**: 200px between ANY two variable centers
- Variable widths: ~60-90px, heights: ~26px
- Check distance to ALL existing AND previously positioned new variables
- Formula: distance = sqrt((x2-x1)² + (y2-y1)²) must be ≥ 200

### 2. ARROW ROUTING - Clear Connection Paths
**Understanding Arrow Paths:**
- Arrows connect the CENTER of one variable to the CENTER of another variable
- Avoid placing new variables directly in the arrow's path between connected variables
- You don't need to avoid the entire rectangular area, just the direct arrow line

**Good patterns for multiple connections:**
- **Chain**: A→B→C→D (linear flow, no blocking)
- **Star**: Hub in center, others around it (clean radial connections)
- **Triangle**: Three variables forming triangle (no variable in the middle)
- **Grid**: 2x2 layout with clear paths between connections
- **Branching**: Tree-like structure with clear parent-child paths

**Key Principle**: If A connects to B, don't place C directly between them on the arrow line.

### 3. MINIMIZE ARROW CROSSINGS
- When two arrows cross each other (e.g., A→B and C→D forming an X), readability suffers
- Try to arrange variables so arrows run parallel (horizontal or vertical)
- Group connections with similar directions together

**Example - avoiding crossings:**
```
BAD (diagonal crossing):        BETTER (parallel):
[A]         [D]                 [A]    [B]
  ↘       ↗                       ↓      ↓
    ✗                           [D]    [C]
  ↗       ↘
[B]         [C]
A→B and D→C cross               Same connections, parallel arrows
```

### 4. SEMANTIC GROUPING - Logical Organization
- Group by process or conceptual clusters (e.g., production variables, quality variables)
- Respect causal flow direction: causes on left/top, effects on right/bottom
- Keep feedback loops compact and circular

### 5. TYPE-BASED LAYERS (vertical organization)
- **Stocks (type: Stock)**: y = 200-700 (main horizontal band)
- **Flows (type: Flow)**: y = 100-800 (between stocks they connect)
- **Auxiliaries (type: Auxiliary)**: y = -100 to 200 OR y = 700-900 (above/below stocks)

### 6. HORIZONTAL DISTRIBUTION
- **Don't cluster**: Spread new variables across x-axis
- **Continue existing patterns**: Extend current layout, don't create isolated islands
- **Canvas bounds**: x: -200 to 2500, y: -200 to 1000

### 7. STEP-BY-STEP POSITIONING PROCESS
For each new variable:
a) Identify which existing/new variables it connects to
b) Calculate average position of connected variables
c) Place near that average (within 200-400px)
d) Check spacing to ALL other variables (≥200px)
e) Adjust if too close to any variable
f) Apply arrow routing principles: avoid blocking paths between connected variables
g) Verify arrangement minimizes arrow crossings

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown blocks, no explanation before/after):
{{
  "positions": [
    {{
      "name": "Variable Name",
      "x": 1200,
      "y": 400
    }},
    ...
  ]
}}

IMPORTANT:
- Position variables ONE AT A TIME in order listed
- Each position must consider ALL previously positioned variables
- Verify spacing before finalizing each position
- Prioritize readability over perfect semantic grouping

Now position the variables:"""


class MDLLayoutOptimizer:
    """Optimizes layout of MDL diagrams using LLM reasoning."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize optimizer.

        Args:
            llm_client: Optional LLM client. If None, will try to create one.
        """
        if llm_client is None:
            try:
                self.llm = LLMClient(provider="deepseek")
            except RuntimeError as e:
                print(f"Warning: LLM not available: {e}")
                print("Will use fallback grid positioning")
                self.llm = None
        else:
            self.llm = llm_client

    def optimize_positions(
        self,
        existing_variables: List[Dict],
        new_variables: List[Dict],
        all_connections: List[Dict]
    ) -> List[Dict]:
        """
        Calculate optimal positions for new variables.

        Args:
            existing_variables: List of dicts with name, x, y, type
            new_variables: List of dicts with name, type (no x, y yet)
            all_connections: List of dicts with from, to, relationship

        Returns:
            List of new_variables with x, y positions added
        """
        if not self.llm or not self.llm.enabled:
            print("Using fallback grid positioning (no LLM available)")
            return self._fallback_grid_positions(existing_variables, new_variables)

        # Prepare data for LLM
        existing_vars_summary = [
            {
                'name': v['name'],
                'type': v.get('type', 'Auxiliary'),
                'x': v.get('x', 0),
                'y': v.get('y', 0)
            }
            for v in existing_variables
        ]

        new_vars_summary = [
            {
                'name': v['name'],
                'type': v.get('type', 'Auxiliary'),
                'description': v.get('description', '')
            }
            for v in new_variables
        ]

        connections_summary = [
            {
                'from': c.get('from', ''),
                'to': c.get('to', ''),
                'type': c.get('relationship', 'positive')
            }
            for c in all_connections
        ]

        # Build prompt
        prompt = LAYOUT_PROMPT_TEMPLATE.format(
            num_new_vars=len(new_variables),
            existing_vars_json=json.dumps(existing_vars_summary, indent=2),
            new_vars_json=json.dumps(new_vars_summary, indent=2),
            connections_json=json.dumps(connections_summary, indent=2)
        )

        print(f"\nAsking LLM to position {len(new_variables)} new variables...")

        try:
            # Call LLM
            response = self.llm.complete(
                prompt,
                temperature=0.3,  # Balance between consistency and spatial reasoning
                max_tokens=6000,  # More tokens for detailed positioning reasoning
                timeout=90
            )

            # Parse JSON response
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                # Extract JSON from markdown code block
                lines = response.split('\n')
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith('```'):
                        in_block = not in_block
                        continue
                    if in_block or (not line.startswith('```')):
                        json_lines.append(line)
                response = '\n'.join(json_lines)

            layout_data = json.loads(response)

            # Apply positions from LLM
            positioned_vars = []
            for new_var in new_variables:
                var_copy = new_var.copy()

                # Find position from LLM response
                for pos in layout_data.get('positions', []):
                    if pos['name'] == new_var['name']:
                        var_copy['x'] = pos['x']
                        var_copy['y'] = pos['y']
                        print(f"  {new_var['name']}: ({pos['x']}, {pos['y']})")
                        break
                else:
                    # LLM didn't provide position, use fallback
                    print(f"  Warning: No position for {new_var['name']}, using fallback")
                    x, y = self._fallback_position(new_var, existing_variables, positioned_vars)
                    var_copy['x'] = x
                    var_copy['y'] = y

                positioned_vars.append(var_copy)

            return positioned_vars

        except Exception as e:
            print(f"Warning: LLM positioning failed: {e}")
            print("Falling back to grid positioning")
            return self._fallback_grid_positions(existing_variables, new_variables)

    def _fallback_grid_positions(
        self,
        existing_variables: List[Dict],
        new_variables: List[Dict]
    ) -> List[Dict]:
        """Simple grid-based positioning fallback."""
        positioned_vars = []

        # Find rightmost edge of existing diagram
        max_x = max([v.get('x', 0) for v in existing_variables], default=0) + 500

        for i, var in enumerate(new_variables):
            var_copy = var.copy()
            var_type = var.get('type', 'Auxiliary')

            # Grid layout by type
            if var_type == 'Stock':
                x = max_x + (i % 3) * 250
                y = 300 + (i // 3) * 150
            elif var_type == 'Flow':
                x = max_x + (i % 3) * 250
                y = 200 + (i // 3) * 150
            else:  # Auxiliary
                x = max_x + (i % 3) * 250
                y = 400 + (i // 3) * 150

            var_copy['x'] = x
            var_copy['y'] = y
            positioned_vars.append(var_copy)

        return positioned_vars

    def _fallback_position(
        self,
        var: Dict,
        existing_variables: List[Dict],
        positioned_vars: List[Dict]
    ) -> Tuple[int, int]:
        """Calculate fallback position for single variable."""
        all_vars = existing_variables + positioned_vars
        max_x = max([v.get('x', 0) for v in all_vars], default=0) + 200

        var_type = var.get('type', 'Auxiliary')
        if var_type == 'Stock':
            return (max_x, 300)
        elif var_type == 'Flow':
            return (max_x, 200)
        else:
            return (max_x, 400)

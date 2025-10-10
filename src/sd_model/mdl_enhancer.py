#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDL Enhancement Processor

Applies theory enhancement operations to existing MDL files:
- Add new variables with smart positioning
- Add new connections (displayed as black lines in Vensim)
- Modify existing variables
- Remove/deprecate variables
- Optional color highlighting for changes

Color Scheme (for variable borders):
- Green (0-255-0): New additions
- Orange (255-165-0): Modifications (better visibility than yellow)
- Red (255-0-0): Removals/deprecations

Note: Connection line colors don't work reliably in Vensim,
so new connections appear as default black lines.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
from .mdl_parser import MDLParser
from .generate_mdl import generate_mdl


class MDLEnhancer:
    """Applies theory enhancement operations to MDL models."""

    def __init__(self, mdl_path: Path):
        """Initialize enhancer with existing MDL file."""
        self.mdl_path = mdl_path
        self.parser = MDLParser(mdl_path)
        self.model_data = self.parser.parse()

        # Extract current state
        self.variables = self.model_data['variables']
        self.connections = self.model_data['connections']
        self.valves = self.model_data['valves']
        self.clouds = self.model_data['clouds']
        self.flows = self.model_data['flows']

        # Build mappings
        self.name_to_id = {v['name']: v['id'] for v in self.variables}
        self.id_to_name = {v['id']: v['name'] for v in self.variables}

        # Track next available IDs
        self.next_var_id = max([v['id'] for v in self.variables]) + 1 if self.variables else 1
        self.next_conn_id = max([int(c['id']) for c in self.connections]) + 1 if self.connections else 1

    def apply_enhancements(
        self,
        enhancement_json: Dict,
        output_path: Path,
        add_colors: bool = True
    ) -> Dict[str, Any]:
        """
        Apply theory enhancement operations to the model.

        Args:
            enhancement_json: Enhancement specification
            output_path: Where to save the enhanced MDL
            add_colors: Whether to add color highlights for changes

        Returns:
            Summary of changes made
        """
        summary = {
            'variables_added': 0,
            'connections_added': 0,
            'variables_modified': 0,
            'variables_removed': 0
        }

        # Process all enhancement suggestions
        for suggestion in enhancement_json.get('missing_from_theories', []):
            sd_impl = suggestion.get('sd_implementation', {})

            # Add new variables
            new_vars = sd_impl.get('new_variables', [])
            for var_spec in new_vars:
                self._add_variable(var_spec, add_colors)
                summary['variables_added'] += 1

            # Add new connections
            new_conns = sd_impl.get('new_connections', [])
            for conn_spec in new_conns:
                self._add_connection(conn_spec)
                summary['connections_added'] += 1

        # Generate the enhanced MDL
        self._generate_output(output_path)

        return summary

    def _add_variable(self, var_spec: Dict, add_color: bool = True):
        """Add a new variable to the model with smart positioning."""
        var_name = var_spec['name']
        var_type = var_spec['type']  # Stock, Flow, Auxiliary

        # Handle duplicates by adding _1 suffix
        if var_name in self.name_to_id:
            original_name = var_name
            var_name = f"{var_name}_1"
            print(f"Warning: Variable '{original_name}' already exists, renaming to '{var_name}'")

        # Calculate position
        position = self._calculate_position(var_name, var_type, var_spec)

        # Create variable entry
        new_var = {
            'id': self.next_var_id,
            'name': var_name,
            'type': var_type,
            'x': position[0],
            'y': position[1],
            'width': self._get_default_width(var_type),
            'height': self._get_default_height(var_type)
        }

        # Add green border color for new variables
        if add_color:
            new_var['color'] = {'border': '0-255-0'}  # Green for new additions

        self.variables.append(new_var)
        self.name_to_id[var_name] = self.next_var_id
        self.id_to_name[self.next_var_id] = var_name
        self.next_var_id += 1

    def _add_connection(self, conn_spec: Dict):
        """Add a new connection between variables."""
        from_var = conn_spec['from']
        to_var = conn_spec['to']
        relationship = conn_spec.get('relationship', 'positive')

        # Skip if variables don't exist
        if from_var not in self.name_to_id or to_var not in self.name_to_id:
            print(f"Warning: Skipping connection {from_var} → {to_var} (variable not found)")
            return

        new_conn = {
            'id': str(self.next_conn_id),
            'from_var': from_var,
            'to_var': to_var,
            'relationship': relationship,
            'source': 'enhancement'
        }

        self.connections.append(new_conn)
        self.next_conn_id += 1

    def _calculate_position(
        self,
        var_name: str,
        var_type: str,
        var_spec: Dict
    ) -> Tuple[int, int]:
        """
        Calculate smart position for new variable.

        Strategy:
        1. Find connected existing variables (if any)
        2. Place near connected variables
        3. Apply offset based on variable type
        4. Avoid overlaps
        """
        # Get connected variables from enhancement spec
        connected_vars = self._find_connected_vars(var_name, var_spec)

        if connected_vars:
            # Place near connected variables
            avg_x, avg_y = self._average_position(connected_vars)

            # Apply type-specific offset
            if var_type == 'Stock':
                x, y = avg_x, avg_y + 100  # Below connected vars
            elif var_type == 'Flow':
                x, y = avg_x + 150, avg_y  # To the right
            else:  # Auxiliary
                x, y = avg_x, avg_y - 100  # Above connected vars
        else:
            # No connections - use grid layout
            x, y = self._next_grid_position(var_type)

        # Avoid overlaps
        x, y = self._avoid_overlaps(x, y, var_type)

        return (x, y)

    def _find_connected_vars(self, var_name: str, var_spec: Dict) -> List[str]:
        """Find variables that will connect to this new variable."""
        # This would require looking at the full enhancement spec
        # For now, return empty list (will use grid positioning)
        return []

    def _average_position(self, var_names: List[str]) -> Tuple[int, int]:
        """Calculate average position of given variables."""
        positions = []
        for name in var_names:
            for v in self.variables:
                if v['name'] == name:
                    positions.append((v['x'], v['y']))

        if not positions:
            return (500, 400)  # Default center

        avg_x = sum(p[0] for p in positions) // len(positions)
        avg_y = sum(p[1] for p in positions) // len(positions)
        return (avg_x, avg_y)

    def _next_grid_position(self, var_type: str) -> Tuple[int, int]:
        """Get next available grid position based on variable type."""
        # Simple grid layout
        if var_type == 'Stock':
            # Place stocks on main horizontal line
            y = 300
            stocks = [v for v in self.variables if v['type'] == 'Stock']
            x = 200 + len(stocks) * 250
        elif var_type == 'Flow':
            # Place flows above stocks
            y = 200
            flows = [v for v in self.variables if v['type'] == 'Flow']
            x = 200 + len(flows) * 250
        else:  # Auxiliary
            # Place auxiliaries below stocks
            y = 400
            auxs = [v for v in self.variables if v['type'] == 'Auxiliary']
            x = 200 + len(auxs) * 250

        return (x, y)

    def _avoid_overlaps(self, x: int, y: int, var_type: str) -> Tuple[int, int]:
        """Adjust position to avoid overlapping with existing variables."""
        width = self._get_default_width(var_type)
        height = self._get_default_height(var_type)
        min_spacing = 50

        adjusted_x, adjusted_y = x, y
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            overlaps = False
            for v in self.variables:
                # Check bounding box overlap
                if (abs(adjusted_x - v['x']) < (width + v['width']) // 2 + min_spacing and
                    abs(adjusted_y - v['y']) < (height + v['height']) // 2 + min_spacing):
                    overlaps = True
                    # Shift right
                    adjusted_x += width + min_spacing
                    break

            if not overlaps:
                break
            iteration += 1

        return (adjusted_x, adjusted_y)

    def _get_default_width(self, var_type: str) -> int:
        """Get default width for variable type."""
        if var_type == 'Stock':
            return 60
        elif var_type == 'Flow':
            return 50
        else:  # Auxiliary
            return 70

    def _get_default_height(self, var_type: str) -> int:
        """Get default height for variable type."""
        return 26  # Standard height for all types

    def _generate_output(self, output_path: Path):
        """Generate the enhanced MDL file."""
        # Prepare data for generator
        vars_json = {'variables': self.variables}
        conns_json = {'connections': self.connections}
        plumbing_json = {
            'valves': self.valves,
            'clouds': self.clouds,
            'flows': self.flows,
            'flow_connections': self.model_data.get('flow_connections', [])
        }

        # Generate MDL
        mdl_text = generate_mdl(
            vars_json,
            conns_json,
            plumbing_json,
            with_control=True,
            markers='std'
        )

        output_path.write_text(mdl_text, encoding='utf-8')


def apply_enhancements(
    mdl_path: Path,
    enhancement_json_path: Path,
    output_path: Path,
    add_colors: bool = True
) -> Dict[str, Any]:
    """
    Apply theory enhancement operations to an MDL file.

    Args:
        mdl_path: Path to existing MDL file
        enhancement_json_path: Path to enhancement JSON
        output_path: Where to save enhanced MDL
        add_colors: Whether to add color highlights

    Returns:
        Summary of changes made
    """
    # Load enhancement specification
    with open(enhancement_json_path) as f:
        enhancement_json = json.load(f)

    # Create enhancer and apply changes
    enhancer = MDLEnhancer(mdl_path)
    summary = enhancer.apply_enhancements(enhancement_json, output_path, add_colors)

    return summary

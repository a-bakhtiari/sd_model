#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDL Text Patching Enhancement

Instead of regenerating the entire MDL from JSON, this module patches the original
MDL text by inserting new elements while preserving all original structure.

This approach:
- Preserves all flow structures (valves, clouds, connections)
- Preserves original formatting
- Only adds new elements as text insertions
- Avoids regeneration bugs
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import re
from .mdl_layout_optimizer import MDLLayoutOptimizer
from .llm.client import LLMClient


class MDLTextPatcher:
    """Patches MDL files by text insertion instead of full regeneration."""

    def __init__(self, mdl_path: Path):
        """Initialize patcher with original MDL file."""
        self.mdl_path = mdl_path
        self.content = mdl_path.read_text(encoding='utf-8')
        self.lines = self.content.split('\n')

        # Track insertion points
        self.equation_insert_line = None
        self.sketch_var_insert_line = None
        self.sketch_conn_insert_line = None

        # Track used IDs
        self.max_var_id = 0
        self.max_conn_id = 0

        self._find_insertion_points()

    def _find_insertion_points(self):
        """Find where to insert new elements in the MDL text."""
        in_sketch = False
        last_equation_line = 0
        last_var_line = 0
        last_conn_line = 0

        for i, line in enumerate(self.lines):
            # Find equation section end (before Control block or sketch)
            if '********************************************************' in line and '.Control' in self.lines[i+1] if i+1 < len(self.lines) else False:
                self.equation_insert_line = i
            elif '---///' in line or '\\\\\\---///' in line:
                if self.equation_insert_line is None:
                    self.equation_insert_line = i
                in_sketch = True

            # In sketch section
            if in_sketch:
                # Track variable lines (Type 10)
                if line.startswith('10,'):
                    last_var_line = i
                    # Extract variable ID
                    parts = line.split(',')
                    if len(parts) > 1:
                        try:
                            var_id = int(parts[1])
                            self.max_var_id = max(self.max_var_id, var_id)
                        except ValueError:
                            pass

                # Track connection lines (Type 1)
                elif line.startswith('1,'):
                    last_conn_line = i
                    # Extract connection ID
                    parts = line.split(',')
                    if len(parts) > 1:
                        try:
                            conn_id = int(parts[1])
                            self.max_conn_id = max(self.max_conn_id, conn_id)
                        except ValueError:
                            pass

        # Set insertion points after last found elements
        self.sketch_var_insert_line = last_var_line + 1 if last_var_line > 0 else None
        self.sketch_conn_insert_line = last_conn_line + 1 if last_conn_line > 0 else None

    def add_enhancements(
        self,
        new_variables: List[Dict],
        new_connections: List[Dict],
        add_colors: bool = True,
        use_llm_layout: bool = False,
        llm_client: Optional[LLMClient] = None,
        color_scheme: str = "theory"
    ) -> str:
        """
        Add new variables and connections to the MDL.

        Args:
            new_variables: List of variable specs with name, type, x, y
            new_connections: List of connection specs with from_var, to_var, relationship
            add_colors: Whether to add green color to new variables
            use_llm_layout: Whether to use LLM for intelligent positioning
            llm_client: Optional LLM client for layout optimization

        Returns:
            Enhanced MDL content as string
        """
        lines = self.lines.copy()

        # Build name→ID mapping from existing variables
        name_to_id = self._build_name_to_id_map()

        # Optimize layout if requested
        if use_llm_layout:
            existing_vars = self._extract_existing_variables()
            optimizer = MDLLayoutOptimizer(llm_client)
            new_variables = optimizer.optimize_positions(
                existing_vars,
                new_variables,
                new_connections
            )

        # Step 1: Add new variable equations
        equation_lines = []
        for var in new_variables:
            var_name = var['name']
            # Find dependencies from connections
            deps = self._find_dependencies(var_name, new_connections, name_to_id)

            equation_lines.append(f"{self._quote_name(var_name)}  = A FUNCTION OF( {deps})")
            equation_lines.append("\t~\t")
            equation_lines.append("\t~\t\t|")
            equation_lines.append("")

        if equation_lines and self.equation_insert_line:
            lines[self.equation_insert_line:self.equation_insert_line] = equation_lines
            # Adjust insertion points for sketch section
            offset = len(equation_lines)
            if self.sketch_var_insert_line:
                self.sketch_var_insert_line += offset
            if self.sketch_conn_insert_line:
                self.sketch_conn_insert_line += offset

        # Step 2: Add new variable sketch elements (Type 10)
        sketch_var_lines = []
        var_id_map = {}  # Map variable names to their new IDs

        for var in new_variables:
            self.max_var_id += 1
            var_id_map[var['name']] = self.max_var_id

            var_name = self._quote_name(var['name'])
            var_type = var.get('type', 'Auxiliary')
            x = var.get('x', 500)
            y = var.get('y', 300)
            width = var.get('width', 60)
            height = var.get('height', 26)

            # Type codes: 3=Stock, 40=Flow, 8=Auxiliary
            type_code = 3 if var_type == 'Stock' else (40 if var_type == 'Flow' else 8)

            # Build variable line
            if add_colors:
                # Select color based on scheme
                if color_scheme == "archetype":
                    border_color = "128-0-128"  # Purple for archetypes
                else:
                    border_color = "0-255-0"  # Green for theory enhancements

                # Extended format with colored border
                line = (
                    f"10,{self.max_var_id},{var_name},"
                    f"{x},{y},{width},{height},"
                    f"{type_code},3,0,1,-1,1,0,0,{border_color},0-0-0,|||0-0-0,0,0,0,0,0,0"
                )
            else:
                # Standard format
                line = (
                    f"10,{self.max_var_id},{var_name},"
                    f"{x},{y},{width},{height},"
                    f"{type_code},3,0,0,-1,0,0,0,0,0,0,0,0,0"
                )

            sketch_var_lines.append(line)

        if sketch_var_lines and self.sketch_var_insert_line:
            lines[self.sketch_var_insert_line:self.sketch_var_insert_line] = sketch_var_lines
            # Adjust connection insertion point
            offset = len(sketch_var_lines)
            if self.sketch_conn_insert_line:
                self.sketch_conn_insert_line += offset

        # Step 3: Add new connections (Type 1)
        sketch_conn_lines = []

        for conn in new_connections:
            from_var = conn['from']
            to_var = conn['to']

            # Get IDs (from existing or newly added)
            from_id = var_id_map.get(from_var) or name_to_id.get(from_var)
            to_id = var_id_map.get(to_var) or name_to_id.get(to_var)

            if from_id is None or to_id is None:
                print(f"Warning: Skipping connection {from_var} → {to_var} (variable not found)")
                continue

            self.max_conn_id += 1

            # Select color based on scheme
            if add_colors:
                if color_scheme == "archetype":
                    conn_color = "128,0,128"  # Purple for archetypes
                else:
                    conn_color = "0,192,0"  # Green for theory enhancements
            else:
                conn_color = "0,0,0"  # Black for no colors

            # Standard influence connection
            line = f"1,{self.max_conn_id},{from_id},{to_id},0,0,0,22,{conn_color},-1--1--1,,1|(0,0)|"
            sketch_conn_lines.append(line)

        if sketch_conn_lines and self.sketch_conn_insert_line:
            lines[self.sketch_conn_insert_line:self.sketch_conn_insert_line] = sketch_conn_lines

        return '\n'.join(lines)

    def _build_name_to_id_map(self) -> Dict[str, int]:
        """Build mapping from variable names to IDs."""
        name_to_id = {}

        for line in self.lines:
            if line.startswith('10,'):
                parts = line.split(',')
                if len(parts) > 2:
                    try:
                        var_id = int(parts[1])
                        var_name = parts[2].strip()
                        # Remove quotes if present
                        if var_name.startswith('"') and var_name.endswith('"'):
                            var_name = var_name[1:-1].replace('""', '"')
                        name_to_id[var_name] = var_id
                    except (ValueError, IndexError):
                        pass

        return name_to_id

    def _find_dependencies(
        self,
        var_name: str,
        connections: List[Dict],
        name_to_id: Dict[str, int]
    ) -> str:
        """Find dependencies for a variable from connections."""
        deps = []

        for conn in connections:
            if conn['to'] == var_name:
                from_var = conn['from']
                relationship = conn.get('relationship', 'positive')

                # Add sign prefix for negative relationships
                prefix = '-' if relationship == 'negative' else ''
                deps.append(f"{prefix}{self._quote_name(from_var)}")

        return ','.join(deps) if deps else ''

    def _quote_name(self, name: str) -> str:
        """Quote variable name if it contains special characters."""
        needs_quotes = any(c in name for c in [',', '(', ')', '|', '"']) or (name != name.strip())
        if needs_quotes:
            return '"' + name.replace('"', '""') + '"'
        return name

    def _extract_existing_variables(self) -> List[Dict]:
        """Extract all existing variables with positions for layout optimization."""
        variables = []

        for line in self.lines:
            if line.startswith('10,'):
                parts = line.split(',')
                if len(parts) > 7:
                    try:
                        var_id = int(parts[1])
                        var_name = parts[2].strip()
                        # Remove quotes
                        if var_name.startswith('"') and var_name.endswith('"'):
                            var_name = var_name[1:-1].replace('""', '"')
                        x = int(parts[3])
                        y = int(parts[4])
                        type_code = int(parts[7])

                        # Determine type
                        var_type = 'Stock' if type_code == 3 else ('Flow' if type_code == 40 else 'Auxiliary')

                        variables.append({
                            'id': var_id,
                            'name': var_name,
                            'x': x,
                            'y': y,
                            'type': var_type
                        })
                    except (ValueError, IndexError):
                        pass

        return variables


def apply_text_patch_enhancements(
    mdl_path: Path,
    new_variables: List[Dict],
    new_connections: List[Dict],
    output_path: Path,
    add_colors: bool = True,
    use_llm_layout: bool = False,
    llm_client: Optional[LLMClient] = None
) -> Dict[str, int]:
    """
    Apply enhancements to MDL using text patching approach.

    Args:
        mdl_path: Path to original MDL file
        new_variables: List of new variable specs
        new_connections: List of new connection specs
        output_path: Where to save enhanced MDL
        add_colors: Whether to add color highlights
        use_llm_layout: Whether to use LLM for intelligent positioning
        llm_client: Optional LLM client for layout

    Returns:
        Summary dict with counts
    """
    patcher = MDLTextPatcher(mdl_path)
    enhanced_content = patcher.add_enhancements(
        new_variables,
        new_connections,
        add_colors,
        use_llm_layout,
        llm_client
    )

    output_path.write_text(enhanced_content, encoding='utf-8')

    return {
        'variables_added': len(new_variables),
        'connections_added': len(new_connections)
    }


def apply_theory_enhancements(
    mdl_path: Path,
    enhancement_json: Dict,
    output_path: Path,
    add_colors: bool = True,
    use_llm_layout: bool = False,
    llm_client: Optional[LLMClient] = None,
    color_scheme: str = "theory"
) -> Dict[str, int]:
    """
    Apply theory-based enhancements to MDL from new format.

    Args:
        mdl_path: Path to original MDL file
        enhancement_json: Theory enhancement dict with new format:
            {"theories": [{"name": ..., "additions": {...}, "modifications": {...}, "removals": {...}}]}
        output_path: Where to save enhanced MDL
        add_colors: Whether to add color highlights
        use_llm_layout: Whether to use LLM for intelligent positioning
        llm_client: Optional LLM client for layout

    Returns:
        Summary dict with counts
    """
    # Collect all additions from all theories
    all_new_variables = []
    all_new_connections = []

    for theory in enhancement_json.get('theories', []):
        additions = theory.get('additions', {})

        # Extract variables
        for var_spec in additions.get('variables', []):
            all_new_variables.append({
                'name': var_spec['name'],
                'type': var_spec['type'],
                'description': var_spec.get('description', '')
            })

        # Extract connections
        for conn_spec in additions.get('connections', []):
            all_new_connections.append({
                'from': conn_spec['from'],
                'to': conn_spec['to'],
                'relationship': conn_spec.get('relationship', 'positive')
            })

    # Apply using text patcher
    patcher = MDLTextPatcher(mdl_path)
    enhanced_content = patcher.add_enhancements(
        all_new_variables,
        all_new_connections,
        add_colors,
        use_llm_layout,
        llm_client,
        color_scheme
    )

    output_path.write_text(enhanced_content, encoding='utf-8')

    return {
        'variables_added': len(all_new_variables),
        'connections_added': len(all_new_connections),
        'theories_processed': len(enhancement_json.get('theories', []))
    }

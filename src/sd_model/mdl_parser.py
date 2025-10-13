#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDL Parser - Extract complete structure from Vensim MDL files.

Extracts:
- Variables with IDs, names, types, positions, sizes
- Connections (Type 1 lines) with from/to relationships
- Flows/valves (Type 11) and clouds (Type 12)
- Equations and dependencies
"""

import csv
import io
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class MDLParser:
    """Parse MDL files to extract complete model structure."""

    def __init__(self, mdl_path: Path):
        self.mdl_path = mdl_path
        self.content = mdl_path.read_text(encoding='utf-8', errors='ignore')
        self.lines = self.content.split('\n')

        # Results
        self.variables: List[Dict] = []
        self.connections: List[Dict] = []
        self.valves: List[Dict] = []
        self.clouds: List[Dict] = []
        self.flows: List[Dict] = []
        self.equations: Dict[str, str] = {}

        # Mappings
        self.id_to_name: Dict[int, str] = {}
        self.name_to_id: Dict[str, int] = {}

    def parse(self) -> Dict[str, Any]:
        """Parse the MDL file and return structured data."""
        # Find sketch section
        sketch_start = self._find_sketch_start()

        if sketch_start == -1:
            raise ValueError("No sketch section found in MDL")

        # Parse equations (before sketch)
        self._parse_equations(self.lines[:sketch_start])

        # Parse sketch section
        self._parse_sketch(self.lines[sketch_start:])

        # Build connections from dependencies
        self._extract_connections_from_equations()

        # Assemble flows from raw connections
        self._assemble_flows()

        return {
            'variables': self.variables,
            'connections': self.connections,
            'valves': self.valves,
            'clouds': self.clouds,
            'flows': self.flows,
            'equations': self.equations,
            'flow_connections': getattr(self, 'flow_connections', [])
        }

    def _find_sketch_start(self) -> int:
        """Find the start of the sketch section."""
        for i, line in enumerate(self.lines):
            if '\\\\\\---///' in line or '--///' in line:
                return i
        return -1

    def _parse_equations(self, lines: List[str]):
        """Parse equation section to extract variables and dependencies."""
        # Use regex to find equations
        text = '\n'.join(lines)

        # Pattern for: Variable = A FUNCTION OF(...) or Variable = expression
        pattern = r'^([^=\n]+?)\s*=\s*(.+?)\s*~'
        regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

        for match in regex.finditer(text):
            var_name = match.group(1).strip()
            equation = match.group(2).strip()

            # Remove quotes from variable name
            var_name = self._unquote(var_name)

            # Clean up equation (remove line continuations)
            equation = equation.replace('\\\n', ' ')
            equation = ' '.join(equation.split())

            self.equations[var_name] = equation

    def _parse_sketch(self, lines: List[str]):
        """Parse sketch section to extract visual elements."""
        # First pass: parse variables, valves, and clouds
        for line in lines:
            line = line.strip()

            if not line or line.startswith('*') or line.startswith('$'):
                continue

            if line.startswith('10,'):
                # Variable node
                self._parse_variable(line)
            elif line.startswith('11,'):
                # Flow valve
                self._parse_valve(line)
            elif line.startswith('12,'):
                # Cloud
                self._parse_cloud(line)
            elif '///---' in line:
                # End of sketch
                break

        # Second pass: parse connections (after we know all valves/clouds)
        for line in lines:
            line = line.strip()

            if line.startswith('1,'):
                # Connection
                self._parse_connection(line)
            elif '///---' in line:
                # End of sketch
                break

    def _parse_variable(self, line: str):
        """Parse a Type 10 variable line."""
        try:
            # Use CSV reader to handle quoted fields
            reader = csv.reader(io.StringIO(line))
            parts = next(reader)

            if len(parts) < 8:
                return

            var_id = int(parts[1])
            name = self._unquote(parts[2])
            x = int(parts[3])
            y = int(parts[4])
            width = int(parts[5])
            height = int(parts[6])
            type_code = int(parts[7])

            # Determine variable type from type code
            # 3 = Stock, 8 = Auxiliary, 40 = Flow/Rate
            if type_code == 3:
                var_type = 'Stock'
            elif type_code == 40:
                var_type = 'Flow'
            else:
                var_type = 'Auxiliary'

            # Check for color (extended format with 27 fields)
            color = None
            if len(parts) >= 27:
                # Look for RGB color pattern
                for i in range(14, min(20, len(parts))):
                    if '-' in parts[i] and len(parts[i].split('-')) == 3:
                        color = parts[i]  # e.g., "0-255-0" for green
                        break

            # Handle duplicate variable names by adding _N suffix
            original_name = name
            counter = 1
            seen_names = [v['name'] for v in self.variables]
            while name in seen_names:
                name = f"{original_name}_{counter}"
                counter += 1

            if name != original_name:
                print(f"Warning: Duplicate variable '{original_name}' (ID {var_id}), renamed to '{name}'")

            variable = {
                'id': var_id,
                'name': name,
                'type': var_type,
                'x': x,
                'y': y,
                'width': width,
                'height': height
            }

            if color:
                variable['color'] = {'border': color}

            self.variables.append(variable)
            self.id_to_name[var_id] = name
            self.name_to_id[name] = var_id

        except (ValueError, IndexError) as e:
            print(f"Error parsing variable line: {line}")
            print(f"Error: {e}")

    def _parse_connection(self, line: str):
        """Parse a Type 1 connection line."""
        try:
            # Extract points from the end of line (after |...|)
            points = []
            if '|' in line:
                # Find the last occurrence of |...|
                last_pipe = line.rfind('|')
                second_last = line.rfind('|', 0, last_pipe)
                if second_last != -1:
                    points_str = line[second_last+1:last_pipe]
                    # Parse points like (x,y)(x2,y2), including negative coordinates
                    import re
                    point_pattern = r'\((-?\d+),(-?\d+)\)'
                    for match in re.finditer(point_pattern, points_str):
                        x = int(match.group(1))
                        y = int(match.group(2))
                        points.append([x, y])

            reader = csv.reader(io.StringIO(line))
            parts = next(reader)

            if len(parts) < 4:
                return

            conn_id = parts[1]
            from_id = int(parts[2])
            to_id = int(parts[3])

            # Store connection parameters for proper recreation
            params = {
                'field3': parts[4] if len(parts) > 4 else '0',
                'field4': parts[5] if len(parts) > 5 else '0',
                'field5': parts[6] if len(parts) > 6 else '0',
                'field6': parts[7] if len(parts) > 7 else '0'
            }

            # Check if this is a flow connection (involves valves or clouds)
            valve_ids = {v['id'] for v in self.valves}
            cloud_ids = {c['id'] for c in self.clouds}

            if from_id in valve_ids or to_id in valve_ids:
                # This is part of a flow structure
                if not hasattr(self, 'flow_connections'):
                    self.flow_connections = []

                flow_conn = {
                    'id': conn_id,  # Preserve original connection ID
                    'from_id': from_id,
                    'to_id': to_id,
                    'params': params
                }
                if points:
                    flow_conn['points'] = points
                self.flow_connections.append(flow_conn)
            else:
                # Regular influence connection - use ID-based format for compatibility
                connection = {
                    'id': conn_id,
                    'from': from_id,
                    'to': to_id,
                    'polarity': 'UNDECLARED',  # Will be determined from equations
                    'params': params  # Store original parameters
                }
                if points:
                    connection['points'] = points
                self.connections.append(connection)

        except (ValueError, IndexError) as e:
            print(f"Error parsing connection: {line}")


    def _get_endpoint_ref(self, endpoint_id: int, cloud_ids: set) -> Dict[str, Any]:
        """Get endpoint reference for a flow."""
        if endpoint_id in cloud_ids:
            return {'kind': 'cloud', 'ref': endpoint_id}
        elif endpoint_id in self.name_to_id.values():
            name = self.id_to_name.get(endpoint_id)
            if name:
                var = next((v for v in self.variables if v['name'] == name), None)
                if var:
                    kind = 'stock' if var['type'] == 'Stock' else 'aux'
                    return {'kind': kind, 'ref': name}
        return {'kind': 'unknown', 'ref': endpoint_id}

    def _parse_valve(self, line: str):
        """Parse a Type 11 flow valve line."""
        try:
            reader = csv.reader(io.StringIO(line))
            parts = next(reader)

            if len(parts) < 7:
                return

            valve_id = int(parts[1])
            x = int(parts[3])
            y = int(parts[4])
            w = int(parts[5])
            h = int(parts[6])

            # Find associated variable name from ID mapping
            var_name = self.id_to_name.get(valve_id + 1)  # Often valve_id + 1
            if not var_name:
                # Try to find by position proximity
                for var in self.variables:
                    if abs(var['x'] - x) < 50 and abs(var['y'] - y) < 50:
                        var_name = var['name']
                        break

            valve = {
                'id': valve_id,
                'var_name': var_name or f'valve_{valve_id}',
                'x': x,
                'y': y,
                'w': w,
                'h': h
            }

            self.valves.append(valve)

        except (ValueError, IndexError) as e:
            print(f"Error parsing valve: {line}")

    def _parse_cloud(self, line: str):
        """Parse a Type 12 cloud line (not comments)."""
        try:
            reader = csv.reader(io.StringIO(line))
            parts = next(reader)

            if len(parts) < 7:
                return

            cloud_id = int(parts[1])
            code = int(parts[2])
            x = int(parts[3])
            y = int(parts[4])
            w = int(parts[5])
            h = int(parts[6])

            # Only add actual clouds (code 48), skip comments (code 0)
            if code != 48:
                return

            cloud = {
                'id': cloud_id,
                'code': code,
                'x': x,
                'y': y,
                'w': w,
                'h': h
            }

            self.clouds.append(cloud)

        except (ValueError, IndexError) as e:
            print(f"Error parsing cloud: {line}")

    def _extract_connections_from_equations(self):
        """Extract dependency relationships from equations."""
        next_conn_id = max([int(c['id']) for c in self.connections] + [0]) + 100

        for var_name, equation in self.equations.items():
            if 'A FUNCTION OF' in equation:
                # Parse dependencies from FUNCTION OF
                # Handle nested parentheses in quoted variable names
                start = equation.find('A FUNCTION OF')
                if start != -1:
                    start = equation.find('(', start)
                    if start != -1:
                        # Find matching closing paren
                        paren_count = 1
                        in_quotes = False
                        end = start + 1
                        while end < len(equation) and paren_count > 0:
                            char = equation[end]
                            if char == '"':
                                in_quotes = not in_quotes
                            elif not in_quotes:
                                if char == '(':
                                    paren_count += 1
                                elif char == ')':
                                    paren_count -= 1
                            end += 1

                        if paren_count == 0:
                            deps_str = equation[start+1:end-1]
                        else:
                            continue
                    else:
                        continue
                else:
                    continue

                # Handle quoted variable names with commas
                deps = []
                current = ""
                in_quotes = False

                for char in deps_str:
                    if char == '"':
                        in_quotes = not in_quotes
                        current += char
                    elif char == ',' and not in_quotes:
                        if current.strip():
                            deps.append(current.strip())
                        current = ""
                    else:
                        current += char

                if current.strip():
                    deps.append(current.strip())

                for dep in deps:
                    # Check for sign (negative/positive)
                    relationship = 'positive'
                    if dep.startswith('-'):
                        relationship = 'negative'
                        dep = dep[1:].strip()
                    elif dep.startswith('+'):
                        dep = dep[1:].strip()

                    # Remove quotes
                    dep = self._unquote(dep)

                    # Add or update connection
                    self._add_or_update_connection(dep, var_name, relationship, next_conn_id)
                    next_conn_id += 1

    def _add_or_update_connection(self, from_var: str, to_var: str, relationship: str, conn_id: int):
        """Add or update a connection."""
        # Get variable IDs
        from_id = self.name_to_id.get(from_var)
        to_id = self.name_to_id.get(to_var)

        if not from_id or not to_id:
            return

        # Check if connection already exists
        for conn in self.connections:
            if conn.get('from') == from_id and conn.get('to') == to_id:
                # Update polarity if it was undeclared
                if conn.get('polarity') == 'UNDECLARED':
                    polarity = 'POSITIVE' if relationship == 'positive' else ('NEGATIVE' if relationship == 'negative' else 'UNDECLARED')
                    conn['polarity'] = polarity
                return

        # Add new connection (from equation) - use ID-based format
        polarity = 'POSITIVE' if relationship == 'positive' else ('NEGATIVE' if relationship == 'negative' else 'UNDECLARED')
        connection = {
            'id': str(conn_id),
            'from': from_id,
            'to': to_id,
            'polarity': polarity,
            'source': 'equation'  # Mark as coming from equation analysis
        }
        self.connections.append(connection)

    def _unquote(self, s: str) -> str:
        """Remove quotes from a string."""
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('""', '"')
        return s

    def _assemble_flows(self):
        """Assemble flow structures from raw connections."""
        if not hasattr(self, 'flow_connections'):
            return

        valve_ids = {v['id'] for v in self.valves}
        cloud_ids = {c['id'] for c in self.clouds}

        # Group connections by valve
        valve_connections = {}
        for conn in self.flow_connections:
            from_id = conn['from_id']
            to_id = conn['to_id']

            if from_id in valve_ids:
                if from_id not in valve_connections:
                    valve_connections[from_id] = {'valve_id': from_id, 'endpoints': []}
                valve_connections[from_id]['endpoints'].append(to_id)
            elif to_id in valve_ids:
                if to_id not in valve_connections:
                    valve_connections[to_id] = {'valve_id': to_id, 'endpoints': []}
                valve_connections[to_id]['endpoints'].append(from_id)

        # Build flow structures
        for valve_id, data in valve_connections.items():
            endpoints = data['endpoints']
            if len(endpoints) == 2:
                # Standard flow: endpoint1 -> valve -> endpoint2
                ep1_ref = self._get_endpoint_ref(endpoints[0], cloud_ids)
                ep2_ref = self._get_endpoint_ref(endpoints[1], cloud_ids)

                # Determine direction based on stock/cloud types
                # Generally: stock -> valve -> cloud or stock -> valve -> stock
                if ep1_ref['kind'] == 'cloud':
                    # Cloud is source
                    flow = {
                        'valve_id': valve_id,
                        'from': ep1_ref,
                        'to': ep2_ref
                    }
                elif ep2_ref['kind'] == 'cloud':
                    # Cloud is sink
                    flow = {
                        'valve_id': valve_id,
                        'from': ep1_ref,
                        'to': ep2_ref
                    }
                else:
                    # Stock to stock - need to determine direction from equations
                    # For now, assume first is source
                    flow = {
                        'valve_id': valve_id,
                        'from': ep1_ref,
                        'to': ep2_ref
                    }

                self.flows.append(flow)

    def to_json_files(self, output_dir: Path):
        """Save parsed data to JSON files for the MDL generator."""
        output_dir.mkdir(exist_ok=True, parents=True)

        # Variables JSON
        variables_data = {
            'variables': self.variables
        }
        (output_dir / 'variables.json').write_text(
            json.dumps(variables_data, indent=2)
        )

        # Connections JSON
        connections_data = {
            'connections': self.connections
        }
        (output_dir / 'connections.json').write_text(
            json.dumps(connections_data, indent=2)
        )

        # Plumbing JSON (if flows exist)
        if self.valves or self.clouds or self.flows:
            plumbing_data = {
                'valves': self.valves,
                'clouds': self.clouds,
                'flows': self.flows,
                'flow_connections': getattr(self, 'flow_connections', []),
                'link_points': []  # Could extract from connection geometry
            }
            (output_dir / 'plumbing.json').write_text(
                json.dumps(plumbing_data, indent=2)
            )


def parse_mdl_to_json(mdl_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Parse an MDL file and save to JSON files."""
    parser = MDLParser(mdl_path)
    result = parser.parse()
    parser.to_json_files(output_dir)
    return result
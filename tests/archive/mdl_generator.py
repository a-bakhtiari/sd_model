"""MDL Generator - Applies theory enhancement changes to Vensim MDL files.

This module provides classes to:
1. Parse existing MDL files
2. Apply add/remove/modify operations
3. Generate new MDL files with color-coded changes
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class MDLVariable:
    """Represents a variable in the MDL file."""
    id: int
    name: str
    x: int
    y: int
    width: int
    height: int
    var_type: int  # 3=stock, 8=auxiliary
    equation: str = ""
    color_rgb: Optional[str] = None  # RGB format like "0-255-0"


@dataclass
class MDLConnection:
    """Represents a connection (arrow) in the MDL file."""
    from_id: int
    to_id: int
    line_data: str  # Full line data for the connection
    color_rgb: Optional[str] = None


class MDLParser:
    """Parses MDL files into structured data."""

    def __init__(self, mdl_path: Path):
        """Initialize parser with MDL file path."""
        self.mdl_path = mdl_path
        self.content = mdl_path.read_text(encoding="utf-8")
        self.lines = self.content.split("\n")

        # Data structures
        self.variables: Dict[int, MDLVariable] = {}
        self.name_to_id: Dict[str, int] = {}
        self.connections: List[MDLConnection] = []
        self.equation_lines: List[str] = []
        self.sketch_start_idx: int = 0
        self.sketch_header: List[str] = []
        self.next_var_id: int = 1

    def parse(self):
        """Parse the MDL file into data structures."""
        self._parse_equations()
        self._parse_sketch()

    def _parse_equations(self):
        """Parse the equation section (before sketch)."""
        for i, line in enumerate(self.lines):
            if "\\\\\\---/// Sketch information" in line:
                self.sketch_start_idx = i
                break
            self.equation_lines.append(line)

    def _parse_sketch(self):
        """Parse the sketch section (visual layout)."""
        if self.sketch_start_idx == 0:
            return

        # Store header lines (sketch marker, view definition, style line)
        sketch_lines = self.lines[self.sketch_start_idx:]
        header_count = 0
        for i, line in enumerate(sketch_lines):
            if line.startswith("10,") or line.startswith("1,") or line.startswith("11,") or line.startswith("12,"):
                break
            self.sketch_header.append(line)
            header_count += 1

        # Parse variable lines (10,)
        for line in sketch_lines[header_count:]:
            if line.startswith("10,"):
                var = self._parse_variable_line(line)
                if var:
                    self.variables[var.id] = var
                    self.name_to_id[var.name] = var.id
                    if var.id >= self.next_var_id:
                        self.next_var_id = var.id + 1

            elif line.startswith("1,"):
                conn = self._parse_connection_line(line)
                if conn:
                    self.connections.append(conn)

    def _parse_variable_line(self, line: str) -> Optional[MDLVariable]:
        """Parse a variable line (10,...) handling quoted names with commas."""
        try:
            # Split carefully to handle quoted names with commas
            # Format: 10,id,"name with , commas",x,y,width,height,...
            parts = []
            in_quotes = False
            current = ""

            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append(current)
                    current = ""
                    continue
                current += char
            parts.append(current)  # Add last part

            if len(parts) < 8:
                return None

            var_id = int(parts[1])
            name = parts[2].strip('"')  # Remove quotes from name
            x = int(parts[3])
            y = int(parts[4])
            width = int(parts[5])
            height = int(parts[6])
            var_type = int(parts[7])

            return MDLVariable(
                id=var_id,
                name=name,
                x=x,
                y=y,
                width=width,
                height=height,
                var_type=var_type,
            )
        except (ValueError, IndexError):
            return None

    def _parse_connection_line(self, line: str) -> Optional[MDLConnection]:
        """Parse a connection line (1,...)."""
        parts = line.split(",")
        if len(parts) < 3:
            return None

        try:
            from_id = int(parts[1])
            to_id = int(parts[2])

            return MDLConnection(
                from_id=from_id,
                to_id=to_id,
                line_data=line,
            )
        except (ValueError, IndexError):
            return None


class MDLGenerator:
    """Generates modified MDL files with theory enhancements."""

    def __init__(self, parser: MDLParser):
        """Initialize generator with parsed MDL data."""
        self.parser = parser
        self.changes_log: List[str] = []

    def apply_changes(self, changes: List[Dict]) -> None:
        """Apply all changes from enhancement JSON."""
        for change in changes:
            operation = change.get("operation")
            mdl_comment = change.get("mdl_comment", "")

            if operation == "add_variable":
                self._add_variable(change["variable"], mdl_comment)
            elif operation == "remove_variable":
                self._remove_variable(change["variable"]["name"], mdl_comment)
            elif operation == "add_connection":
                self._add_connection(change["connection"], mdl_comment)
            elif operation == "remove_connection":
                self._remove_connection(change["connection"], mdl_comment)
            elif operation == "modify_connection":
                self._modify_connection(change["connection"], mdl_comment)

    def _add_variable(self, var_data: Dict, comment: str):
        """Add a new variable to the model."""
        name = var_data["name"]
        var_type_str = var_data["type"]
        x = var_data["position"]["x"]
        y = var_data["position"]["y"]
        width = var_data["size"]["width"]
        height = var_data["size"]["height"]
        color = var_data.get("color", {}).get("border", "0-255-0")

        # Map type string to MDL type code
        type_code = 3 if var_type_str == "Stock" else 8  # 3=stock, 8=auxiliary

        # Assign new ID
        new_id = self.parser.next_var_id
        self.parser.next_var_id += 1

        # Create variable
        var = MDLVariable(
            id=new_id,
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            var_type=type_code,
            color_rgb=color,
        )

        self.parser.variables[new_id] = var
        self.parser.name_to_id[name] = new_id
        self.changes_log.append(f"ADD VAR: {name} (ID {new_id}) - {comment}")

    def _remove_variable(self, name: str, comment: str):
        """Remove a variable from the model."""
        if name not in self.parser.name_to_id:
            self.changes_log.append(f"REMOVE VAR FAILED: {name} not found - {comment}")
            return

        var_id = self.parser.name_to_id[name]

        # Mark for removal (we'll actually remove it during generation)
        if var_id in self.parser.variables:
            del self.parser.variables[var_id]
        del self.parser.name_to_id[name]

        # Remove connections referencing this variable
        self.parser.connections = [
            conn for conn in self.parser.connections
            if conn.from_id != var_id and conn.to_id != var_id
        ]

        self.changes_log.append(f"REMOVE VAR: {name} (ID {var_id}) - {comment}")

    def _add_connection(self, conn_data: Dict, comment: str):
        """Add a new connection to the model."""
        from_name = conn_data["from"]
        to_name = conn_data["to"]
        color = conn_data.get("color", "0-255-0")

        # Look up IDs
        if from_name not in self.parser.name_to_id:
            self.changes_log.append(f"ADD CONN FAILED: {from_name} not found - {comment}")
            return
        if to_name not in self.parser.name_to_id:
            self.changes_log.append(f"ADD CONN FAILED: {to_name} not found - {comment}")
            return

        from_id = self.parser.name_to_id[from_name]
        to_id = self.parser.name_to_id[to_name]

        # Create connection line (simplified format)
        line_data = f"1,{from_id},{to_id},1,0,0,0,0,192,0,-1--1--1,,1|(0,0)|"

        conn = MDLConnection(
            from_id=from_id,
            to_id=to_id,
            line_data=line_data,
            color_rgb=color,
        )

        self.parser.connections.append(conn)
        self.changes_log.append(f"ADD CONN: {from_name} → {to_name} - {comment}")

    def _remove_connection(self, conn_data: Dict, comment: str):
        """Remove a connection from the model."""
        from_name = conn_data["from"]
        to_name = conn_data["to"]

        if from_name not in self.parser.name_to_id or to_name not in self.parser.name_to_id:
            self.changes_log.append(f"REMOVE CONN FAILED: Variables not found - {comment}")
            return

        from_id = self.parser.name_to_id[from_name]
        to_id = self.parser.name_to_id[to_name]

        # Remove matching connection
        original_count = len(self.parser.connections)
        self.parser.connections = [
            conn for conn in self.parser.connections
            if not (conn.from_id == from_id and conn.to_id == to_id)
        ]

        removed = original_count - len(self.parser.connections)
        self.changes_log.append(f"REMOVE CONN: {from_name} → {to_name} ({removed} removed) - {comment}")

    def _modify_connection(self, conn_data: Dict, comment: str):
        """Modify an existing connection."""
        from_name = conn_data["from"]
        to_name = conn_data["to"]
        color = conn_data.get("color", "255-165-0")

        if from_name not in self.parser.name_to_id or to_name not in self.parser.name_to_id:
            self.changes_log.append(f"MODIFY CONN FAILED: Variables not found - {comment}")
            return

        from_id = self.parser.name_to_id[from_name]
        to_id = self.parser.name_to_id[to_name]

        # Find and modify connection
        for conn in self.parser.connections:
            if conn.from_id == from_id and conn.to_id == to_id:
                conn.color_rgb = color
                self.changes_log.append(f"MODIFY CONN: {from_name} → {to_name} - {comment}")
                return

        self.changes_log.append(f"MODIFY CONN FAILED: Connection not found - {comment}")

    def generate_mdl(self, output_path: Path) -> None:
        """Generate the modified MDL file."""
        lines = []

        # 1. Write equation section
        lines.append("{UTF-8}")

        # Write equations for all current variables
        for var in sorted(self.parser.variables.values(), key=lambda v: v.id):
            # Simple placeholder equation
            lines.append(f"{var.name}  = A FUNCTION OF( )")
            lines.append("\t~\t")
            lines.append("\t~\t\t|")
            lines.append("")

        # Add simulation control variables
        lines.extend([
            "FINAL TIME  = 100",
            "\t~\tMonth",
            "\t~\tThe final time for the simulation.",
            "\t|",
            "",
            "INITIAL TIME  = 0",
            "\t~\tMonth",
            "\t~\tThe initial time for the simulation.",
            "\t|",
            "",
            "SAVEPER  = ",
            "        TIME STEP",
            "\t~\tMonth [0,?]",
            "\t~\tThe frequency with which output is stored.",
            "\t|",
            "",
            "TIME STEP  = 1",
            "\t~\tMonth [0,?]",
            "\t~\tThe time step for the simulation.",
            "\t|",
            "",
        ])

        # 2. Write sketch section
        lines.extend(self.parser.sketch_header)

        # Write all variables (10, lines)
        for var in sorted(self.parser.variables.values(), key=lambda v: v.id):
            color_part = ""
            if var.color_rgb:
                # Convert RGB string to color codes for border
                # Format: 0,0,-1,0,0,0,0,0,0,0  (default)
                # For colored: 0,2,-1,1,0,0,0-0-0,0-255-0 (text color, border color)
                color_part = f",0,2,-1,1,0,0,0-0-0,{var.color_rgb},|||0-0-0,0,0,0,0,0,0"
            else:
                color_part = ",0,0,-1,0,0,0,0,0,0,0"

            # Add quotes around name if it contains special characters
            name = f'"{var.name}"' if any(c in var.name for c in ['(', ')', ' ', ',', '-', '/']) else var.name
            line = f"10,{var.id},{name},{var.x},{var.y},{var.width},{var.height},{var.var_type},3{color_part}"
            lines.append(line)

        # Write all connections (1, lines)
        for conn in self.parser.connections:
            lines.append(conn.line_data)

        # Write footer
        lines.append("///---\\\\\\")
        lines.append("\t:GRAPH Model")
        lines.append("")

        # Write to file
        output_path.write_text("\n".join(lines), encoding="utf-8")

        print(f"\n✓ Generated MDL file: {output_path}")
        print(f"  Variables: {len(self.parser.variables)}")
        print(f"  Connections: {len(self.parser.connections)}")

    def print_changes_log(self):
        """Print all changes that were applied."""
        print("\n" + "="*80)
        print("CHANGES LOG")
        print("="*80)
        for log in self.changes_log:
            print(f"  {log}")
        print("="*80)

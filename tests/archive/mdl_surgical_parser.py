"""Surgical MDL Parser - Extract sections for targeted edits.

Parses MDL into structured sections without using LLM.
Designed for surgical edits (change specific lines, not regenerate entire file).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class EquationBlock:
    """A variable equation block (3 lines: equation, units, doc|terminator)."""
    var_name: str
    equation_line: str  # The = A FUNCTION OF(...) line (may be multiline)
    units_line: str     # ~ units
    doc_line: str       # ~ description|   (includes terminator |)

    def to_lines(self) -> List[str]:
        """Convert back to lines."""
        return [
            self.equation_line,
            self.units_line,
            self.doc_line
        ]


@dataclass
class SketchVariable:
    """A sketch variable (10, line)."""
    sketch_id: int
    name: str
    full_line: str


class MDLSurgicalParser:
    """Parse MDL for surgical editing."""

    def __init__(self, mdl_path: Path):
        self.mdl_path = mdl_path
        self.content = mdl_path.read_text(encoding="utf-8")
        self.lines = self.content.split("\n")

        # Parsed sections
        self.equations: Dict[str, EquationBlock] = {}
        self.equation_order: List[str] = []  # Preserve order
        self.control_section: List[str] = []
        self.sketch_header: List[str] = []
        self.sketch_vars: Dict[int, SketchVariable] = {}
        self.sketch_other: List[str] = []  # 1, 11, 12 lines
        self.sketch_footer: List[str] = []

        # Mappings
        self.name_to_id: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}
        self.max_id: int = 0

    def parse(self):
        """Parse the MDL file into sections."""
        # Find sketch marker
        sketch_start = -1
        for i, line in enumerate(self.lines):
            if "\\\\\\---/// Sketch information" in line:
                sketch_start = i
                break

        if sketch_start == -1:
            raise ValueError("No sketch section found in MDL file")

        # Parse equation section (before sketch)
        self._parse_equations(self.lines[:sketch_start])

        # Parse sketch section
        self._parse_sketch(self.lines[sketch_start:])

        # Build mappings
        self._build_mappings()

    def _parse_equations(self, lines: List[str]):
        """Parse equation section into blocks."""
        i = 0

        # Skip UTF-8 marker
        if i < len(lines) and "{UTF-8}" in lines[i]:
            i += 1

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Check for control section start
            if "***" in line:
                # Start of control section
                self.control_section = lines[i:]
                break

            # Parse equation block (4+ lines for multiline)
            if "=" in line:
                # Start of equation
                equation_line = line
                lines_consumed = 1

                # Handle multiline equations (\ continuation)
                while equation_line.rstrip().endswith("\\"):
                    if i + lines_consumed < len(lines):
                        equation_line += "\n" + lines[i + lines_consumed]
                        lines_consumed += 1
                    else:
                        break

                # Now get units and doc/terminator (after multiline equation)
                units_idx = i + lines_consumed
                doc_idx = i + lines_consumed + 1

                units_line = lines[units_idx] if units_idx < len(lines) else ""
                doc_line = lines[doc_idx] if doc_idx < len(lines) else ""

                # Extract variable name (before =)
                # Need to handle both quoted and unquoted names
                var_name_raw = equation_line.split("=")[0].strip()

                # Store with quotes if present (for equation reconstruction)
                # But also extract unquoted version for matching
                if var_name_raw.startswith('"') and var_name_raw.endswith('"'):
                    var_name = var_name_raw[1:-1]  # Unquoted for matching
                else:
                    var_name = var_name_raw

                # Store block
                block = EquationBlock(
                    var_name=var_name,
                    equation_line=equation_line,
                    units_line=units_line,
                    doc_line=doc_line
                )
                self.equations[var_name] = block
                self.equation_order.append(var_name)

                # Move past this block (lines_consumed for equation + 2 for ~,~|)
                i += lines_consumed + 2

                # Skip blank line after block
                if i < len(lines) and not lines[i].strip():
                    i += 1
            else:
                i += 1

    def _parse_sketch(self, lines: List[str]):
        """Parse sketch section."""
        # Find sketch end marker
        sketch_end = -1
        for i, line in enumerate(lines):
            if "///---" in line:
                sketch_end = i
                break

        if sketch_end == -1:
            sketch_end = len(lines)

        # Extract header (up to first 10, 1, 11, or 12 line)
        sketch_start = 0
        for i, line in enumerate(lines):
            if line.startswith("10,") or line.startswith("1,") or line.startswith("11,") or line.startswith("12,"):
                sketch_start = i
                break

        self.sketch_header = lines[:sketch_start]

        # Parse sketch content
        for line in lines[sketch_start:sketch_end]:
            if line.startswith("10,"):
                # Variable line
                var = self._parse_sketch_variable(line)
                if var:
                    self.sketch_vars[var.sketch_id] = var
                    if var.sketch_id > self.max_id:
                        self.max_id = var.sketch_id
            else:
                # Connection, flow, cloud, etc.
                self.sketch_other.append(line)

        # Footer (after ///)
        if sketch_end < len(lines):
            self.sketch_footer = lines[sketch_end:]

    def _parse_sketch_variable(self, line: str) -> Optional[SketchVariable]:
        """Parse a 10, sketch variable line."""
        try:
            # Handle quoted names with commas inside
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
            parts.append(current)

            if len(parts) < 4:
                return None

            sketch_id = int(parts[1])
            name = parts[2].strip('"')

            return SketchVariable(
                sketch_id=sketch_id,
                name=name,
                full_line=line
            )
        except (ValueError, IndexError):
            return None

    def _build_mappings(self):
        """Build name ↔ ID mappings."""
        for sketch_id, var in self.sketch_vars.items():
            self.name_to_id[var.name] = sketch_id
            self.id_to_name[sketch_id] = var.name

    def reassemble(self) -> str:
        """Reassemble MDL from parsed sections."""
        lines = []

        # UTF-8 header
        lines.append("{UTF-8}")

        # Equations (preserve order)
        for var_name in self.equation_order:
            if var_name in self.equations:
                block = self.equations[var_name]
                lines.extend(block.to_lines())
                # Add blank line after each block
                lines.append("")

        # Control section
        lines.extend(self.control_section)

        # Sketch header
        lines.extend(self.sketch_header)

        # Sketch variables (sorted by ID)
        for sketch_id in sorted(self.sketch_vars.keys()):
            lines.append(self.sketch_vars[sketch_id].full_line)

        # Other sketch elements (connections, flows, etc.)
        lines.extend(self.sketch_other)

        # Footer
        lines.extend(self.sketch_footer)

        return "\n".join(lines)

    def get_next_id(self) -> int:
        """Get next available ID for new variable."""
        return self.max_id + 1

    def add_equation(self, var_name: str, equation_block: EquationBlock):
        """Add a new equation block."""
        self.equations[var_name] = equation_block
        self.equation_order.append(var_name)

    def remove_equation(self, var_name: str):
        """Remove an equation block."""
        if var_name in self.equations:
            del self.equations[var_name]
            self.equation_order.remove(var_name)

    def update_equation_line(self, var_name: str, new_equation_line: str):
        """Update just the equation line (= A FUNCTION OF(...))."""
        if var_name in self.equations:
            self.equations[var_name].equation_line = new_equation_line

    def add_sketch_variable(self, sketch_id: int, name: str, sketch_line: str):
        """Add a new sketch variable."""
        var = SketchVariable(sketch_id=sketch_id, name=name, full_line=sketch_line)
        self.sketch_vars[sketch_id] = var
        self.name_to_id[name] = sketch_id
        self.id_to_name[sketch_id] = name
        if sketch_id > self.max_id:
            self.max_id = sketch_id

    def remove_sketch_variable(self, sketch_id: int):
        """Remove a sketch variable."""
        if sketch_id in self.sketch_vars:
            name = self.sketch_vars[sketch_id].name
            del self.sketch_vars[sketch_id]
            if name in self.name_to_id:
                del self.name_to_id[name]
            if sketch_id in self.id_to_name:
                del self.id_to_name[sketch_id]

    def remove_connections_referencing(self, sketch_id: int):
        """Remove all connection lines referencing a variable ID."""
        self.sketch_other = [
            line for line in self.sketch_other
            if not (line.startswith("1,") and self._connection_references_id(line, sketch_id))
        ]

    def _connection_references_id(self, line: str, sketch_id: int) -> bool:
        """Check if a connection line references the given ID."""
        parts = line.split(",")
        if len(parts) < 4:
            return False
        try:
            from_id = int(parts[2])
            to_id = int(parts[3])
            return from_id == sketch_id or to_id == sketch_id
        except ValueError:
            return False

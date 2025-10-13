#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDL File Creator from Scratch

Creates a complete MDL file from theory enhancement output,
discarding the original model entirely.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from .llm.client import LLMClient


def create_mdl_from_scratch(
    theory_concretization: Dict,
    output_path: Path,
    llm_client: Optional[LLMClient] = None,
    clustering_scheme: Optional[Dict] = None,
    template_mdl_path: Optional[Path] = None
) -> Dict:
    """
    Create side-by-side model: original on left, theory-generated on right.

    This "recreation" mode keeps the original model and adds theory-generated
    variables to the RIGHT side of the diagram (X offset +3000px). User can
    then manually delete old variables in Vensim if desired.

    This approach:
    - Reuses proven addition mode code (no bugs!)
    - Provides visual comparison between old and new models
    - Gives user control over what to keep/remove
    - Simple implementation with X coordinate offset

    Args:
        theory_concretization: Output from theory_concretization step (step 2)
        output_path: Where to save the MDL file
        llm_client: LLM client for layout optimization
        clustering_scheme: Optional clustering from step 1 for spatial organization
        template_mdl_path: Path to original MDL

    Returns:
        Dict with creation summary
    """
    from .mdl_text_patcher import apply_text_patch_enhancements

    # Extract all variables and connections from theory enhancement
    all_variables = []
    all_connections = []

    processes = theory_concretization.get('processes', [])
    for process in processes:
        process_name = process.get('process_name', 'Unknown')
        variables = process.get('variables', [])
        connections = process.get('connections', [])

        # Add cluster assignment to each variable
        for var in variables:
            var['cluster'] = process_name

        all_variables.extend(variables)
        all_connections.extend(connections)

    if not all_variables:
        return {
            'error': 'No variables found in theory concretization output',
            'variables_added': 0
        }

    if not template_mdl_path or not template_mdl_path.exists():
        return {
            'error': 'Template MDL path required for recreation mode',
            'variables_added': 0
        }

    # Apply X offset to position theory model to the RIGHT of original model
    X_OFFSET = 3000  # Theory model appears 3000px to the right
    for var in all_variables:
        # Add offset to X coordinate (use default 1000 if no position set yet)
        var['x'] = var.get('x', 1000) + X_OFFSET
        # Keep Y coordinate as-is (or use default)
        if 'y' not in var:
            var['y'] = 500

    # Use regular addition mode with offset variables
    # This is proven, stable code that works perfectly
    result = apply_text_patch_enhancements(
        template_mdl_path,
        all_variables,
        all_connections,
        output_path,
        add_colors=False,  # No colors for recreation
        use_llm_layout=True,  # ALWAYS use LLM positioning
        llm_client=llm_client
    )

    return result


def _assign_positions(
    variables: List[Dict],
    connections: List[Dict],
    llm_client: Optional[LLMClient],
    clustering_scheme: Optional[Dict]
) -> List[Dict]:
    """
    Assign X,Y positions to variables using LLM layout.

    Returns list of variables with x, y coordinates added.
    """
    # For recreation mode, always use simple grid layout
    # (LLM-based layout would require the full relayout infrastructure)
    return _simple_grid_layout(variables, clustering_scheme)


def _simple_grid_layout(variables: List[Dict], clustering_scheme: Optional[Dict]) -> List[Dict]:
    """
    Create a simple grid layout when LLM is not available.

    Groups variables by cluster if clustering_scheme is provided.
    """
    positioned = []

    if clustering_scheme:
        # Group by cluster
        clusters = clustering_scheme.get('clusters', [])
        cluster_names = [c.get('name', '') for c in clusters]

        # Organize variables by cluster
        vars_by_cluster = {name: [] for name in cluster_names}
        vars_by_cluster['_unassigned'] = []

        for var in variables:
            cluster = var.get('cluster', '_unassigned')
            if cluster in vars_by_cluster:
                vars_by_cluster[cluster].append(var)
            else:
                vars_by_cluster['_unassigned'].append(var)

        # Position each cluster in a grid
        x_offset = 100
        y_offset = 100
        cluster_spacing = 400

        for cluster_name in cluster_names:
            cluster_vars = vars_by_cluster.get(cluster_name, [])
            for i, var in enumerate(cluster_vars):
                var_copy = var.copy()
                var_copy['x'] = x_offset + (i % 5) * 200
                var_copy['y'] = y_offset + (i // 5) * 150
                positioned.append(var_copy)

            y_offset += cluster_spacing
    else:
        # Simple grid without clustering
        for i, var in enumerate(variables):
            var_copy = var.copy()
            var_copy['x'] = 100 + (i % 10) * 200
            var_copy['y'] = 100 + (i // 10) * 150
            positioned.append(var_copy)

    return positioned


def _parse_llm_positions(response: str) -> Dict[str, Tuple[int, int]]:
    """
    Parse LLM ASCII diagram response to extract variable positions.

    Returns dict mapping variable name -> (x, y)
    """
    import re

    position_map = {}

    # Look for patterns like "Variable Name (x,y)"
    pattern = r'([^(]+)\s*\((\d+),\s*(\d+)\)'

    for match in re.finditer(pattern, response):
        var_name = match.group(1).strip()
        x = int(match.group(2))
        y = int(match.group(3))
        position_map[var_name] = (x, y)

    return position_map


def _generate_mdl_from_template(
    variables: List[Dict],
    connections: List[Dict],
    var_name_to_id: Dict[str, int],
    template_content: Optional[str]
) -> str:
    """
    Generate MDL content using original file as template.

    Preserves control section and formatting from template, but replaces
    all equations and sketch elements with new theory-generated content.

    Returns MDL content as string.
    """
    lines = []

    # Extract control and metadata sections from template if available
    control_section = None
    sketch_header = None
    sketch_footer = None

    if template_content:
        template_lines = template_content.split('\n')

        # Find control section (from .Control to sketch marker)
        control_start = None
        control_end = None
        for i, line in enumerate(template_lines):
            if '.Control' in line:
                control_start = i - 1  # Include the *** line before
            elif line.startswith('\\\\\\---///') and control_start is not None:
                control_end = i
                break

        if control_start is not None and control_end is not None:
            control_section = template_lines[control_start:control_end]

        # Find sketch header (from \\\ to first :)
        sketch_start = None
        sketch_header_end = None
        for i, line in enumerate(template_lines):
            if line.startswith('\\\\\\---///'):
                sketch_start = i
            elif sketch_start is not None and line.startswith(':') and not line.startswith(':GRAPH'):
                sketch_header_end = i + 1
                break

        if sketch_start is not None and sketch_header_end is not None:
            sketch_header = template_lines[sketch_start:sketch_header_end]

        # Find sketch footer (from :GRAPH to end)
        footer_start = None
        for i, line in enumerate(template_lines):
            if line.startswith(':GRAPH') or line.startswith('///---\\\\\\'):
                # Look for the section divider after sketch elements
                if i > sketch_header_end if sketch_header_end else 0:
                    footer_start = i
                    break

        if footer_start is not None:
            sketch_footer = template_lines[footer_start:]

    # Header
    lines.append("{UTF-8}")

    # Equations section - new variables only
    for var in variables:
        var_name = var['name']

        # Find dependencies from connections
        deps = []
        for conn in connections:
            if conn.get('to') == var_name:
                deps.append(conn.get('from', ''))

        # Quote name if needed
        quoted_name = _quote_var_name(var_name)

        if deps:
            deps_str = ",".join([_quote_var_name(d) for d in deps if d])
            lines.append(f"{quoted_name} = A FUNCTION OF( {deps_str} )")
        else:
            lines.append(f"{quoted_name} = A FUNCTION OF( )")
        lines.append("\t~\t")
        lines.append("\t~\t\t|")
        lines.append("")

    # Control section from template or default
    if control_section:
        lines.extend(control_section)
    else:
        # Default control section
        lines.append("********************************************************")
        lines.append("\t.Control")
        lines.append("********************************************************~")
        lines.append("\t\tSimulation Control Parameters")
        lines.append("\t|")
        lines.append("")
        lines.append("FINAL TIME  = 100")
        lines.append("\t~\tMonth")
        lines.append("\t~\tThe final time for the simulation.")
        lines.append("\t|")
        lines.append("")
        lines.append("INITIAL TIME  = 0")
        lines.append("\t~\tMonth")
        lines.append("\t~\tThe initial time for the simulation.")
        lines.append("\t|")
        lines.append("")
        lines.append("SAVEPER  =")
        lines.append("\t\tTIME STEP")
        lines.append("\t~\tMonth [0,?]")
        lines.append("\t~\tThe frequency with which output is stored.")
        lines.append("\t|")
        lines.append("")
        lines.append("TIME STEP  = 1")
        lines.append("\t~\tMonth [0,?]")
        lines.append("\t~\tThe time step for the simulation.")
        lines.append("\t|")
        lines.append("")

    # Sketch section header from template or default
    if sketch_header:
        lines.extend(sketch_header)
    else:
        lines.append("\\\\\\---/// Sketch information - do not modify anything except names")
        lines.append("V300  Do not put anything below this section - it will be ignored")
        lines.append("*View 1")
        lines.append("$192-192-192,0,Times New Roman|12||0-0-0|0-0-0|0-0-255|-1--1--1|255-255-255|96,96,100,0")
        lines.append("///---\\\\\\")
        lines.append(":")

    # Variable sketch entries (Type 10) - new variables only
    for var in variables:
        var_id = var_name_to_id[var['name']]
        var_name = var['name']
        x = var.get('x', 500)
        y = var.get('y', 500)
        var_type = var.get('type', 'Auxiliary')

        # Map type to Vensim type code
        if var_type == 'Stock':
            type_code = 3
        elif var_type == 'Flow':
            type_code = 40
        else:  # Auxiliary
            type_code = 0

        # Quote name if needed
        quoted_name = _quote_var_name(var['name'])

        # Format: 10,id,name,x,y,width,height,type_code,color...
        line = f"10,{var_id},{quoted_name},{x},{y},40,20,{type_code},3,0,0,-1,0,0,0,0,0,0,0,0,0"
        lines.append(line)

    # Connection sketch entries (Type 1) - new connections only
    conn_id = 1
    for conn in connections:
        from_var = conn.get('from', '')
        to_var = conn.get('to', '')
        relationship = conn.get('relationship', 'positive')

        from_id = var_name_to_id.get(from_var)
        to_id = var_name_to_id.get(to_var)

        if from_id and to_id:
            # Determine polarity based on relationship
            if relationship == 'negative':
                thickness = 43
                polarity_flag = 1
            else:  # positive or unspecified
                thickness = 0
                polarity_flag = 0

            # Format: 1,conn_id,from_id,to_id,shape,hidden,thickness,font_size,color_r,color_g,color_b,polarity_code,...
            line = f"1,{conn_id},{from_id},{to_id},0,0,{thickness},22,0,192,{polarity_flag},-1--1--1,,1|(0,0)|"
            lines.append(line)
            conn_id += 1

    # Sketch footer from template or default
    if sketch_footer:
        lines.extend(sketch_footer)
    else:
        lines.append("///---\\\\\\")
        lines.append(":GRAPH")
        lines.append("///---\\\\\\")
        lines.append(":BUTTON")
        lines.append("///---\\\\\\")
        lines.append(":FUNCTION")
        lines.append("///---\\\\\\")
        lines.append(":TABLE")
        lines.append("///---\\\\\\")
        lines.append(":L<%^E!@")
        lines.append("1:untitled.vdfx")
        lines.append("9:untitled")
        lines.append("22:$,Dollar,Dollars,$s")
        lines.append("22:Hour,Hours")
        lines.append("22:Month,Months")
        lines.append("22:Person,People,Persons")
        lines.append("22:Unit,Units")
        lines.append("22:Week,Weeks")
        lines.append("22:Year,Years")
        lines.append("23:0")
        lines.append("15:0,0,0,0,0,0")
        lines.append("19:100,0")
        lines.append("27:2,")
        lines.append("34:0,")
        lines.append("42:1")
        lines.append("72:0")
        lines.append("73:0")
        lines.append("")

    return '\n'.join(lines)


def _quote_var_name(name: str) -> str:
    """
    Quote variable name if it contains special characters.

    Vensim requires quotes around names with spaces, commas, parentheses, etc.
    """
    special_chars = [' ', ',', '(', ')', '-', '/', "'"]

    if any(char in name for char in special_chars):
        # Escape internal quotes by doubling them
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    return name

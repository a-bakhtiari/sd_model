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
    clustering_scheme: Optional[Dict] = None
) -> Dict:
    """
    Create a completely new MDL file from theory enhancement output.

    This function builds an MDL from scratch using ONLY the variables and
    connections generated from theory enhancement. The original model is
    completely discarded.

    Args:
        theory_concretization: Output from theory_concretization step (step 2)
        output_path: Where to save the new MDL file
        llm_client: Optional LLM client for layout optimization
        clustering_scheme: Optional clustering from step 1 for spatial organization

    Returns:
        Dict with creation summary
    """

    # Extract all variables and connections from theory enhancement
    all_variables = []
    all_connections = []
    all_boundary_flows = []

    processes = theory_concretization.get('processes', [])
    for process in processes:
        process_name = process.get('process_name', 'Unknown')
        variables = process.get('variables', [])
        connections = process.get('connections', [])
        boundary_flows = process.get('boundary_flows', [])

        # Add cluster assignment to each variable
        for var in variables:
            var['cluster'] = process_name

        all_variables.extend(variables)
        all_connections.extend(connections)
        all_boundary_flows.extend(boundary_flows)

    if not all_variables:
        return {
            'error': 'No variables found in theory concretization output',
            'variables_created': 0
        }

    # Assign positions using LLM layout if available
    positioned_variables = _assign_positions(
        all_variables,
        all_connections,
        llm_client,
        clustering_scheme
    )

    # Build variable name to ID mapping
    var_name_to_id = {var['name']: i + 1 for i, var in enumerate(positioned_variables)}

    # Generate MDL content
    mdl_content = _generate_mdl_structure(
        positioned_variables,
        all_connections,
        all_boundary_flows,
        var_name_to_id
    )

    # Write to file
    output_path.write_text(mdl_content, encoding='utf-8')

    return {
        'variables_created': len(positioned_variables),
        'connections_created': len(all_connections),
        'boundary_flows_created': len(all_boundary_flows),
        'output_path': str(output_path)
    }


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
    # If no LLM client, use simple grid layout
    if not llm_client or not llm_client.enabled:
        return _simple_grid_layout(variables, clustering_scheme)

    # Use full relayout logic to position variables
    from .mdl_full_relayout import _get_llm_layout

    # Build clustering section if provided
    clustering_section = ""
    if clustering_scheme:
        clusters = clustering_scheme.get('clusters', [])
        overall_narrative = clustering_scheme.get('overall_narrative', '')

        if clusters:
            clustering_section = "\n## PROCESS CLUSTERING (Spatial Organization Hint)\n\n"
            clustering_section += f"**Overall Flow**: {overall_narrative}\n\n"
            clustering_section += "**Process Modules**:\n"
            for cluster in clusters:
                name = cluster.get('name', '')
                narrative = cluster.get('narrative', '')
                clustering_section += f"- **{name}**: {narrative}\n"

            clustering_section += "\nUse these clusters to spatially organize variables. Place related variables near each other.\n"

    # Create simplified variables for LLM
    vars_for_llm = [{'name': v['name'], 'type': v['type']} for v in variables]
    conns_for_llm = [{'from': c['from'], 'to': c['to']} for c in connections]

    # Build prompt (simplified version of full relayout prompt)
    prompt = f"""You are positioning {len(variables)} variables for a System Dynamics model diagram.

## VARIABLES TO POSITION
{json.dumps(vars_for_llm, indent=2)}

## CONNECTIONS
{json.dumps(conns_for_llm, indent=2)}

{clustering_section}

## YOUR TASK
Create an ASCII diagram showing variable positions. Use this format:

```
Var Name 1 (x,y)       Var Name 2 (x,y)

     Var Name 3 (x,y)

               Var Name 4 (x,y)
```

Requirements:
- Use coordinates between (0,0) and (2000,2000)
- Group related variables spatially
- Leave space between variables (minimum 150px)
- Place high-connectivity variables centrally

Return ONLY the ASCII diagram showing positions.
"""

    try:
        response = llm_client.complete(prompt, temperature=0.1, max_tokens=2000)

        # Parse LLM response to extract positions
        position_map = _parse_llm_positions(response)

        # Apply positions to variables
        positioned = []
        for var in variables:
            var_copy = var.copy()
            if var['name'] in position_map:
                var_copy['x'], var_copy['y'] = position_map[var['name']]
            else:
                # Default position if not found
                var_copy['x'], var_copy['y'] = 500, 500
            positioned.append(var_copy)

        return positioned

    except Exception as e:
        print(f"Warning: LLM positioning failed ({e}), using grid layout")
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


def _generate_mdl_structure(
    variables: List[Dict],
    connections: List[Dict],
    boundary_flows: List[Dict],
    var_name_to_id: Dict[str, int]
) -> str:
    """
    Generate complete MDL file structure.

    Returns MDL content as string.
    """
    lines = []

    # Header
    lines.append("{UTF-8}")

    # Equations section
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
            lines.append(f"{quoted_name}  = A FUNCTION OF( {deps_str})")
        else:
            lines.append(f"{quoted_name}  = A FUNCTION OF( )")
        lines.append("\t~\t")
        lines.append("\t~\t\t|")
        lines.append("")

    # Control section
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

    # Sketch section
    lines.append("\\\\\\---/// Sketch information - do not modify anything except names")
    lines.append("V300  Do not put anything below this section - it will be ignored")
    lines.append("*View 1")
    lines.append("$192-192-192,0,Times New Roman|12||0-0-0|0-0-0|0-0-255|-1--1--1|255-255-255|96,96,100,0")
    lines.append("///---\\\\\\")
    lines.append(":")

    # Variable sketch entries (Type 10)
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

    # Connection sketch entries (Type 1)
    conn_id = 1
    for conn in connections:
        from_var = conn.get('from', '')
        to_var = conn.get('to', '')
        relationship = conn.get('relationship', 'positive')

        from_id = var_name_to_id.get(from_var)
        to_id = var_name_to_id.get(to_var)

        if from_id and to_id:
            # Determine polarity based on relationship
            # Negative polarity: thickness=43, polarity_flag=1
            # Positive polarity: thickness=0, polarity_flag=0
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

    # End sketch section
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

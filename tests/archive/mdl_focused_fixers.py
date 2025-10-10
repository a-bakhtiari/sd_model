"""Focused LLM Fixers for MDL Sections.

Uses before/after comparison to fix specific sections without large prompts.
"""
from __future__ import annotations

import sys
from typing import Tuple

sys.path.insert(0, '.')

from src.sd_model.llm.client import LLMClient


def extract_sections(mdl_content: str) -> Tuple[str, str, str]:
    """Extract MDL sections: equations, sketch, footer.

    Returns:
        (equations_section, sketch_section, footer_section)
    """
    lines = mdl_content.split("\n")

    # Find sketch marker
    sketch_start = -1
    for i, line in enumerate(lines):
        if "\\\\\\---///" in line:
            sketch_start = i
            break

    # Find sketch end
    sketch_end = -1
    for i in range(sketch_start + 1, len(lines)):
        if "///---" in lines[i]:
            sketch_end = i + 1
            break

    equations = "\n".join(lines[:sketch_start])
    sketch = "\n".join(lines[sketch_start:sketch_end]) if sketch_end > sketch_start else ""
    footer = "\n".join(lines[sketch_end:]) if sketch_end > 0 else ""

    return equations, sketch, footer


def fix_sketch_section(
    original_sketch: str,
    modified_sketch: str,
    llm_client: LLMClient
) -> str:
    """Fix sketch section structure using original as reference.

    Args:
        original_sketch: Sketch section from original working MDL
        modified_sketch: Sketch section from modified MDL (may have issues)
        llm_client: LLM client instance

    Returns:
        Fixed sketch section
    """

    prompt = f"""Fix the MDL sketch section structure.

# Original Sketch (CORRECT structure)
```
{original_sketch}
```

# Modified Sketch (may have ordering issues)
```
{modified_sketch}
```

# Task
Fix the modified sketch to match the original structure:

1. **Header order:**
   - \\\\\\---/// Sketch information marker
   - V300 version line
   - *View 1 view name
   - $ style definition

2. **Content order:**
   - All 10, variable lines (after $ line)
   - All 12, cloud lines
   - All 1, connection lines
   - All 11, flow lines
   - ///---\\\\ end marker

3. **Preserve:**
   - All variable lines from modified (including new ones)
   - All connection lines
   - Flow/cloud adjacency where present

# Output
Return ONLY the fixed sketch section (from \\\\\\---/// to ///---\\\\).
No explanations, just the corrected lines.
"""

    response = llm_client.complete(prompt, temperature=0.1, max_tokens=3000, timeout=120)

    # Clean response - remove markdown code blocks if present
    cleaned = response.strip()
    lines = cleaned.split("\n")

    # Remove lines that are just markdown markers
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in ["```", "```mdl", "```vensim"]:
            continue
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def fix_equation_section(
    original_equations: str,
    modified_equations: str,
    llm_client: LLMClient
) -> str:
    """Fix equation section formatting using original as reference.

    Args:
        original_equations: Equations from original working MDL
        modified_equations: Equations from modified MDL (may have issues)
        llm_client: LLM client instance

    Returns:
        Fixed equation section
    """

    prompt = f"""Fix the MDL equation section formatting.

# Original Equations (CORRECT format)
```
{original_equations[:1000]}
...
```

# Modified Equations (may have spacing/format issues)
```
{modified_equations}
```

# Task
Fix the modified equations to match original format:

1. **Block structure:**
   - Each variable: 3 lines (equation, ~, ~|)
   - Blank line between blocks
   - Preserve multiline equations (\\)

2. **Ordering:**
   - Keep same grouping as original
   - New variables can go before control section

3. **Preserve:**
   - All variable names (including new ones)
   - All dependencies
   - Exact equation content

# Output
Return ONLY the fixed equation section (from {{UTF-8}} to before \\\\\\---///).
No explanations, just the corrected lines.
"""

    response = llm_client.complete(prompt, temperature=0.1, max_tokens=3000, timeout=120)

    # Clean response - remove markdown code blocks if present
    cleaned = response.strip()
    lines = cleaned.split("\n")

    # Remove lines that are just markdown markers
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in ["```", "```mdl", "```vensim"]:
            continue
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def reassemble_mdl(equations: str, sketch: str, footer: str) -> str:
    """Reassemble MDL from fixed sections.

    Args:
        equations: Fixed equation section
        sketch: Fixed sketch section
        footer: Footer section (usually unchanged)

    Returns:
        Complete MDL content
    """
    parts = []

    if equations:
        parts.append(equations)

    if sketch:
        # Don't add extra blank line if equations already has trailing blank
        if not equations.endswith("\n\n"):
            parts.append("")
        parts.append(sketch)

    if footer:
        parts.append(footer)

    return "\n".join(parts)

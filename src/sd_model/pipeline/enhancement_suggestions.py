"""
Enhancement Suggestions Module

Analyzes an existing SD model and generates specific, actionable suggestions for improvement
based on:
- Current model structure (parsed from MDL)
- Theory metadata (from recreation run)
- Research question
- User questions
- Feedback from advisors/peers
- Additional context

Outputs structured JSON for UI consumption (e.g., Streamlit)
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from ..llm.client import LLMClient
from ..mdl_parser import MDLParser


def read_enhancement_inputs(project_root: Path) -> Dict[str, str]:
    """Read enhancement input files (questions, feedback, context)."""
    enhancement_dir = project_root / "knowledge" / "enhancement"

    inputs = {
        "questions": "",
        "feedback": "",
        "context": ""
    }

    for key in inputs.keys():
        file_path = enhancement_dir / f"{key}.txt"
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                # Filter out comment lines
                lines = [line for line in content.split('\n')
                        if line.strip() and not line.strip().startswith('#')]
                inputs[key] = '\n'.join(lines).strip()
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

    return inputs


def parse_mdl_to_structure(mdl_path: Path) -> Dict:
    """
    Parse MDL file into structured format for enhancement analysis.

    Returns:
        {
          "summary": {...},
          "variables_by_type": {...},
          "connections": [...]
        }
    """
    # Use MDLParser
    parser = MDLParser(mdl_path)
    parsed = parser.parse()

    # Convert to structured format
    variables_by_type = {
        "stocks": [],
        "flows": [],
        "auxiliaries": [],
        "constants": []
    }

    connections = []

    # Categorize variables from parsed data
    # Variables can be either a dict or a list
    vars_data = parsed.get("variables", [])
    if isinstance(vars_data, dict):
        # Dict format: {var_name: var_data}
        for var_name, var_data in vars_data.items():
            var_type = var_data.get("type", "auxiliary").lower()
            if "stock" in var_type or "level" in var_type:
                variables_by_type["stocks"].append(var_name)
            elif "flow" in var_type or "rate" in var_type:
                variables_by_type["flows"].append(var_name)
            elif "constant" in var_type or "parameter" in var_type:
                variables_by_type["constants"].append(var_name)
            else:
                variables_by_type["auxiliaries"].append(var_name)
    else:
        # List format: [{"name": var_name, "type": var_type}, ...]
        for var in vars_data:
            var_name = var.get("name", "")
            var_type = var.get("type", "auxiliary").lower()
            if "stock" in var_type or "level" in var_type:
                variables_by_type["stocks"].append(var_name)
            elif "flow" in var_type or "rate" in var_type:
                variables_by_type["flows"].append(var_name)
            elif "constant" in var_type or "parameter" in var_type:
                variables_by_type["constants"].append(var_name)
            else:
                variables_by_type["auxiliaries"].append(var_name)

    # Extract connections from parsed data
    for conn in parsed.get("connections", []):
        connections.append({
            "from": conn.get("source", conn.get("from", "")),
            "to": conn.get("target", conn.get("to", "")),
            "polarity": conn.get("polarity", "unknown")
        })

    return {
        "summary": {
            "total_variables": sum(len(v) for v in variables_by_type.values()),
            "total_connections": len(connections),
            "stocks": len(variables_by_type["stocks"]),
            "flows": len(variables_by_type["flows"]),
            "auxiliaries": len(variables_by_type["auxiliaries"])
        },
        "variables_by_type": variables_by_type,
        "connections": connections
    }


def _basic_mdl_parse(mdl_path: Path) -> Dict:
    """Basic MDL parsing fallback if full parser not available."""
    # TODO: Implement basic parsing or use existing parser
    # For now, return empty structure
    return {
        "variables": {},
        "connections": []
    }


def load_theory_metadata(run_folder: Path) -> Dict:
    """Load theory metadata from theory_planning_step1.json in run folder."""
    theory_file = run_folder / "theory" / "theory_planning_step1.json"

    if not theory_file.exists():
        return {}

    try:
        with open(theory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract relevant info
        clusters = data.get("clustering_strategy", {}).get("clusters", [])

        return {
            "processes": [
                {
                    "name": cluster.get("name", ""),
                    "theories_used": cluster.get("theories_used", []),
                    "additional_theories": cluster.get("additional_theories_used", [])
                }
                for cluster in clusters
            ],
            "overall_narrative": data.get("clustering_strategy", {}).get("overall_narrative", "")
        }
    except Exception as e:
        print(f"Warning: Could not load theory metadata: {e}")
        return {}


def create_enhancement_prompt(
    model_structure: Dict,
    theory_metadata: Dict,
    research_question: str,
    available_theories: List[Dict],
    user_inputs: Dict
) -> str:
    """Create the prompt for enhancement suggestions."""

    # Format model structure
    model_summary = f"""
## Current Model Structure

**Summary:**
- Total Variables: {model_structure['summary']['total_variables']}
- Stocks: {model_structure['summary']['stocks']}
- Flows: {model_structure['summary']['flows']}
- Auxiliaries: {model_structure['summary']['auxiliaries']}
- Connections: {model_structure['summary']['total_connections']}

**Stocks:** {', '.join(model_structure['variables_by_type']['stocks'][:20])}
{('... and ' + str(len(model_structure['variables_by_type']['stocks']) - 20) + ' more') if len(model_structure['variables_by_type']['stocks']) > 20 else ''}

**Key Flows:** {', '.join(model_structure['variables_by_type']['flows'][:15])}
{('... and ' + str(len(model_structure['variables_by_type']['flows']) - 15) + ' more') if len(model_structure['variables_by_type']['flows']) > 15 else ''}

**Key Auxiliaries:** {', '.join(model_structure['variables_by_type']['auxiliaries'][:20])}
{('... and ' + str(len(model_structure['variables_by_type']['auxiliaries']) - 20) + ' more') if len(model_structure['variables_by_type']['auxiliaries']) > 20 else ''}
"""

    # Format theory metadata
    theory_section = ""
    if theory_metadata:
        theory_section = "\n## Theories Currently Used in Model\n\n"
        for process in theory_metadata.get("processes", []):
            theory_section += f"**{process['name']}:**\n"
            for theory in process['theories_used']:
                theory_section += f"- {theory}\n"
            theory_section += "\n"

    # Format available theories
    available_theories_section = "\n## Available Theories (Not Yet Used or Could Be Used More)\n\n"
    for theory in available_theories:
        available_theories_section += f"- **{theory.get('name')}**: {theory.get('description', '')}\n"

    # User inputs
    user_section = ""
    if user_inputs.get("questions"):
        user_section += f"\n## User's Specific Questions\n\n{user_inputs['questions']}\n"
    if user_inputs.get("feedback"):
        user_section += f"\n## Feedback from Advisors/Peers\n\n{user_inputs['feedback']}\n"
    if user_inputs.get("context"):
        user_section += f"\n## Additional Context\n\n{user_inputs['context']}\n"

    prompt = f"""# System Dynamics Model Enhancement Task

You are an expert in System Dynamics modeling and organizational/social theories. Your task is to analyze an existing SD model and provide specific, actionable enhancement suggestions.

## Research Question

{research_question}

{model_summary}

{theory_section}

{available_theories_section}

{user_section}

---

# Your Task

Analyze the current model and generate specific, actionable suggestions for improvement. Consider:

1. **User's questions** - Address their specific concerns
2. **Feedback received** - Incorporate suggestions from advisors/peers
3. **Additional context** - Respect their priorities and constraints
4. **Theory coverage** - Identify gaps or opportunities to apply theories more effectively
5. **Model structure** - Suggest structural improvements (feedback loops, connections, variables)
6. **Research alignment** - Ensure model serves the research question well

## Suggestion Categories

Generate suggestions in these categories:
- **add_variable**: Suggest adding a new stock, flow, or auxiliary
- **remove_variable**: Suggest removing redundant or unhelpful variables
- **modify_variable**: Suggest changing how a variable is defined or used
- **add_connection**: Suggest adding a causal link between variables
- **remove_connection**: Suggest removing a weak or incorrect connection
- **add_feedback_loop**: Suggest creating a new feedback loop
- **structural_change**: Suggest reorganizing processes or major structure changes
- **theory_recommendation**: Suggest applying a new theory or using existing theory differently

## Output Format

Return a JSON array of suggestions. Each suggestion must have:

```json
{{
  "id": <number>,
  "category": "<category>",
  "priority": "high|medium|low",
  "title": "<brief title>",
  "rationale": "<why this suggestion, referencing user inputs, theories, or model analysis>",
  "specific_change": {{
    "action": "<what to do>",
    // ... specific details depending on category
  }},
  "theory_basis": "<which theory supports this>",
  "related_variables": ["<list of affected variables>"]
}}
```

Be specific. Instead of "consider adding trust dynamics", say "Add stock 'Trust Level' in Process 2 with inflow 'Trust Building Rate' driven by 'Positive Interactions', connected to 'Community Belonging'".

**Output only valid JSON**. Start with `[` and end with `]`. No markdown code blocks, no extra text.
"""

    return prompt


def generate_enhancement_suggestions(
    mdl_path: Path,
    run_folder: Path,
    project_root: Path,
    llm_client: Optional[LLMClient] = None
) -> Dict:
    """
    Generate enhancement suggestions for an existing model.

    Args:
        mdl_path: Path to the MDL file to analyze
        run_folder: Path to the run folder containing theory metadata
        project_root: Path to project root (for reading inputs)
        llm_client: Optional LLM client

    Returns:
        Dict with suggestions and metadata
    """

    # Parse model structure
    print(f"Parsing model structure from {mdl_path}...")
    model_structure = parse_mdl_to_structure(mdl_path)

    # Load theory metadata
    print(f"Loading theory metadata from {run_folder}...")
    theory_metadata = load_theory_metadata(run_folder)

    # Read research question
    rq_path = project_root / "knowledge" / "RQ.txt"
    research_question = ""
    if rq_path.exists():
        research_question = rq_path.read_text(encoding='utf-8').strip()

    # Read available theories
    theories_path = project_root / "knowledge" / "theories.csv"
    available_theories = []
    if theories_path.exists():
        import csv
        with open(theories_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                available_theories.append({
                    "name": row.get("name", ""),
                    "description": row.get("description", "")
                })

    # Read enhancement inputs
    print(f"Reading enhancement inputs...")
    user_inputs = read_enhancement_inputs(project_root)

    # Create prompt
    print("Creating enhancement prompt...")
    prompt = create_enhancement_prompt(
        model_structure,
        theory_metadata,
        research_question,
        available_theories,
        user_inputs
    )

    # Call LLM
    print("Calling LLM for suggestions...")
    if llm_client is None:
        from ..config import should_use_gpt
        import logging
        logger = logging.getLogger(__name__)
        provider, model = should_use_gpt("enhancement_suggestions")
        logger.info(f"  → Enhancement using: {provider.upper()} ({model})")
        llm_client = LLMClient(provider=provider, model=model)

    response = llm_client.complete(prompt, temperature=0.3, max_tokens=4000)

    # Parse JSON response
    try:
        # Remove markdown code blocks if present
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        suggestions = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        print(f"Response: {response[:500]}...")
        suggestions = []

    # Build result
    result = {
        "timestamp": datetime.now().isoformat(),
        "model_analyzed": {
            "file": str(mdl_path),
            "run_folder": str(run_folder),
            "variables": model_structure["summary"]["total_variables"],
            "connections": model_structure["summary"]["total_connections"],
            "processes": len(theory_metadata.get("processes", []))
        },
        "suggestions": suggestions,
        "summary": {
            "total_suggestions": len(suggestions),
            "by_priority": {
                "high": sum(1 for s in suggestions if s.get("priority") == "high"),
                "medium": sum(1 for s in suggestions if s.get("priority") == "medium"),
                "low": sum(1 for s in suggestions if s.get("priority") == "low")
            },
            "by_category": {}
        }
    }

    # Count by category
    for suggestion in suggestions:
        category = suggestion.get("category", "other")
        result["summary"]["by_category"][category] = \
            result["summary"]["by_category"].get(category, 0) + 1

    return result


def save_suggestions(suggestions: Dict, output_dir: Path):
    """Save suggestions to JSON and optionally Markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON (for Streamlit UI)
    json_path = output_dir / "latest.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)
    print(f"✓ Suggestions saved to {json_path}")

    # Save to history
    history_dir = output_dir / "history"
    history_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = history_dir / f"{timestamp}_suggestions.json"
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)

    # Optionally save Markdown (for human reading)
    md_path = output_dir / "latest.md"
    markdown = format_suggestions_as_markdown(suggestions)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"✓ Human-readable version saved to {md_path}")


def format_suggestions_as_markdown(suggestions: Dict) -> str:
    """Format suggestions as human-readable Markdown."""
    md = f"""# Model Enhancement Suggestions
Generated: {suggestions['timestamp']}

Model Analyzed: `{suggestions['model_analyzed']['file']}`
- Variables: {suggestions['model_analyzed']['variables']}
- Connections: {suggestions['model_analyzed']['connections']}
- Processes: {suggestions['model_analyzed']['processes']}

---

## Summary

Total Suggestions: {suggestions['summary']['total_suggestions']}

By Priority:
- High: {suggestions['summary']['by_priority'].get('high', 0)}
- Medium: {suggestions['summary']['by_priority'].get('medium', 0)}
- Low: {suggestions['summary']['by_priority'].get('low', 0)}

By Category:
"""

    for category, count in suggestions['summary']['by_category'].items():
        md += f"- {category}: {count}\n"

    md += "\n---\n\n"

    # Group by priority
    for priority in ["high", "medium", "low"]:
        priority_suggestions = [s for s in suggestions['suggestions']
                               if s.get('priority') == priority]

        if priority_suggestions:
            md += f"## {priority.upper()} PRIORITY\n\n"

            for suggestion in priority_suggestions:
                md += f"### {suggestion.get('id')}. {suggestion.get('title')}\n"
                md += f"**Category:** {suggestion.get('category')} | "
                md += f"**Theory:** {suggestion.get('theory_basis', 'N/A')}\n\n"
                md += f"**Why:** {suggestion.get('rationale', '')}\n\n"

                # Format specific change
                specific = suggestion.get('specific_change', {})
                if specific:
                    md += "**What to do:**\n"
                    for key, value in specific.items():
                        if isinstance(value, list):
                            md += f"- {key}: {', '.join(str(v) for v in value)}\n"
                        else:
                            md += f"- {key}: {value}\n"

                md += "\n---\n\n"

    return md

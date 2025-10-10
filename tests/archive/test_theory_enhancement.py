#!/usr/bin/env python3
"""
Test Module 2: Theory Enhancement Suggester

Takes core analysis and generates specific SD implementation suggestions
for missing theory elements and model improvements.
"""
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sd_model.llm.client import LLMClient


def load_json_artifact(path: Path) -> dict:
    """Load JSON artifact with error handling."""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_enhancement_prompt(
    theories: list[dict],
    variables: dict,
    connections: dict,
    loops: dict
) -> str:
    """Create prompt for theory enhancement suggestions."""

    # Calculate basic stats
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Get sample variables
    sample_vars = variables.get("variables", [])[:8]
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in sample_vars
    ])

    # Get sample connections
    sample_conns = connections.get("connections", [])[:8]
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in sample_conns
    ])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in theories
    ])

    prompt = f"""You are a system dynamics modeling expert specializing in Communities of Practice and Knowledge Management theories for open-source software development.

# Current System Dynamics Model

## Model Summary
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

## Sample Variables
{vars_text}

## Sample Connections
{conns_text}

# Theories Being Used
{theories_text}

# Your Task

Analyze the model and theories to identify:
1. **Missing theory elements** - Key concepts from the theories not yet modeled
2. **Underutilized aspects** - Parts of theories only partially implemented
3. **SD implementation suggestions** - Specific variables, connections, and loops to add

For each missing theory element, provide:

1. **What to add** (variables, connections)
2. **Why it's important** (theoretical justification)
3. **How to implement** (step-by-step SD modeling)
4. **Expected impact** (what dynamics this will capture)

Return JSON in this structure:

{{
  "missing_from_theories": [
    {{
      "theory_name": "theory name",
      "missing_element": "specific element from theory",
      "why_important": "why this matters for the model",
      "how_to_add": "high-level implementation guidance",
      "sd_implementation": {{
        "new_variables": [
          {{
            "name": "Variable Name",
            "type": "Stock|Flow|Auxiliary",
            "description": "what it represents"
          }}
        ],
        "new_connections": [
          {{
            "from": "Variable A",
            "to": "Variable B",
            "relationship": "positive|negative",
            "rationale": "why this connection exists"
          }}
        ],
        "expected_loops": [
          {{
            "type": "reinforcing|balancing",
            "description": "what loop this will create or strengthen"
          }}
        ]
      }},
      "expected_impact": "what dynamics this will enable"
    }}
  ],
  "general_improvements": [
    {{
      "improvement_type": "add_mechanism|refine_structure|add_feedback",
      "description": "what to improve",
      "implementation": "how to do it",
      "impact": "high|medium|low"
    }}
  ]
}}

Focus on practical, implementable suggestions. Be specific about variable names and types.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_theory_enhancement(
    theories: list[dict],
    variables: dict,
    connections: dict,
    loops: dict
) -> dict:
    """Generate theory enhancement suggestions."""

    print("=" * 80)
    print("MODULE 2: THEORY ENHANCEMENT SUGGESTER")
    print("=" * 80)

    # Create prompt
    print("\n1. Creating enhancement prompt...")
    prompt = create_enhancement_prompt(theories, variables, connections, loops)
    print(f"   ✓ Prompt created ({len(prompt)} characters)")

    # Call LLM
    print("\n2. Calling DeepSeek for enhancement suggestions...")
    print("   (This may take 1-2 minutes...)")

    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.2, max_tokens=4000)

    print(f"   ✓ Received response ({len(response)} characters)")

    # Parse response
    print("\n3. Parsing response...")
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
            print("   ✓ Successfully parsed JSON")
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        print(f"   ✗ Failed to parse JSON: {e}")
        print("\n   Raw response:")
        print("   " + "-" * 76)
        print("   " + response[:500])
        print("   " + "-" * 76)
        return {"error": str(e), "raw_response": response}

    return result


def main():
    """Main test function."""
    import csv

    # Define paths
    project_root = Path(__file__).parent.parent
    artifacts_dir = project_root / "projects" / "oss_model" / "artifacts"
    knowledge_dir = project_root / "projects" / "oss_model" / "knowledge"

    # Load theories
    theories_path = knowledge_dir / "theories.csv"
    theories = []
    with open(theories_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('name'):
                theories.append(row)

    # Load artifacts
    print("=" * 80)
    print("Loading artifacts from oss_model project...")
    print("=" * 80)

    variables = load_json_artifact(artifacts_dir / "variables_llm.json")
    connections = load_json_artifact(artifacts_dir / "connections.json")
    loops = load_json_artifact(artifacts_dir / "loops.json")

    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    print(f"\n✓ Loaded {len(theories)} theories from: {theories_path}")
    print(f"✓ Variables: {var_count}")
    print(f"✓ Connections: {conn_count}")
    print(f"✓ Loops: {loop_count}\n")

    # Run enhancement
    result = run_theory_enhancement(theories, variables, connections, loops)

    # Save result
    output_path = Path(__file__).parent / "theory_enhancement_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✓ Enhancement suggestions generated! Saved to: {output_path}")
    print("=" * 80)

    # Print summary
    if "error" not in result:
        print("\n" + "=" * 80)
        print("ENHANCEMENT SUMMARY")
        print("=" * 80)

        missing = result.get("missing_from_theories", [])
        print(f"\nMissing Theory Elements: {len(missing)}")
        for m in missing:
            theory = m.get("theory_name", "Unknown")
            element = m.get("missing_element", "Unknown")
            new_vars = len(m.get("sd_implementation", {}).get("new_variables", []))
            new_conns = len(m.get("sd_implementation", {}).get("new_connections", []))
            print(f"\n  • {theory}: {element}")
            print(f"    → {new_vars} new variables, {new_conns} new connections")

        improvements = result.get("general_improvements", [])
        print(f"\nGeneral Improvements: {len(improvements)}")
        for imp in improvements:
            print(f"  • {imp.get('improvement_type', 'unknown')}: {imp.get('description', 'N/A')[:60]}...")


if __name__ == "__main__":
    main()

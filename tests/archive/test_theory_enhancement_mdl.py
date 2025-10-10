"""
Test: Enhanced Theory Enhancement for MDL Generation

This test creates an MDL-ready version of theory enhancement that includes:
- Add/remove/modify operations
- Position suggestions
- All metadata needed for MDL generation
- Concise MDL-ready comments
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.sd_model.llm.client import LLMClient


def create_mdl_enhancement_prompt(
    theories: list,
    variables: dict,
    connections: dict,
    loops: dict
) -> str:
    """Create enhanced prompt for MDL-ready theory enhancement."""

    # Calculate stats
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Get sample variables with positions
    sample_vars = variables.get("variables", [])[:10]
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')}) at position x={v.get('x', 0)}, y={v.get('y', 0)}"
        for v in sample_vars
    ])

    # Get sample connections
    sample_conns = connections.get("connections", [])[:10]
    conns_text = "\n".join([
        f"- {c.get('from_var', 'unknown')} → {c.get('to_var', 'unknown')} ({c.get('relationship', 'unknown')})"
        for c in sample_conns
    ])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t.get('description', 'No description')}"
        for t in theories
    ])

    prompt = f"""You are a system dynamics modeling expert specializing in Communities of Practice and Knowledge Management theories for open-source software development.

# Current System Dynamics Model

## Model Summary
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

## Sample Variables (with positions)
{vars_text}

## Sample Connections
{conns_text}

# Theories Being Used
{theories_text}

# Your Task: Generate MDL-Ready Model Enhancements

Analyze the model and theories to suggest COMPREHENSIVE changes including:
1. **Additions** - Missing theory elements
2. **Removals** - Redundant or unsupported elements
3. **Modifications** - Improvements to existing elements

For EACH change, you MUST provide:
- Complete metadata for MDL generation (positions, sizes, colors)
- Concise MDL-ready comment (max 80 chars, citation included)
- Position suggestions based on related variables' locations

## IMPORTANT Guidelines:

**For new variables:**
- Suggest x,y position near related existing variables
- Explain position reasoning (e.g., "between A and B for flow continuity")
- Use standard sizes: Stock/Flow width=60-70, Auxiliary width=50-60, height=26

**For colors:**
- Green (0-255-0) for additions
- Orange (255-165-0) for modifications
- Red (255-0-0) for removals (visual marker)

**For comments:**
- Keep under 80 characters
- Include operation type and citation
- Examples:
  - "Added: CoP theory - peripheral participation (Wenger 1998)"
  - "Modified: Empirical support for positive relationship (Smith 2020)"
  - "Removed: Redundant with Knowledge Transfer variable"

**Be critical and selective:**
- Remove redundant variables
- Fix theoretically unsupported connections
- Merge similar concepts
- Simplify overly complex structures

Return JSON in this EXACT structure:

{{
  "model_changes": [
    {{
      "operation": "add_variable",
      "variable": {{
        "name": "Peripheral Participants",
        "type": "Stock",
        "description": "Newcomers observing and doing simple tasks",
        "position": {{
          "x": 950,
          "y": 350,
          "reasoning": "Between New Contributors (x=862) and Experienced Contributors (x=1080) for progression flow"
        }},
        "size": {{"width": 70, "height": 26}},
        "color": {{"border": "0-255-0"}},
        "initial_value": "0",
        "units": "people"
      }},
      "mdl_comment": "Added: CoP theory - peripheral participation (Wenger 1998)"
    }},
    {{
      "operation": "add_connection",
      "connection": {{
        "from": "Mentoring Effectiveness",
        "to": "Progression Rate",
        "relationship": "positive",
        "color": "0-255-0"
      }},
      "mdl_comment": "Added: Mentoring accelerates progression (Ye et al. 2005)"
    }},
    {{
      "operation": "remove_variable",
      "variable": {{
        "name": "Redundant Variable Name"
      }},
      "mdl_comment": "Removed: Redundant with Knowledge Transfer"
    }},
    {{
      "operation": "modify_connection",
      "connection": {{
        "from": "Variable A",
        "to": "Variable B",
        "old_relationship": "undeclared",
        "new_relationship": "positive",
        "color": "255-165-0"
      }},
      "mdl_comment": "Modified: Positive relationship supported (Jones 2019)"
    }},
    {{
      "operation": "remove_connection",
      "connection": {{
        "from": "Variable X",
        "to": "Variable Y"
      }},
      "mdl_comment": "Removed: Not supported by theory or evidence"
    }}
  ],
  "summary": {{
    "additions": {{"variables": 5, "connections": 3}},
    "removals": {{"variables": 2, "connections": 1}},
    "modifications": {{"variables": 0, "connections": 2}},
    "net_change": "Model refined with theoretical alignment"
  }}
}}

**Critical Requirements:**
- ALL operations must have "mdl_comment" field (max 80 chars)
- ALL new variables must have position suggestions with reasoning
- Use actual variable names from the model above
- Be selective: 5-15 high-impact changes total
- Include at least 1 removal to demonstrate critical thinking

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_mdl_enhancement_test():
    """Test the MDL-ready theory enhancement."""

    print("="*80)
    print("MDL-Ready Theory Enhancement Test")
    print("="*80)

    # Load oss_model artifacts
    repo_root = Path(".")
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    theories_dir = repo_root / "projects" / "oss_model" / "knowledge" / "theories"

    print("\n1. Loading artifacts...")
    variables = json.loads((artifacts_dir / "variables_llm.json").read_text())
    connections = json.loads((artifacts_dir / "connections.json").read_text())
    loops = json.loads((artifacts_dir / "loops.json").read_text())

    print(f"   ✓ Loaded {len(variables.get('variables', []))} variables")
    print(f"   ✓ Loaded {len(connections.get('connections', []))} connections")
    print(f"   ✓ Loaded {len(loops.get('reinforcing', []) + loops.get('balancing', []))} loops")

    # Load theories (simplified - just theory names and descriptions)
    print("\n2. Loading theories...")
    from src.sd_model.knowledge.loader import load_theories
    theories_objs = load_theories(theories_dir)
    theories = [
        {
            "name": t.theory_name,
            "description": t.description,
            "focus_area": t.focus_area
        }
        for t in theories_objs
    ]
    print(f"   ✓ Loaded {len(theories)} theories")

    # Create prompt
    print("\n3. Creating MDL enhancement prompt...")
    prompt = create_mdl_enhancement_prompt(theories, variables, connections, loops)
    print(f"   ✓ Prompt created ({len(prompt)} chars)")

    # Call LLM
    print("\n4. Calling LLM (DeepSeek)...")
    print("   This may take 30-60 seconds...")
    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.2, max_tokens=4000)

    # Parse response
    print("\n5. Parsing response...")
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")
        print("   ✓ JSON parsed successfully")
    except Exception as e:
        print(f"   ✗ Parse error: {e}")
        print(f"\nRaw response:\n{response[:500]}...")
        return

    # Save result to tests directory
    tests_dir = repo_root / "tests"
    output_path = tests_dir / "theory_enhancement_mdl.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n6. Saved to: {output_path}")

    # Display summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    summary = result.get("summary", {})
    additions = summary.get("additions", {})
    removals = summary.get("removals", {})
    modifications = summary.get("modifications", {})

    print(f"\nAdditions:")
    print(f"  Variables: {additions.get('variables', 0)}")
    print(f"  Connections: {additions.get('connections', 0)}")

    print(f"\nRemovals:")
    print(f"  Variables: {removals.get('variables', 0)}")
    print(f"  Connections: {removals.get('connections', 0)}")

    print(f"\nModifications:")
    print(f"  Variables: {modifications.get('variables', 0)}")
    print(f"  Connections: {modifications.get('connections', 0)}")

    print(f"\nTotal changes: {len(result.get('model_changes', []))}")

    # Show sample changes
    print("\n" + "="*80)
    print("SAMPLE CHANGES (first 3)")
    print("="*80)
    for i, change in enumerate(result.get("model_changes", [])[:3]):
        print(f"\n{i+1}. Operation: {change.get('operation')}")
        print(f"   Comment: {change.get('mdl_comment', 'N/A')}")
        if "variable" in change:
            var = change["variable"]
            print(f"   Variable: {var.get('name')} ({var.get('type', 'N/A')})")
            if "position" in var:
                pos = var["position"]
                print(f"   Position: x={pos.get('x')}, y={pos.get('y')}")
                print(f"   Reasoning: {pos.get('reasoning', 'N/A')[:60]}...")
        if "connection" in change:
            conn = change["connection"]
            print(f"   Connection: {conn.get('from')} → {conn.get('to')} ({conn.get('relationship', 'N/A')})")

    print("\n" + "="*80)
    print("✅ Test completed successfully!")
    print(f"Full results in: {output_path}")
    print("="*80)


if __name__ == "__main__":
    run_mdl_enhancement_test()

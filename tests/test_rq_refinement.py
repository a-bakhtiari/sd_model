#!/usr/bin/env python3
"""
Test Module 4: Research Question Refiner

Suggests improved RQ formulations based on model capabilities,
theoretical framework, and PhD research standards.
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


def create_refinement_prompt(
    rqs: list[str],
    rq_alignment: dict,
    variables: dict,
    connections: dict,
    loops: dict
) -> str:
    """Create prompt for RQ refinement suggestions."""

    # Format current RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Calculate model statistics
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Extract alignment scores from Module 3 output
    alignment_summary = ""
    for i in range(1, 4):
        rq_data = rq_alignment.get(f"rq_{i}", {})
        score = rq_data.get("alignment_score", 0)
        issues = rq_data.get("critical_issues", [])
        alignment_summary += f"\nRQ{i} - Alignment Score: {score}/10\n"
        if issues:
            alignment_summary += "Issues:\n"
            for issue in issues:
                alignment_summary += f"  - {issue.get('issue', 'N/A')} (severity: {issue.get('severity', 'unknown')})\n"

    prompt = f"""You are a PhD research methodology expert specializing in system dynamics. Help refine these research questions to be more focused, measurable, and aligned with the model and theoretical framework.

# Current Research Questions
{rqs_text}

# Model Capabilities
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

# Current Alignment Assessment
{alignment_summary}

# Your Task

For each RQ, provide:
1. **Issues** with current formulation
2. **Refined versions** (2-3 alternatives)
3. **New RQ suggestions** based on model insights
4. **PhD-worthiness assessment**

Criteria for good RQs:
- Specific and measurable
- Aligned with model capabilities
- Theoretically grounded
- Contributes to knowledge
- Feasible within PhD scope

Return JSON in this structure:

{{
  "current_rqs": ["RQ1...", "RQ2...", "RQ3..."],
  "refinement_suggestions": [
    {{
      "rq_number": 1,
      "original": "original RQ text",
      "issues": [
        "too broad",
        "not measurable",
        "doesn't specify mechanism"
      ],
      "refined_versions": [
        {{
          "version": "refined RQ text",
          "rationale": "why this is better",
          "sd_modelability": "poor|moderate|good|excellent",
          "theoretical_grounding": "poor|moderate|good|excellent",
          "phd_worthiness": 1-10,
          "feasibility": "low|medium|high",
          "contribution": "what new knowledge this adds"
        }}
      ],
      "recommendation": "which refined version is best and why"
    }}
  ],
  "new_rq_suggestions": [
    {{
      "suggested_rq": "new RQ based on model insights",
      "based_on_model": "what model feature suggests this",
      "theoretical_basis": "which theory/theories support this",
      "phd_worthiness": 1-10,
      "originality": "assessment of novelty",
      "rationale": "why this is worth investigating"
    }}
  ],
  "overall_strategy": {{
    "recommended_approach": "focus|broaden|pivot",
    "reasoning": "why this strategy is best",
    "trade_offs": "what you gain and lose with this approach"
  }}
}}

Be creative but grounded. Suggest RQs that are ambitious but achievable.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_rq_refinement(
    rqs: list[str],
    rq_alignment: dict,
    variables: dict,
    connections: dict,
    loops: dict
) -> dict:
    """Generate RQ refinement suggestions."""

    print("=" * 80)
    print("MODULE 4: RESEARCH QUESTION REFINER")
    print("=" * 80)

    # Create prompt
    print("\n1. Creating RQ refinement prompt...")
    prompt = create_refinement_prompt(rqs, rq_alignment, variables, connections, loops)
    print(f"   ✓ Prompt created ({len(prompt)} characters)")

    # Call LLM
    print("\n2. Calling DeepSeek for RQ refinement...")
    print("   (This may take 1-2 minutes...)")

    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.3, max_tokens=4000)

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
    # Define paths
    project_root = Path(__file__).parent.parent
    artifacts_dir = project_root / "projects" / "oss_model" / "artifacts"
    knowledge_dir = project_root / "projects" / "oss_model" / "knowledge"

    # Load RQ alignment from Module 3
    alignment_path = Path(__file__).parent / "rq_alignment_result.json"
    if not alignment_path.exists():
        print(f"ERROR: RQ alignment not found at {alignment_path}")
        print("Run test_rq_alignment.py first!")
        return

    with open(alignment_path, 'r', encoding='utf-8') as f:
        rq_alignment = json.load(f)

    # Load RQs
    rq_path = knowledge_dir / "RQ.txt"
    with open(rq_path, 'r', encoding='utf-8') as f:
        rqs = [line.strip() for line in f.readlines() if line.strip()]

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

    print(f"\n✓ Loaded RQ alignment from: {alignment_path}")
    print(f"✓ Loaded {len(rqs)} RQs from: {rq_path}")
    print(f"✓ Variables: {var_count}")
    print(f"✓ Connections: {conn_count}")
    print(f"✓ Loops: {loop_count}\n")

    # Run refinement
    result = run_rq_refinement(rqs, rq_alignment, variables, connections, loops)

    # Save result
    output_path = Path(__file__).parent / "rq_refinement_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✓ RQ refinement complete! Saved to: {output_path}")
    print("=" * 80)

    # Print summary
    if "error" not in result:
        print("\n" + "=" * 80)
        print("RQ REFINEMENT SUMMARY")
        print("=" * 80)

        refinements = result.get("refinement_suggestions", [])
        print(f"\nRefinement Suggestions: {len(refinements)}")
        for ref in refinements:
            rq_num = ref.get("rq_number", 0)
            versions = ref.get("refined_versions", [])
            print(f"\n  RQ{rq_num}: {len(versions)} refined versions")
            if versions:
                best = versions[0]
                score = best.get("phd_worthiness", 0)
                print(f"    Best version (PhD-worthiness: {score}/10):")
                print(f"    '{best.get('version', 'N/A')[:80]}...'")

        new_rqs = result.get("new_rq_suggestions", [])
        print(f"\nNew RQ Suggestions: {len(new_rqs)}")
        for new_rq in new_rqs[:2]:  # Show top 2
            score = new_rq.get("phd_worthiness", 0)
            print(f"  [{score}/10] {new_rq.get('suggested_rq', 'N/A')[:80]}...")

        strategy = result.get("overall_strategy", {})
        approach = strategy.get("recommended_approach", "unknown")
        print(f"\nRecommended Strategy: {approach.upper()}")


if __name__ == "__main__":
    main()

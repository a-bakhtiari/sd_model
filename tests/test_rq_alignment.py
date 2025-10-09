#!/usr/bin/env python3
"""
Test Module 3: RQ-Theory-Model Alignment Evaluator

Evaluates how well research questions are addressed by the current
combination of theories and model structure.
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


def create_alignment_prompt(
    rqs: list[str],
    theories: list[dict],
    variables: dict,
    connections: dict,
    loops: dict
) -> str:
    """Create prompt for RQ-theory-model alignment evaluation."""

    # Calculate model statistics
    var_count = len(variables.get("variables", []))
    conn_count = len(connections.get("connections", []))
    loop_count = len(loops.get("reinforcing", [])) + len(loops.get("balancing", [])) + len(loops.get("undetermined", []))

    # Get sample variables for context
    sample_vars = variables.get("variables", [])[:8]
    vars_text = "\n".join([
        f"- {v['name']} ({v.get('type', 'Unknown')})"
        for v in sample_vars
    ])

    # Get sample connections for context
    sample_conns = connections.get("connections", [])[:8]
    conns_text = "\n".join([
        f"- {c['from_var']} → {c['to_var']} ({c.get('relationship', 'unknown')})"
        for c in sample_conns
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Format theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']} (Focus: {t['focus_area']})"
        for t in theories
    ])

    prompt = f"""You are a PhD research methodology expert. Evaluate the alignment between research questions, theoretical framework, and system dynamics model.

# Research Questions
{rqs_text}

# Current Theories
{theories_text}

# Model Summary
- Variables: {var_count}
- Connections: {conn_count}
- Feedback Loops: {loop_count}

# Sample Model Variables
{vars_text}

# Sample Model Connections
{conns_text}

# Your Task

Provide a detailed evaluation of how well the research questions can be answered with the current theories and model. For each RQ, assess:

1. **Alignment Score** (1-10): How well can this RQ be answered?
2. **Theory Fit**: Do the current theories support this RQ?
3. **Model Fit**: Does the model structure enable answering this RQ?
4. **Critical Issues**: What's preventing full coverage?
5. **Recommendations**: What should be added/removed/modified?

Return JSON in this structure:

{{
  "overall_assessment": {{
    "model_rq_fit": "poor|moderate|good|excellent",
    "theory_rq_fit": "poor|moderate|good|excellent",
    "coherence": "poor|moderate|good|excellent",
    "phd_viability": "poor|moderate|good|excellent",
    "summary": "overall assessment in 2-3 sentences"
  }},
  "rq_1": {{
    "alignment_score": 1-10,
    "theory_fit": {{
      "score": 1-10,
      "assessment": "how well theories support this RQ",
      "gaps": ["missing theoretical elements"]
    }},
    "model_fit": {{
      "score": 1-10,
      "assessment": "how well model structure enables answering this",
      "gaps": ["missing model elements"]
    }},
    "critical_issues": [
      {{
        "issue": "what's wrong",
        "severity": "low|medium|high|critical"
      }}
    ],
    "recommendations": {{
      "theories_to_add": [
        {{
          "theory": "theory name",
          "why": "why it would help"
        }}
      ],
      "theories_to_remove": [],
      "model_additions": ["what to add to model"],
      "priority": "low|medium|high"
    }}
  }},
  "rq_2": {{
    "alignment_score": 1-10,
    "theory_fit": {{ ... }},
    "model_fit": {{ ... }},
    "critical_issues": [ ... ],
    "recommendations": {{ ... }}
  }},
  "rq_3": {{
    "alignment_score": 1-10,
    "theory_fit": {{ ... }},
    "model_fit": {{ ... }},
    "critical_issues": [ ... ],
    "recommendations": {{ ... }}
  }},
  "actionable_steps": [
    {{
      "step": "what to do",
      "rationale": "why this helps",
      "impact": "high|medium|low",
      "effort": "low|medium|high"
    }}
  ]
}}

Be honest and critical. If something doesn't fit well, say so clearly.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_rq_alignment(
    rqs: list[str],
    theories: list[dict],
    variables: dict,
    connections: dict,
    loops: dict
) -> dict:
    """Evaluate RQ-theory-model alignment."""

    print("=" * 80)
    print("MODULE 3: RQ-THEORY-MODEL ALIGNMENT EVALUATOR")
    print("=" * 80)

    # Create prompt
    print("\n1. Creating alignment evaluation prompt...")
    prompt = create_alignment_prompt(rqs, theories, variables, connections, loops)
    print(f"   ✓ Prompt created ({len(prompt)} characters)")

    # Call LLM
    print("\n2. Calling DeepSeek for alignment evaluation...")
    print("   (This may take 1-2 minutes...)")

    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.1, max_tokens=4000)

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

    # Load RQs
    rq_path = knowledge_dir / "RQ.txt"
    with open(rq_path, 'r', encoding='utf-8') as f:
        rqs = [line.strip() for line in f.readlines() if line.strip()]

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

    print(f"\n✓ Loaded {len(rqs)} RQs from: {rq_path}")
    print(f"✓ Loaded {len(theories)} theories from: {theories_path}")
    print(f"✓ Variables: {var_count}")
    print(f"✓ Connections: {conn_count}")
    print(f"✓ Loops: {loop_count}\n")

    # Run alignment evaluation
    result = run_rq_alignment(rqs, theories, variables, connections, loops)

    # Save result
    output_path = Path(__file__).parent / "rq_alignment_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✓ Alignment evaluation complete! Saved to: {output_path}")
    print("=" * 80)

    # Print summary
    if "error" not in result:
        print("\n" + "=" * 80)
        print("ALIGNMENT EVALUATION SUMMARY")
        print("=" * 80)

        overall = result.get("overall_assessment", {})
        print(f"\nOverall Assessment:")
        print(f"  Model-RQ Fit: {overall.get('model_rq_fit', 'N/A').upper()}")
        print(f"  Theory-RQ Fit: {overall.get('theory_rq_fit', 'N/A').upper()}")
        print(f"  Coherence: {overall.get('coherence', 'N/A').upper()}")
        print(f"  PhD Viability: {overall.get('phd_viability', 'N/A').upper()}")

        print(f"\nRQ Alignment Scores:")
        for i in range(1, 4):
            rq_data = result.get(f"rq_{i}", {})
            score = rq_data.get("alignment_score", 0)
            theory_score = rq_data.get("theory_fit", {}).get("score", 0)
            model_score = rq_data.get("model_fit", {}).get("score", 0)
            print(f"  RQ{i}: {score}/10 (Theory: {theory_score}/10, Model: {model_score}/10)")

        steps = result.get("actionable_steps", [])
        print(f"\nActionable Steps: {len(steps)}")
        for step in steps[:3]:  # Show top 3
            impact = step.get("impact", "unknown")
            print(f"  • [{impact.upper()}] {step.get('step', 'N/A')}")


if __name__ == "__main__":
    main()

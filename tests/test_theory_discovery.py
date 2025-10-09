#!/usr/bin/env python3
"""
Test Module 5: Adjacent Theory Discovery

Recommends new theories (direct + adjacent) based on RQs and model gaps.
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


def create_discovery_prompt(
    rqs: list[str],
    current_theories: list[dict],
    rq_alignment: dict
) -> str:
    """Create prompt for theory discovery."""

    # Format current theories
    theories_text = "\n".join([
        f"- {t['name']}: {t['description']}"
        for t in current_theories
    ])

    # Format RQs
    rqs_text = "\n".join([f"{i+1}. {rq}" for i, rq in enumerate(rqs)])

    # Extract alignment issues and recommendations
    gaps_and_recommendations = ""
    for i in range(1, 4):
        rq_data = rq_alignment.get(f"rq_{i}", {})
        score = rq_data.get("alignment_score", 0)

        # Get gaps from model_fit and theory_fit
        model_gaps = rq_data.get("model_fit", {}).get("gaps", [])
        theory_gaps = rq_data.get("theory_fit", {}).get("gaps", [])

        # Get theory recommendations
        recs = rq_data.get("recommendations", {}).get("theories_to_add", [])

        if model_gaps or theory_gaps or recs:
            gaps_and_recommendations += f"\nRQ{i} (Alignment: {score}/10):\n"

            if theory_gaps:
                gaps_and_recommendations += "  Theory gaps:\n"
                for gap in theory_gaps:
                    gaps_and_recommendations += f"    - {gap}\n"

            if recs:
                gaps_and_recommendations += "  Suggested theories:\n"
                for rec in recs:
                    gaps_and_recommendations += f"    - {rec.get('theory', 'Unknown')}: {rec.get('why', '')}\n"

    prompt = f"""You are an expert in organizational theory, knowledge management, software engineering, and system dynamics. Recommend new theories that could strengthen this PhD research project.

# Research Questions
{rqs_text}

# Current Theories
{theories_text}

# Gaps and Recommendations from Alignment Analysis
{gaps_and_recommendations}

# Your Task

Recommend theories at three levels:
1. **Direct**: Clearly relevant to current RQs and model
2. **Adjacent**: Slightly different angle, creative connection
3. **Cross-domain**: Provocative parallels from other fields

For each theory, provide:
- Theory name and key scholars
- Relevance to RQs and model
- Adjacency level (direct, adjacent, exploratory)
- PhD contribution potential
- Risk/reward assessment

Return JSON in this structure:

{{
  "high_relevance": [
    {{
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description of theory",
      "relevance_to_rqs": "how it addresses RQs",
      "relevance_to_model": "how it could be modeled in SD",
      "adjacency_level": "direct",
      "phd_contribution": "what novel contribution this enables",
      "model_additions": ["what to add to model"],
      "risk": "low|medium|high",
      "reward": "low|medium|high"
    }}
  ],
  "adjacent_opportunities": [
    {{
      "theory_name": "Theory Name",
      "key_citation": "Author Year",
      "description": "brief description",
      "why_adjacent": "why slightly off-center but valuable",
      "novel_angle": "what new perspective this brings",
      "adjacency_level": "adjacent",
      "phd_contribution": "potential contribution",
      "risk": "medium|high",
      "reward": "medium|high"
    }}
  ],
  "cross_domain_inspiration": [
    {{
      "theory": "Theory from different field",
      "source_domain": "where it comes from",
      "parallel": "how it relates to OSS development",
      "transfer_potential": "what insight could transfer",
      "adjacency_level": "exploratory",
      "risk": "high",
      "reward": "low|medium|high",
      "rationale": "why this is worth considering despite risk"
    }}
  ],
  "phd_strategy": {{
    "recommended_theories": ["list of 2-3 top recommendations"],
    "rationale": "why these specific theories",
    "integration_strategy": "how to integrate them with existing theories",
    "expected_impact": "what this enables for the PhD"
  }}
}}

Focus on theories that:
- Are established (not trendy buzzwords)
- Have empirical foundation
- Can be modeled in SD
- Contribute to knowledge gaps

Be bold but responsible - suggest theories that advance the work without derailing it.

Return ONLY the JSON structure, no additional text.
"""
    return prompt


def run_theory_discovery(
    rqs: list[str],
    current_theories: list[dict],
    rq_alignment: dict
) -> dict:
    """Discover new theories to strengthen research."""

    print("=" * 80)
    print("MODULE 5: ADJACENT THEORY DISCOVERY")
    print("=" * 80)

    # Create prompt
    print("\n1. Creating theory discovery prompt...")
    prompt = create_discovery_prompt(rqs, current_theories, rq_alignment)
    print(f"   ✓ Prompt created ({len(prompt)} characters)")

    # Call LLM
    print("\n2. Calling DeepSeek for theory discovery...")
    print("   (This may take 1-2 minutes...)")

    client = LLMClient(provider="deepseek")
    response = client.complete(prompt, temperature=0.4, max_tokens=4000)

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

    # Load current theories
    theories_path = knowledge_dir / "theories.csv"
    theories = []
    with open(theories_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('name'):
                theories.append(row)

    print("=" * 80)
    print("Loading data from oss_model project...")
    print("=" * 80)

    print(f"\n✓ Loaded RQ alignment from: {alignment_path}")
    print(f"✓ Loaded {len(rqs)} RQs from: {rq_path}")
    print(f"✓ Loaded {len(theories)} current theories from: {theories_path}\n")

    # Run discovery
    result = run_theory_discovery(rqs, theories, rq_alignment)

    # Save result
    output_path = Path(__file__).parent / "theory_discovery_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✓ Theory discovery complete! Saved to: {output_path}")
    print("=" * 80)

    # Print summary
    if "error" not in result:
        print("\n" + "=" * 80)
        print("THEORY DISCOVERY SUMMARY")
        print("=" * 80)

        high_rel = result.get("high_relevance", [])
        print(f"\nHigh Relevance Theories: {len(high_rel)}")
        for theory in high_rel:
            name = theory.get("theory_name", "Unknown")
            citation = theory.get("key_citation", "")
            risk = theory.get("risk", "unknown")
            reward = theory.get("reward", "unknown")
            print(f"  • {name} ({citation}) - Risk: {risk.upper()}, Reward: {reward.upper()}")

        adjacent = result.get("adjacent_opportunities", [])
        print(f"\nAdjacent Opportunities: {len(adjacent)}")
        for theory in adjacent[:2]:  # Show top 2
            name = theory.get("theory_name", "Unknown")
            angle = theory.get("novel_angle", "N/A")
            print(f"  • {name}: {angle[:60]}...")

        cross_domain = result.get("cross_domain_inspiration", [])
        print(f"\nCross-Domain Inspiration: {len(cross_domain)}")
        for theory in cross_domain[:1]:  # Show top 1
            name = theory.get("theory", "Unknown")
            domain = theory.get("source_domain", "Unknown")
            print(f"  • {name} (from {domain})")

        strategy = result.get("phd_strategy", {})
        recommended = strategy.get("recommended_theories", [])
        print(f"\nTop Recommendations: {', '.join(recommended)}")


if __name__ == "__main__":
    main()

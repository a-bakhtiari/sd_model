"""Thin wrapper delegating to modular pipeline for theory validation."""

from pathlib import Path
from sd_model.pipeline.theory_validation import validate_model


def main():
    print("Validating model against theories...")
    result = validate_model(Path("connections.json"), Path("loops_interpreted.json"), Path("knowledge/theories.csv"), Path("theory_validation.json"), api_key=None, model="deepseek-chat")
    print("\n📊 Overall Results:")
    print(f"Average alignment score: {result['average_alignment']:.1f}/10")
    print("\n🔍 Key findings:")
    print("Consistently missing connections:")
    for missing in result.get('consistent_missing', [])[:2]:
        s = missing.get('suggested', {})
        print(f"  - {s.get('from', '?')} → {s.get('to', '?')}")
    print("\n✅ Saved detailed analysis to theory_validation.json")


if __name__ == "__main__":
    main()

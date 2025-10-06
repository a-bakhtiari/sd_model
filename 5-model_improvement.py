"""Thin wrapper delegating to modular pipeline for improvements."""

from pathlib import Path
from sd_model.pipeline.improve import improve_model


def main():
    print("Generating model improvements based on theory validation...")
    output = improve_model(Path("theory_validation.json"), Path("connections.json"), Path("model_improvements.json"), api_key=None, model="deepseek-chat")
    print(f"\n📊 Improvement Summary:")
    print(f"Additions proposed: {output['statistics']['additions_proposed']}")
    print(f"Removals suggested: {output['statistics']['removals_suggested']}")
    print(f"New variables needed: {output['statistics']['new_variables']}")
    print("\n🎯 Implementation Order:")
    for i, step in enumerate(output.get('improvements', {}).get('implementation_order', []), 1):
        print(f"{i}. {step}")
    print("\n💾 Saved to model_improvements.json")
    print("\nNext: Review improvements and decide which to implement in Vensim")


if __name__ == "__main__":
    main()

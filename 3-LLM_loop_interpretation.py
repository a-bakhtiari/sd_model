"""Thin wrapper delegating to modular pipeline for loop interpretation."""

from pathlib import Path
from sd_model.pipeline.interpret import interpret_loops


def main():
    print("Sending loops to LLM for interpretation...")
    final_analysis = interpret_loops(Path("loops.json"), Path("loops_interpreted.json"), api_key=None, model="deepseek-chat")
    print("\n✅ Loop interpretation complete!")
    print("\n📊 Key Insights:")
    print(f"System pattern: {final_analysis.get('system_insights', 'N/A')}")
    print("\n🔝 Dominant loops:")
    for loop_name in final_analysis.get('dominant_loops', [])[:3]:
        print(f"  - {loop_name}")
    print("\n💾 Saved to loops_interpreted.json")


if __name__ == "__main__":
    main()

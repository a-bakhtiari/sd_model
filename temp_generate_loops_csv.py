#!/usr/bin/env python3
"""
Temporary script to regenerate loops CSV without rerunning entire pipeline.
"""
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.pipeline.csv_export import generate_loops_csv

def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"

    loops_path = artifacts_dir / "loops.json"
    descriptions_path = artifacts_dir / "loop_descriptions.json"
    citations_path = artifacts_dir / "loop_citations_verified.json"
    output_path = artifacts_dir / "loops_export.csv"

    print("Generating loops CSV...")
    print(f"  Loops: {loops_path}")
    print(f"  Descriptions: {descriptions_path}")
    print(f"  Citations: {citations_path}")
    print(f"  Output: {output_path}")
    print()

    # Generate CSV
    rows = generate_loops_csv(
        loops_path=loops_path,
        descriptions_path=descriptions_path,
        citations_path=citations_path,
        output_path=output_path,
    )

    print(f"✓ Generated {output_path}")
    print(f"  {rows} rows written")


if __name__ == "__main__":
    main()

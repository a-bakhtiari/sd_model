#!/usr/bin/env python3
"""Migrate existing artifacts from flat structure to organized subdirectories."""

from __future__ import annotations

import shutil
from pathlib import Path
import sys

# Map of old artifact names to new paths (relative to artifacts dir)
MIGRATION_MAP = {
    # Parsing artifacts
    "parsed.json": "parsing/parsed.json",
    "variables_llm.json": "parsing/variables_llm.json",
    "connections_llm.json": "parsing/connections_llm.json",
    "diagram_style.json": "parsing/diagram_style.json",
    # Connection artifacts
    "connections.json": "connections/connections.json",
    "connection_descriptions.json": "connections/connection_descriptions.json",
    "connection_citations.json": "connections/connection_citations.json",
    "connection_citations_verified.json": "connections/connection_citations_verified.json",
    "connection_citations_verification_debug.txt": "connections/connection_citations_verification_debug.txt",
    "connections_export.csv": "connections/connections_export.csv",
    # Loop artifacts
    "loops.json": "loops/loops.json",
    "loop_descriptions.json": "loops/loop_descriptions.json",
    "loop_citations.json": "loops/loop_citations.json",
    "loop_citations_verified.json": "loops/loop_citations_verified.json",
    "loop_citations_verification_debug.txt": "loops/loop_citations_verification_debug.txt",
    "loops_export.csv": "loops/loops_export.csv",
    # Theory artifacts
    "theory_validation.json": "theory/theory_validation.json",
    "theory_enhancement.json": "theory/theory_enhancement.json",
    "theory_enhancement_mdl.json": "theory/theory_enhancement_mdl.json",
    "theory_discovery.json": "theory/theory_discovery.json",
    # Research question artifacts
    "rq_alignment.json": "research_questions/rq_alignment.json",
    "rq_refinement.json": "research_questions/rq_refinement.json",
    # Improvement artifacts
    "gap_analysis.json": "improvements/gap_analysis.json",
    "model_improvements.json": "improvements/model_improvements.json",
}


def migrate_project(project_dir: Path, dry_run: bool = False) -> None:
    """Migrate artifacts for a single project."""
    artifacts_dir = project_dir / "artifacts"

    if not artifacts_dir.exists():
        print(f"  ⚠ No artifacts directory found in {project_dir}")
        return

    print(f"\n📁 Processing: {project_dir.name}")

    moved_count = 0
    skipped_count = 0

    for old_name, new_relative_path in MIGRATION_MAP.items():
        old_path = artifacts_dir / old_name
        new_path = artifacts_dir / new_relative_path

        if not old_path.exists():
            continue

        # Skip if already in new location
        if new_path.exists():
            print(f"  ⏭  {old_name} -> already exists at {new_relative_path}")
            skipped_count += 1
            continue

        if dry_run:
            print(f"  📋 Would move: {old_name} -> {new_relative_path}")
            moved_count += 1
        else:
            # Create parent directory if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            shutil.move(str(old_path), str(new_path))
            print(f"  ✓ Moved: {old_name} -> {new_relative_path}")
            moved_count += 1

    if moved_count == 0 and skipped_count == 0:
        print(f"  ℹ  No artifacts to migrate")
    else:
        print(f"  Summary: {moved_count} moved, {skipped_count} skipped")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate artifacts from flat to organized structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Migrate only a specific project (e.g., 'oss_model')",
    )

    args = parser.parse_args()

    # Find projects directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    projects_dir = repo_root / "projects"

    if not projects_dir.exists():
        print(f"❌ Projects directory not found: {projects_dir}")
        sys.exit(1)

    print("🔄 Artifact Migration Tool")
    print(f"Projects directory: {projects_dir}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be moved\n")

    # Process projects
    if args.project:
        project_dir = projects_dir / args.project
        if not project_dir.exists():
            print(f"❌ Project not found: {project_dir}")
            sys.exit(1)
        migrate_project(project_dir, dry_run=args.dry_run)
    else:
        # Process all projects
        project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]

        if not project_dirs:
            print("ℹ️  No project directories found")
            return

        for project_dir in sorted(project_dirs):
            migrate_project(project_dir, dry_run=args.dry_run)

    print("\n✅ Migration complete!")
    if args.dry_run:
        print("   Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()

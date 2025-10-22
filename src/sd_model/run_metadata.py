"""Utilities for managing pipeline run metadata and versioning."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def generate_run_id(custom_name: Optional[str] = None) -> str:
    """Generate a unique run ID with timestamp.

    Args:
        custom_name: Optional custom name to append to timestamp

    Returns:
        Run ID in format: "20251010_113305" or "20251010_113305_custom-name"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if custom_name and custom_name.strip():
        # Sanitize custom name (remove special chars, replace spaces with hyphens)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in custom_name)
        safe_name = safe_name.strip("-_")
        return f"{timestamp}_{safe_name}"

    return timestamp


def create_run_metadata(
    run_id: str,
    project: str,
    artifacts_dir: Path,
    pipeline_args: Dict,
    pipeline_result: Dict
) -> Dict:
    """Create metadata for a pipeline run.

    Args:
        run_id: Unique run identifier
        project: Project name
        artifacts_dir: Path to artifacts directory for this run
        pipeline_args: Arguments passed to run_pipeline
        pipeline_result: Result dictionary from run_pipeline

    Returns:
        Dictionary containing run metadata
    """
    metadata = {
        "run_id": run_id,
        "project": project,
        "timestamp": datetime.now().isoformat(),
        "artifacts_directory": str(artifacts_dir),
        "pipeline_configuration": {
            "improve_model": pipeline_args.get("improve_model", False),
            "verify_citations": pipeline_args.get("verify_cit", False),
            "discover_papers": pipeline_args.get("discover_papers", False),
            "apply_patch": pipeline_args.get("apply_patch", False),
        },
        "artifacts_generated": {
            key: str(value) if value else None
            for key, value in pipeline_result.items()
            if value is not None
        },
        "summary": {
            "total_artifacts": len([v for v in pipeline_result.values() if v]),
        }
    }

    return metadata


def save_run_metadata(
    artifacts_dir: Path,
    metadata: Dict
) -> Path:
    """Save run metadata to JSON file.

    Args:
        artifacts_dir: Directory where artifacts are saved
        metadata: Metadata dictionary

    Returns:
        Path to saved metadata file
    """
    metadata_path = artifacts_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


def find_latest_step1_run(project_base_dir: Path) -> Optional[str]:
    """Find the most recent run that has Step 1 (theory planning) output.

    Args:
        project_base_dir: Base directory for the project (e.g., projects/oss_model)

    Returns:
        Run ID of the most recent run with Step 1 output, or None if not found
    """
    runs_dir = project_base_dir / "artifacts" / "runs"

    if not runs_dir.exists():
        return None

    # Find all run directories with Step 1 output
    step1_runs = []
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue

        step1_path = run_dir / "theory" / "theory_planning_step1.json"
        if step1_path.exists():
            step1_runs.append(run_dir.name)

    if not step1_runs:
        return None

    # Sort by run_id (timestamp is in the name, so lexicographic sort works)
    # Most recent will be last
    step1_runs.sort()
    return step1_runs[-1]


def update_latest_symlink(base_artifacts_dir: Path, run_id: str) -> None:
    """Create or update 'latest' symlink to point to most recent run.

    Args:
        base_artifacts_dir: Base artifacts directory (e.g., projects/oss_model/artifacts)
        run_id: Run ID to point to
    """
    runs_dir = base_artifacts_dir / "runs"
    latest_link = runs_dir / "latest"

    # Remove existing symlink if it exists
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()

    # Create new symlink (relative path for portability)
    try:
        os.symlink(run_id, latest_link, target_is_directory=True)
    except OSError:
        # On Windows or systems without symlink support, just skip
        pass

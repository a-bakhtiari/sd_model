from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AppConfig


@dataclass
class ProjectPaths:
    """Resolved paths for a given project, including knowledge assets and artifacts."""

    project: str
    base_dir: Path
    artifacts_dir: Path
    db_dir: Path
    mdl_dir: Path
    knowledge_dir: Path
    theories_dir: Path
    references_bib_path: Path
    feedback_json_path: Path

    # Common artifacts
    parsed_path: Path
    loops_path: Path
    interpret_path: Path
    connections_path: Path
    theory_validation_path: Path
    model_improvements_path: Path

    def ensure(self) -> None:
        """Ensure required directories exist."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.mdl_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.theories_dir.mkdir(parents=True, exist_ok=True)


def for_project(cfg: AppConfig, project: str) -> ProjectPaths:
    base = cfg.projects_dir / project
    knowledge_dir = base / "knowledge"
    paths = ProjectPaths(
        project=project,
        base_dir=base,
        artifacts_dir=base / "artifacts",
        db_dir=base / "db",
        mdl_dir=base / "mdl",
        knowledge_dir=knowledge_dir,
        theories_dir=knowledge_dir / "theories",
        references_bib_path=knowledge_dir / "references.bib",
        feedback_json_path=knowledge_dir / "feedback.json",
        parsed_path=base / "artifacts" / "parsed.json",
        loops_path=base / "artifacts" / "loops.json",
        interpret_path=base / "artifacts" / "interpretation.json",
        connections_path=base / "artifacts" / "connections.json",
        theory_validation_path=base / "artifacts" / "theory_validation.json",
        model_improvements_path=base / "artifacts" / "model_improvements.json",
    )
    return paths


def first_mdl_file(paths: ProjectPaths) -> Optional[Path]:
    """Return first .mdl file in the project's mdl folder, if any."""
    if not paths.mdl_dir.exists():
        return None
    for p in sorted(paths.mdl_dir.glob("*.mdl")):
        return p
    return None

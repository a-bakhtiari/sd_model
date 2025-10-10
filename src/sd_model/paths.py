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
    enhanced_mdl_dir: Path
    knowledge_dir: Path
    theories_dir: Path
    references_bib_path: Path
    feedback_json_path: Path

    # Artifact subdirectories
    parsing_dir: Path
    connections_dir: Path
    loops_dir: Path
    theory_dir: Path
    rq_dir: Path
    improvements_dir: Path

    # Parsing artifacts
    parsed_path: Path
    variables_llm_path: Path
    connections_llm_path: Path
    diagram_style_path: Path

    # Connection artifacts
    connections_path: Path
    connection_descriptions_path: Path
    connection_citations_path: Path
    connection_citations_verified_path: Path
    connection_citations_verification_debug_path: Path
    connections_export_path: Path

    # Loop artifacts
    loops_path: Path
    loop_descriptions_path: Path
    loop_citations_path: Path
    loop_citations_verified_path: Path
    loop_citations_verification_debug_path: Path
    loops_export_path: Path

    # Theory artifacts
    theory_validation_path: Path
    theory_enhancement_path: Path
    theory_enhancement_mdl_path: Path
    theory_discovery_path: Path

    # Research question artifacts
    rq_alignment_path: Path
    rq_refinement_path: Path
    rq_txt_path: Path

    # Improvement artifacts
    gap_analysis_path: Path
    model_improvements_path: Path

    # Legacy compatibility
    interpret_path: Path

    def ensure(self) -> None:
        """Ensure required directories exist."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.parsing_dir.mkdir(parents=True, exist_ok=True)
        self.connections_dir.mkdir(parents=True, exist_ok=True)
        self.loops_dir.mkdir(parents=True, exist_ok=True)
        self.theory_dir.mkdir(parents=True, exist_ok=True)
        self.rq_dir.mkdir(parents=True, exist_ok=True)
        self.improvements_dir.mkdir(parents=True, exist_ok=True)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.mdl_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.theories_dir.mkdir(parents=True, exist_ok=True)


def for_project(cfg: AppConfig, project: str) -> ProjectPaths:
    base = cfg.projects_dir / project
    artifacts_dir = base / "artifacts"
    knowledge_dir = base / "knowledge"

    # Artifact subdirectories
    parsing_dir = artifacts_dir / "parsing"
    connections_dir = artifacts_dir / "connections"
    loops_dir = artifacts_dir / "loops"
    theory_dir = artifacts_dir / "theory"
    rq_dir = artifacts_dir / "research_questions"
    improvements_dir = artifacts_dir / "improvements"

    paths = ProjectPaths(
        project=project,
        base_dir=base,
        artifacts_dir=artifacts_dir,
        db_dir=base / "db",
        mdl_dir=base / "mdl",
        enhanced_mdl_dir=base / "mdl" / "enhanced",
        knowledge_dir=knowledge_dir,
        theories_dir=knowledge_dir / "theories",
        references_bib_path=knowledge_dir / "references.bib",
        feedback_json_path=knowledge_dir / "feedback.json",
        # Subdirectories
        parsing_dir=parsing_dir,
        connections_dir=connections_dir,
        loops_dir=loops_dir,
        theory_dir=theory_dir,
        rq_dir=rq_dir,
        improvements_dir=improvements_dir,
        # Parsing artifacts
        parsed_path=parsing_dir / "parsed.json",
        variables_llm_path=parsing_dir / "variables_llm.json",
        connections_llm_path=parsing_dir / "connections_llm.json",
        diagram_style_path=parsing_dir / "diagram_style.json",
        # Connection artifacts
        connections_path=connections_dir / "connections.json",
        connection_descriptions_path=connections_dir / "connection_descriptions.json",
        connection_citations_path=connections_dir / "connection_citations.json",
        connection_citations_verified_path=connections_dir / "connection_citations_verified.json",
        connection_citations_verification_debug_path=connections_dir / "connection_citations_verification_debug.txt",
        connections_export_path=connections_dir / "connections_export.csv",
        # Loop artifacts
        loops_path=loops_dir / "loops.json",
        loop_descriptions_path=loops_dir / "loop_descriptions.json",
        loop_citations_path=loops_dir / "loop_citations.json",
        loop_citations_verified_path=loops_dir / "loop_citations_verified.json",
        loop_citations_verification_debug_path=loops_dir / "loop_citations_verification_debug.txt",
        loops_export_path=loops_dir / "loops_export.csv",
        # Theory artifacts
        theory_validation_path=theory_dir / "theory_validation.json",
        theory_enhancement_path=theory_dir / "theory_enhancement.json",
        theory_enhancement_mdl_path=theory_dir / "theory_enhancement_mdl.json",
        theory_discovery_path=theory_dir / "theory_discovery.json",
        # Research question artifacts
        rq_alignment_path=rq_dir / "rq_alignment.json",
        rq_refinement_path=rq_dir / "rq_refinement.json",
        rq_txt_path=knowledge_dir / "RQ.txt",
        # Improvement artifacts
        gap_analysis_path=improvements_dir / "gap_analysis.json",
        model_improvements_path=improvements_dir / "model_improvements.json",
        # Legacy compatibility
        interpret_path=artifacts_dir / "interpretation.json",
    )
    return paths


def first_mdl_file(paths: ProjectPaths) -> Optional[Path]:
    """Return first .mdl file in the project's mdl folder, if any."""
    if not paths.mdl_dir.exists():
        return None
    for p in sorted(paths.mdl_dir.glob("*.mdl")):
        return p
    return None

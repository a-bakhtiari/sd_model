from __future__ import annotations
from pathlib import Path
from sd_model.config import settings


def projects_dir() -> Path:
    return Path(getattr(settings, "projects_dir", "projects"))


def project_name(default: str | None = None) -> str:
    name = getattr(settings, "project_name", None) or default or "default"
    return name


def project_root(name: str | None = None) -> Path:
    root = projects_dir() / project_name(name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def artifacts_dir(name: str | None = None) -> Path:
    d = project_root(name) / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def mdl_dir(name: str | None = None) -> Path:
    d = project_root(name) / "mdl"
    d.mkdir(parents=True, exist_ok=True)
    return d


def connections_path(name: str | None = None) -> Path:
    return artifacts_dir(name) / "connections.json"


def loops_path(name: str | None = None) -> Path:
    return artifacts_dir(name) / "loops.json"


def loops_interpreted_path(name: str | None = None) -> Path:
    return artifacts_dir(name) / "loops_interpreted.json"


def theory_validation_path(name: str | None = None) -> Path:
    return artifacts_dir(name) / "theory_validation.json"


def model_improvements_path(name: str | None = None) -> Path:
    return artifacts_dir(name) / "model_improvements.json"


def provenance_db_path(name: str | None = None) -> Path:
    return project_root(name) / "provenance.sqlite"


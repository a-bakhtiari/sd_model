from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class AppConfig:
    """Top-level configuration for the application.

    - `root_dir`: Repository root (assumed to contain `projects`, `schemas`, `src`).
    - `projects_dir`: Folder containing per-project data and artifacts.
    - `schemas_dir`: Folder with JSON Schemas used for artifact validation.
    - `env`: Dictionary of environment-derived toggles.
    """

    root_dir: Path
    projects_dir: Path
    schemas_dir: Path
    env: dict


def detect_repo_root() -> Path:
    """Detect repository root by walking upwards until `projects` or `src` exists.

    Falls back to current working directory.
    """
    cwd = Path.cwd().resolve()
    for p in [cwd] + list(cwd.parents):
        if (p / "projects").exists() or (p / "src").exists():
            return p
    return cwd


def load_config() -> AppConfig:
    # Load .env file from repository root
    root = detect_repo_root()
    load_dotenv(root / ".env")

    projects_dir = root / "projects"
    schemas_dir = root / "schemas"
    env = {
        "USE_LLM": os.getenv("SD_USE_LLM", "0") in {"1", "true", "True"},
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "SEMANTIC_SCHOLAR_API_KEY": os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
    }
    return AppConfig(
        root_dir=root,
        projects_dir=projects_dir,
        schemas_dir=schemas_dir,
        env=env,
    )


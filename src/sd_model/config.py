import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path


def _load_env():
    load_dotenv(dotenv_path=Path(".env"), override=False)


@dataclass
class Settings:
    deepseek_api_key: Optional[str]
    model_name: str
    provenance_db: Optional[str]
    projects_dir: str
    project_name: str


def _load_settings() -> Settings:
    _load_env()
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        provenance_db=os.getenv("PROVENANCE_DB"),
        projects_dir=os.getenv("PROJECTS_DIR", "projects"),
        project_name=os.getenv("PROJECT_NAME", "oss_model"),
    )


settings = _load_settings()

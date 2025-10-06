from pydantic import BaseSettings, Field
from dotenv import load_dotenv
from pathlib import Path


# Load .env automatically from project root if present
load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    # Read from environment or .env
    deepseek_api_key: str | None = Field(default=None, env="DEEPSEEK_API_KEY")
    model_name: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")
    provenance_db: str = Field(default="provenance.sqlite", env="PROVENANCE_DB")


settings = Settings()

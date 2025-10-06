from pydantic import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str | None = None
    model_name: str = "deepseek-chat"

    class Config:
        env_prefix = "DEEPSEEK_"


settings = Settings()  # loaded from env


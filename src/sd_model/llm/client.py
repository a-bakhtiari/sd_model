from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# Load .env file from repository root
# Walk up from this file to find the repo root (contains .env)
_current_file = Path(__file__).resolve()
_repo_root = _current_file.parent.parent.parent.parent  # src/sd_model/llm/client.py -> go up 4 levels to repo root
_env_path = _repo_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class LLMClient:
    """Very thin LLM client wrapper with support for OpenAI-compatible and DeepSeek APIs."""

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        """Initialize LLM client.

        Args:
            model: Specific model name (e.g., "gpt-4o", "deepseek-chat")
            provider: Force specific provider ("openai" or "deepseek"). Default: "deepseek"
        """
        self._provider: Optional[str] = None
        self._enabled = False
        self._api_key: Optional[str] = None
        self._openai = None

        # Default to DeepSeek unless explicitly requested OpenAI
        provider = provider or "deepseek"

        openai_key = os.getenv("OPENAI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")

        if provider == "openai" and openai_key:
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            try:
                import openai  # type: ignore

                openai.api_key = openai_key
                self._openai = openai
                self._provider = "openai"
                self._api_key = openai_key
                self._enabled = True
                print(f"LLM: Using OpenAI ({self.model})")
            except Exception as e:
                raise RuntimeError(f"OpenAI requested but failed to initialize: {e}")
        elif provider == "deepseek" and deepseek_key:
            self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            self._provider = "deepseek"
            self._api_key = deepseek_key
            self._enabled = True
            print(f"LLM: Using DeepSeek ({self.model})")
        else:
            raise RuntimeError(f"Provider '{provider}' requested but API key not found in .env")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete(self, prompt: str, temperature: float = 0.0) -> str:
        if not self._enabled or not self._provider:
            return "[LLM Fallback] Deterministic summary generated without external calls."

        try:
            if self._provider == "openai" and self._openai:
                resp = self._openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                return resp.choices[0].message["content"]

            if self._provider == "deepseek" and self._api_key:
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "stream": False,
                    },
                    timeout=180,  # Increased to 3 minutes for large prompts
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"LLM API call failed: {exc}")

        return "[LLM Fallback] Deterministic summary generated without external calls."

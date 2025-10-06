from __future__ import annotations
import requests
from sd_model.config import settings


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.deepseek_api_key
        self.model = model or settings.model_name

    def chat(self, prompt: str, temperature: float = 0.0) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        if "```" in content:
            # strip markdown fences if present
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0]
            else:
                content = content.split("```")[-2]
        return content

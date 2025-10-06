from __future__ import annotations
import os
import requests


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model

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


from __future__ import annotations

import os
from typing import Optional


class LLMClient:
    """Very thin LLM client wrapper.

    If OpenAI is available and `OPENAI_API_KEY` is set, uses that. Otherwise,
    returns heuristic summaries to allow the pipeline to run deterministically.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._openai = None
        self._enabled = False
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai  # type: ignore

                openai.api_key = api_key
                self._openai = openai
                self._enabled = True
            except Exception:
                self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete(self, prompt: str, temperature: float = 0.0) -> str:
        if not self._enabled:
            # Deterministic fallback: return a concise echo-based summary
            return (
                "[LLM Fallback] Deterministic summary generated without external calls.\n"[
                    :1000
                ]
            )
        # Note: Keep this minimal to avoid coupling. Some environments may not allow network.
        try:
            resp = self._openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return resp.choices[0].message["content"]
        except Exception as e:
            # Fallback from errors
            return (
                f"[LLM Error: {e}] Fallback summary."
            )


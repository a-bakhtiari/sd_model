from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generator, Optional

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
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
            try:
                from openai import OpenAI  # type: ignore

                self._openai = OpenAI(api_key=openai_key)
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

    def complete(self, prompt: str, temperature: float = 0.0, max_tokens: Optional[int] = None, timeout: int = 180) -> str:
        if not self._enabled or not self._provider:
            return "[LLM Fallback] Deterministic summary generated without external calls."

        try:
            if self._provider == "openai" and self._openai:
                result = self._openai.responses.create(
                    model=self.model,
                    input=prompt,
                    reasoning={"effort": "low"}
                )
                return result.output_text

            if self._provider == "deepseek" and self._api_key:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "stream": False,
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout,  # Configurable timeout, default 3 minutes
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"LLM API call failed: {exc}")

        return "[LLM Fallback] Deterministic summary generated without external calls."

    def chat(self, messages: list, temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """Send a chat conversation to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                      e.g., [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            The assistant's response text
        """
        if not self._enabled or not self._provider:
            return "Sorry, the LLM client is not enabled. Please configure your API keys in .env file."

        try:
            if self._provider == "openai" and self._openai:
                # OpenAI chat completion
                response = self._openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            if self._provider == "deepseek" and self._api_key:
                # DeepSeek chat completion
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"LLM chat call failed: {exc}")

        return "Sorry, something went wrong with the LLM request."

    def chat_stream(self, messages: list, temperature: float = 0.7, max_tokens: Optional[int] = None) -> Generator[str, None, None]:
        """Stream a chat conversation from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Text chunks as they arrive from the API
        """
        if not self._enabled or not self._provider:
            yield "Sorry, the LLM client is not enabled. Please configure your API keys in .env file."
            return

        try:
            if self._provider == "openai" and self._openai:
                # OpenAI streaming
                stream = self._openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            elif self._provider == "deepseek" and self._api_key:
                # DeepSeek streaming
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=180,
                    stream=True
                )
                response.raise_for_status()

                # Parse SSE (Server-Sent Events) format
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get('choices', [{}])[0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as exc:
            yield f"\n\nError: {str(exc)}"

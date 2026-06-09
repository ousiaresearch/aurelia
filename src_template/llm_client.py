"""
llm_client.py — Zero-dependency LLM client for OpenAI-compatible APIs.

No external dependencies. Pure stdlib urllib. Works with:
- OpenRouter (openrouter.ai/api/v1)
- OpenAI (api.openai.com/v1)
- CommandCode (api.commandcode.ai/provider/v1)
- Any OpenAI-compatible endpoint

Used by rich_narrative.py to generate prose from simulation state.
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


class LLMClient:
    """Lightweight LLM client. No deps beyond Python stdlib."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "deepseek/deepseek-v4-pro",
        timeout: int = 60,
    ):
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self._available = None  # Lazy check

    @property
    def available(self) -> bool:
        """Check if the client has valid credentials."""
        if self._available is None:
            self._available = bool(self.api_key and len(self.api_key) > 10)
        return self._available

    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        stop: Optional[list] = None,
    ) -> Optional[str]:
        """
        Send a chat completion request.
        Returns the response text, or None on failure.
        Never raises — always graceful.
        """
        if not self.available:
            return None

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            body["stop"] = stop

        url = f"{self.base_url}/chat/completions"
        data = json.dumps(body).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://aurelia-simulation.colab",
        }

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    def try_chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        max_retries: int = 2,
    ) -> Optional[str]:
        """Chat with retries. Returns None after exhausted retries."""
        for attempt in range(max_retries + 1):
            result = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
            if result:
                return result
            if attempt < max_retries:
                time.sleep(1.0 * (attempt + 1))
        return None


# Global singleton for speed-run use
_client: Optional[LLMClient] = None


def get_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMClient:
    """Get or create the global LLM client."""
    global _client
    if _client is None:
        _client = LLMClient(
            base_url=base_url,
            api_key=api_key,
            model=model or "deepseek/deepseek-v4-pro",
        )
    return _client


def set_client(client: LLMClient):
    """Set the global LLM client explicitly."""
    global _client
    _client = client

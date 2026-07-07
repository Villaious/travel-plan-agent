from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from travel_agent.core.config import get_env, get_float_env, get_int_env
from travel_agent.core.exceptions import AgentError


class OpenAICompatibleLLM:
    """Small OpenAI-compatible chat client backed by urllib."""

    def __init__(self) -> None:
        self.api_key = get_env("LLM_API_KEY") or get_env("OPENAI_API_KEY")
        self.base_url = (get_env("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = get_env("LLM_MODEL") or "gpt-4o-mini"
        self.temperature = get_float_env("LLM_TEMPERATURE", 0.3)
        self.timeout = get_int_env("LLM_TIMEOUT", 60)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict[str, str]], response_format: dict[str, str] | None = None) -> str:
        if not self.api_key:
            raise AgentError("LLM_API_KEY is not configured.")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentError(f"LLM request failed: {exc}") from exc
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AgentError(f"Unexpected LLM response: {data}") from exc

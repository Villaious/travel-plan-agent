from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from travel_agent.core.config import get_env, get_int_env
from travel_agent.tools.base import BaseTool


class SerpApiSearchTool(BaseTool):
    name = "serpapi_search"
    description = "Search scenic spot information through SerpApi Google Search API."

    endpoint = "https://serpapi.com/search"

    def __init__(self) -> None:
        self.api_key = get_env("SERPAPI_API_KEY")
        self.timeout = get_int_env("SERPAPI_TIMEOUT", 15)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.api_key != "your_serpapi_api_key_here")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        if not self.enabled:
            return {"source": "disabled", "results": []}
        query = kwargs.get("query", "景点 旅游 攻略")
        location = kwargs.get("location", "China")
        num = int(kwargs.get("num", 5))
        params = {
            "engine": "google",
            "q": query,
            "location": location,
            "hl": "zh-cn",
            "gl": "cn",
            "num": str(num),
            "api_key": self.api_key,
        }
        url = f"{self.endpoint}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"source": "serpapi", "results": [], "error": str(exc)}
        return {
            "source": "serpapi",
            "query": query,
            "results": self._normalize(payload, num),
        }

    def _normalize(self, payload: dict[str, Any], num: int) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        knowledge_graph = payload.get("knowledge_graph") or {}
        if knowledge_graph:
            description = knowledge_graph.get("description") or knowledge_graph.get("snippet") or ""
            if description:
                results.append(
                    {
                        "title": knowledge_graph.get("title", "知识图谱"),
                        "snippet": description,
                        "link": knowledge_graph.get("source", {}).get("link", ""),
                    }
                )
        answer_box = payload.get("answer_box") or {}
        if answer_box.get("snippet"):
            results.append(
                {
                    "title": answer_box.get("title", "精选摘要"),
                    "snippet": answer_box.get("snippet", ""),
                    "link": answer_box.get("link", ""),
                }
            )
        for item in payload.get("organic_results", [])[:num]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                }
            )
        return [item for item in results if item.get("snippet")][:num]

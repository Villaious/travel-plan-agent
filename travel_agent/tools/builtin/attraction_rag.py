from __future__ import annotations

import hashlib
import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from travel_agent.core.config import get_env, get_int_env
from travel_agent.tools.base import BaseTool


VECTOR_SIZE = 384


ATTRACTION_KNOWLEDGE: list[dict[str, Any]] = [
    {
        "destination": "上海",
        "name": "外滩",
        "type": "城市漫步",
        "lat": 31.2400,
        "lng": 121.4900,
        "ticket": 0,
        "duration": 90,
        "tags": ["城市漫步", "摄影", "夜景", "建筑"],
        "content": "外滩是上海最具代表性的城市天际线观景地，适合第一次到上海的游客安排在上午或傍晚。这里可以看到万国建筑群、黄浦江和陆家嘴 skyline，适合城市漫步、摄影和夜景观赏。",
    },
    {
        "destination": "上海",
        "name": "上海博物馆",
        "type": "文化",
        "lat": 31.2304,
        "lng": 121.4700,
        "ticket": 0,
        "duration": 120,
        "tags": ["文化", "博物馆", "历史", "雨天"],
        "content": "上海博物馆位于人民广场附近，收藏青铜器、陶瓷、书画等中国古代艺术精品。它适合文化偏好用户，也适合作为雨天或高温天气下的室内景点。",
    },
    {
        "destination": "北京",
        "name": "故宫博物院",
        "type": "文化",
        "lat": 39.9163,
        "lng": 116.3972,
        "ticket": 60,
        "duration": 240,
        "tags": ["文化", "历史", "博物馆", "建筑"],
        "content": "故宫博物院是北京文化旅行的核心景点，适合历史、建筑、博物馆偏好用户。建议预留半天时间，从午门进入，沿中轴线游览三大殿和后宫区域。",
    },
    {
        "destination": "北京",
        "name": "天坛公园",
        "type": "文化",
        "lat": 39.8822,
        "lng": 116.4066,
        "ticket": 34,
        "duration": 150,
        "tags": ["文化", "建筑", "公园", "城市漫步"],
        "content": "天坛公园以祈年殿、圜丘、回音壁等礼制建筑闻名，也有开阔的林荫空间。它适合文化建筑兴趣，也适合想把城市漫步和历史体验结合起来的游客。",
    },
]


class QdrantAttractionRagTool(BaseTool):
    name = "qdrant_attraction_rag"
    description = "Retrieve attraction knowledge from Qdrant by RAG."

    def __init__(self) -> None:
        self.url = get_env("QDRANT_URL").rstrip("/")
        self.api_key = get_env("QDRANT_API_KEY")
        self.collection = get_env("QDRANT_COLLECTION", "travel_attraction_knowledge")
        self.timeout = get_int_env("QDRANT_TIMEOUT", 10)
        self._seeded = False

    @property
    def enabled(self) -> bool:
        invalid_values = {"", "your_qdrant_api_key_here", "https://your-cluster.qdrant.tech:6333"}
        return self.url not in invalid_values and self.api_key not in invalid_values

    def run(self, **kwargs: Any) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        destination = kwargs.get("destination", "上海")
        preferences = kwargs.get("preferences", []) or []
        limit = int(kwargs.get("limit", 4))
        try:
            self._ensure_collection()
            self._seed_knowledge()
            return self._search(destination, preferences, limit)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
            return []


    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        if not self.enabled or not documents:
            return 0
        try:
            self._ensure_collection()
            self._seed_knowledge()
            points = []
            for item in documents:
                document = self._normalize_document(item)
                text = self._document_text(document)
                payload = {**document, "text": text, "source": "serpapi_rag"}
                points.append({"id": self._point_id(document), "vector": self._embed(text), "payload": payload})
            self._request("PUT", f"/collections/{self.collection}/points?wait=true", {"points": points})
            return len(points)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
            return 0

    def _normalize_document(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "destination": item.get("destination", ""),
            "name": item.get("name", "未命名景点"),
            "type": item.get("type", "景区"),
            "lat": item.get("lat", 0),
            "lng": item.get("lng", 0),
            "ticket": item.get("ticket", 0),
            "duration": item.get("duration", 90),
            "tags": item.get("tags", []),
            "content": item.get("content") or item.get("reason", ""),
            "advantages": item.get("advantages", []),
            "suitable_for": item.get("suitable_for", []),
        }
    def _ensure_collection(self) -> None:
        response = self._request("GET", f"/collections/{self.collection}", allow_error=True)
        if response.get("result"):
            return
        self._request(
            "PUT",
            f"/collections/{self.collection}",
            {
                "vectors": {
                    "size": VECTOR_SIZE,
                    "distance": "Cosine",
                }
            },
        )

    def _seed_knowledge(self) -> None:
        if self._seeded:
            return
        points = []
        for item in ATTRACTION_KNOWLEDGE:
            text = self._document_text(item)
            payload = {**item, "text": text, "source": "qdrant_rag"}
            points.append({"id": self._point_id(item), "vector": self._embed(text), "payload": payload})
        self._request("PUT", f"/collections/{self.collection}/points?wait=true", {"points": points})
        self._seeded = True

    def _search(self, destination: str, preferences: list[str], limit: int) -> list[dict[str, Any]]:
        query = f"目的地：{destination}；偏好：{'、'.join(preferences) or '经典旅行'}；请检索适合旅行规划的景点知识。"
        payload = {
            "vector": self._embed(query),
            "limit": limit,
            "with_payload": True,
            "score_threshold": 0.05,
            "filter": {"must": [{"key": "destination", "match": {"value": destination}}]},
        }
        response = self._request("POST", f"/collections/{self.collection}/points/search", payload)
        results = []
        for item in response.get("result", []):
            payload = item.get("payload", {})
            results.append(
                {
                    "name": payload.get("name", "未命名景点"),
                    "type": payload.get("type", "spot"),
                    "lat": payload.get("lat", 0),
                    "lng": payload.get("lng", 0),
                    "ticket": payload.get("ticket", 0),
                    "duration": payload.get("duration", 90),
                    "tags": payload.get("tags", []),
                    "reason": f"RAG知识库命中：{payload.get('content', '')}",
                    "source": "qdrant_rag",
                    "rag_score": round(float(item.get("score", 0)), 4),
                }
            )
        return [item for item in results if item["lat"] and item["lng"]]

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None, allow_error: bool = False) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.url}{path}",
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if allow_error:
                return {}
            raise exc

    def _document_text(self, item: dict[str, Any]) -> str:
        return f"{item['destination']} {item['name']} {item['type']} {' '.join(item.get('tags', []))} {item.get('content', '')} {' '.join(item.get('advantages', []))} {' '.join(item.get('suitable_for', []))}"

    def _point_id(self, item: dict[str, Any]) -> int:
        digest = hashlib.sha256(f"{item['destination']}:{item['name']}".encode("utf-8")).hexdigest()
        return int(digest[:15], 16)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * VECTOR_SIZE
        tokens = self._tokens(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _tokens(self, text: str) -> list[str]:
        chars = [char for char in text.lower() if not char.isspace()]
        grams = chars[:]
        grams.extend("".join(chars[index:index + 2]) for index in range(max(0, len(chars) - 1)))
        return grams or ["travel"]


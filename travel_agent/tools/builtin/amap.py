from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from travel_agent.core.config import get_env, get_int_env
from travel_agent.core.exceptions import ToolError
from travel_agent.tools.base import BaseTool


class AmapPlaceSearchTool(BaseTool):
    name = "amap_place_search"
    description = "Search POIs through Amap Web Service place text API."

    endpoint = "https://restapi.amap.com/v3/place/text"

    def __init__(self) -> None:
        self.api_key = get_env("AMAP_API_KEY")
        self.timeout = get_int_env("AMAP_TIMEOUT", 10)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def run(self, **kwargs: Any) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ToolError("AMAP_API_KEY is not configured.")
        params = {
            "key": self.api_key,
            "keywords": kwargs.get("keywords", "景点"),
            "city": kwargs.get("city", ""),
            "citylimit": str(kwargs.get("citylimit", "true")).lower(),
            "offset": str(kwargs.get("offset", 20)),
            "page": str(kwargs.get("page", 1)),
            "extensions": kwargs.get("extensions", "base"),
            "output": "JSON",
        }
        if kwargs.get("types"):
            params["types"] = kwargs["types"]
        url = f"{self.endpoint}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ToolError(f"Amap place search failed: {exc}") from exc
        if payload.get("status") != "1":
            raise ToolError(f"Amap place search error: {payload.get('info', 'UNKNOWN')}")
        return [self._normalize_poi(item, kwargs.get("default_category", "spot")) for item in payload.get("pois", [])]

    def _normalize_poi(self, poi: dict[str, Any], category: str) -> dict[str, Any]:
        lng, lat = self._parse_location(poi.get("location", ""))
        name = poi.get("name") or "未命名地点"
        return {
            "name": name,
            "type": poi.get("type") or category,
            "address": poi.get("address") or "",
            "lat": lat,
            "lng": lng,
            "ticket": 0,
            "duration": 90 if category == "spot" else 60,
            "price": self._estimate_price(category),
            "tags": self._tags_from_type(poi.get("type", ""), category),
            "reason": f"来自高德地图POI搜索：{name}。",
            "source": "amap",
            "amap_id": poi.get("id", ""),
        }

    def _parse_location(self, location: str) -> tuple[float, float]:
        if not location or "," not in location:
            return 0.0, 0.0
        lng_text, lat_text = location.split(",", 1)
        try:
            return float(lng_text), float(lat_text)
        except ValueError:
            return 0.0, 0.0

    def _estimate_price(self, category: str) -> int:
        if category == "hotel":
            return 480
        if category == "restaurant":
            return 80
        return 0

    def _tags_from_type(self, poi_type: str, category: str) -> list[str]:
        tags = [category]
        for keyword in ["文化", "美食", "酒店", "公园", "博物馆", "风景", "购物", "城市漫步", "餐饮", "中餐", "小吃"]:
            if keyword in poi_type:
                tags.append(keyword)
        return tags


class AmapRoutePlanningTool(BaseTool):
    name = "amap_route_planning"
    description = "Plan real routes through Amap walking, driving or transit APIs."

    endpoints = {
        "walking": "https://restapi.amap.com/v3/direction/walking",
        "driving": "https://restapi.amap.com/v3/direction/driving",
        "transit": "https://restapi.amap.com/v3/direction/transit/integrated",
    }

    def __init__(self) -> None:
        self.api_key = get_env("AMAP_API_KEY")
        self.timeout = get_int_env("AMAP_TIMEOUT", 10)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def run(self, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            raise ToolError("AMAP_API_KEY is not configured.")
        route_type = kwargs.get("route_type", "walking")
        if route_type not in self.endpoints:
            route_type = "walking"
        origin = kwargs["origin"]
        destination = kwargs["destination"]
        params = {
            "key": self.api_key,
            "origin": self._location(origin),
            "destination": self._location(destination),
            "output": "JSON",
        }
        if route_type == "transit":
            params["city"] = kwargs.get("city") or kwargs.get("origin_city") or ""
            params["cityd"] = kwargs.get("destination_city") or params["city"]
        url = f"{self.endpoints[route_type]}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ToolError(f"Amap route planning failed: {exc}") from exc
        if payload.get("status") != "1":
            raise ToolError(f"Amap route planning error: {payload.get('info', 'UNKNOWN')}")
        return self._normalize(payload, route_type)

    def _location(self, point: dict[str, Any]) -> str:
        return f"{float(point['lng'])},{float(point['lat'])}"

    def _normalize(self, payload: dict[str, Any], route_type: str) -> dict[str, Any]:
        route = payload.get("route", {})
        if route_type == "transit":
            transits = route.get("transits", [])
            first = transits[0] if transits else {}
            distance = int(float(first.get("distance") or 0))
            duration = int(float(first.get("duration") or 0))
            segments = first.get("segments", [])
            instruction = "；".join(self._segment_text(item) for item in segments[:5] if item)
        else:
            paths = route.get("paths", [])
            first = paths[0] if paths else {}
            distance = int(float(first.get("distance") or 0))
            duration = int(float(first.get("duration") or 0))
            steps = first.get("steps", [])
            instruction = "；".join(step.get("instruction", "") for step in steps[:5] if step.get("instruction"))
        return {
            "route_type": route_type,
            "source": "amap",
            "distance_m": distance,
            "distance_km": round(distance / 1000, 2),
            "duration_seconds": duration,
            "duration_minutes": round(duration / 60),
            "description": instruction or "高德地图已返回路线。",
        }

    def _segment_text(self, segment: dict[str, Any]) -> str:
        bus = segment.get("bus", {})
        walking = segment.get("walking", {})
        lines = bus.get("buslines", [])
        if lines:
            return lines[0].get("name", "公交线路")
        if walking:
            return "步行换乘"
        return "换乘"

from __future__ import annotations

from functools import lru_cache
from time import sleep
from math import atan2, cos, radians, sin, sqrt
from typing import Any

from backend.app.models.schemas import RouteRequest
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapRoutePlanningTool


class MapService:
    def __init__(self) -> None:
        self.amap_route = AmapRoutePlanningTool()

    def summarize_route(self, request: RouteRequest) -> dict[str, Any]:
        points = request.points
        segments = []
        total_distance = 0.0
        total_duration = 0
        source = "local_fallback"
        polyline: list[list[float]] = []
        for previous, current in zip(points, points[1:]):
            segment = self._segment(previous, current, request)
            segments.append(segment)
            total_distance += float(segment.get("distance_km", 0))
            total_duration += int(segment.get("duration_minutes", 0))
            segment_line = segment.get("polyline") or self._straight_polyline(previous, current)
            polyline.extend(self._join_polyline(polyline, segment_line))
            if segment.get("source") == "amap":
                source = "amap"
        return {
            "route_type": request.route_type,
            "source": source,
            "distance_km": round(total_distance, 1),
            "duration_minutes": total_duration,
            "points_count": len(points),
            "segments": segments,
            "polyline": polyline,
        }

    def _segment(self, origin: dict[str, Any], destination: dict[str, Any], request: RouteRequest) -> dict[str, Any]:
        last_error = ""
        if self.amap_route.enabled:
            for attempt in range(1, 6):
                try:
                    segment = self.amap_route.run(origin=origin, destination=destination, route_type=request.route_type, city=request.city)
                    segment["attempts"] = attempt
                    return segment
                except ToolError as exc:
                    last_error = str(exc)
                    if attempt < 5:
                        sleep(min(0.2 * attempt, 1.0))
        distance = self._haversine(float(origin["lat"]), float(origin["lng"]), float(destination["lat"]), float(destination["lng"]))
        speed = {"walking": 4, "driving": 28, "transit": 18}.get(request.route_type, 4)
        return {
            "route_type": request.route_type,
            "source": "local_fallback",
            "distance_m": round(distance * 1000),
            "distance_km": round(distance, 2),
            "duration_seconds": round(distance / speed * 3600),
            "duration_minutes": round(distance / speed * 60),
            "description": "未配置或未成功调用高德路线API，使用直线距离估算。",
            "polyline": self._straight_polyline(origin, destination),
        }

    def _straight_polyline(self, origin: dict[str, Any], destination: dict[str, Any]) -> list[list[float]]:
        return [[float(origin["lng"]), float(origin["lat"])], [float(destination["lng"]), float(destination["lat"])]]

    def _join_polyline(self, existing: list[list[float]], segment_line: list[list[float]]) -> list[list[float]]:
        if not segment_line:
            return []
        if existing and existing[-1] == segment_line[0]:
            return segment_line[1:]
        return segment_line

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        return radius * 2 * atan2(sqrt(a), sqrt(1 - a))


@lru_cache(maxsize=1)
def get_map_service() -> MapService:
    return MapService()


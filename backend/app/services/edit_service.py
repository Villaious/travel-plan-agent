from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

from backend.app.models.schemas import TripEditRequest
from travel_agent.tools import BudgetTool, MapRouteTool


class TripEditService:
    def __init__(self) -> None:
        self.budget_tool = BudgetTool()
        self.map_tool = MapRouteTool()

    def edit(self, request: TripEditRequest) -> dict[str, Any]:
        plan = deepcopy(request.plan)
        itinerary = plan.get("itinerary", plan)
        days = itinerary.get("days", [])
        if request.day_index >= len(days):
            raise ValueError("day_index超出行程范围")
        stops = days[request.day_index].setdefault("stops", [])
        if request.action == "add":
            if not request.stop:
                raise ValueError("add操作需要stop")
            stops.append({**request.stop, "category": request.stop.get("category", "spot")})
        elif request.action == "delete":
            if request.stop_index is None or request.stop_index >= len(stops):
                raise ValueError("delete操作需要有效stop_index")
            stops.pop(request.stop_index)
        elif request.action == "move":
            if request.stop_index is None or request.target_index is None:
                raise ValueError("move操作需要stop_index和target_index")
            if request.stop_index >= len(stops) or request.target_index >= len(stops):
                raise ValueError("move索引超出范围")
            item = stops.pop(request.stop_index)
            stops.insert(request.target_index, item)
        self._refresh_times(stops)
        people = plan.get("budget", {}).get("people", 1)
        plan["budget"] = self.budget_tool.run(itinerary=itinerary, people=people)
        center = plan.get("map", {}).get("center") or self._center_from_itinerary(itinerary)
        plan["map"] = self.map_tool.run(itinerary=itinerary, center=center)
        plan["itinerary"] = itinerary
        return plan

    def _refresh_times(self, stops: list[dict[str, Any]]) -> None:
        times = ["09:00", "11:00", "12:30", "14:30", "16:00", "18:00", "19:30"]
        for index, stop in enumerate(stops):
            stop["time"] = times[index] if index < len(times) else "20:30"

    def _center_from_itinerary(self, itinerary: dict[str, Any]) -> list[float]:
        points = []
        for day in itinerary.get("days", []):
            for item in [day.get("hotel", {})] + day.get("stops", []):
                if item.get("lat") and item.get("lng"):
                    points.append([float(item["lat"]), float(item["lng"])])
        if not points:
            return [31.2304, 121.4737]
        return [sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)]


@lru_cache(maxsize=1)
def get_trip_edit_service() -> TripEditService:
    return TripEditService()

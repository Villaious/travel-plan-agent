from math import atan2, cos, radians, sin, sqrt
from typing import Any

from travel_agent.tools.base import BaseTool


class MapRouteTool(BaseTool):
    name = "map_route"
    description = "Create ordered map markers and simple route geometry."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        itinerary = kwargs["itinerary"]
        center = kwargs["center"]
        markers = []
        routes = []
        for day in itinerary["days"]:
            day_markers = []
            hotel = day["hotel"]
            day_markers.append(self._marker(hotel, day["day"], "hotel", "入住酒店"))
            for order, stop in enumerate(day["stops"], start=1):
                day_markers.append(self._marker(stop, day["day"], stop["category"], f"{order}. {stop['time']}"))
            markers.extend(day_markers)
            routes.append(
                {
                    "day": day["day"],
                    "points": [[item["lat"], item["lng"]] for item in day_markers],
                    "distance_km": round(self._distance(day_markers), 1),
                }
            )
        return {"center": center, "markers": markers, "routes": routes}

    def _marker(self, item: dict[str, Any], day: int, category: str, label: str) -> dict[str, Any]:
        return {
            "name": item["name"],
            "lat": item["lat"],
            "lng": item["lng"],
            "day": day,
            "category": category,
            "label": label,
        }

    def _distance(self, markers: list[dict[str, Any]]) -> float:
        total = 0.0
        for previous, current in zip(markers, markers[1:]):
            total += self._haversine(previous["lat"], previous["lng"], current["lat"], current["lng"])
        return total

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        return radius * 2 * atan2(sqrt(a), sqrt(1 - a))

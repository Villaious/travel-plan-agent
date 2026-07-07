from datetime import datetime, timedelta
from typing import Any

from travel_agent.tools.base import BaseTool


class ItineraryTool(BaseTool):
    name = "itinerary"
    description = "Build a day-by-day itinerary from destination data and preferences."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        data = kwargs["data"]
        destination = kwargs["destination"]
        days = max(1, int(kwargs.get("days", 2)))
        start_date = datetime.strptime(kwargs.get("start_date"), "%Y-%m-%d").date()
        preferences = kwargs.get("preferences") or []
        hotel = self._select_hotel(data["hotels"], kwargs.get("budget_level", "舒适"))
        ranked_spots = self._rank_spots(data["spots"], preferences)
        restaurants = data["restaurants"]

        plan_days = []
        cursor = 0
        for day_index in range(days):
            selected = ranked_spots[cursor : cursor + 3]
            if not selected:
                selected = ranked_spots[:3]
            cursor += 3

            lunch = restaurants[day_index % len(restaurants)]
            dinner = restaurants[(day_index + 1) % len(restaurants)]
            stops = self._build_day_stops(selected, lunch, dinner)
            plan_days.append(
                {
                    "day": day_index + 1,
                    "date": str(start_date + timedelta(days=day_index)),
                    "hotel": hotel,
                    "stops": stops,
                }
            )

        return {
            "destination": destination,
            "days": plan_days,
            "preferences": preferences,
            "summary": f"{destination}{days}天旅行计划：围绕{self._preference_text(preferences)}安排景点、餐饮与住宿。",
        }

    def _rank_spots(self, spots: list[dict[str, Any]], preferences: list[str]) -> list[dict[str, Any]]:
        def score(spot: dict[str, Any]) -> int:
            tags = set(spot.get("tags", []))
            return sum(3 for item in preferences if item in tags) + (1 if spot["ticket"] == 0 else 0)

        return sorted(spots, key=score, reverse=True)

    def _select_hotel(self, hotels: list[dict[str, Any]], budget_level: str) -> dict[str, Any]:
        for hotel in hotels:
            if hotel["level"] == budget_level:
                return hotel
        return hotels[0]

    def _build_day_stops(
        self,
        spots: list[dict[str, Any]],
        lunch: dict[str, Any],
        dinner: dict[str, Any],
    ) -> list[dict[str, Any]]:
        times = ["09:00", "11:00", "12:30", "14:30", "18:00"]
        stops: list[dict[str, Any]] = []
        for index, spot in enumerate(spots[:2]):
            stops.append({**spot, "category": "spot", "time": times[index]})
        stops.append({**lunch, "category": "restaurant", "time": times[2], "ticket": 0, "duration": 60, "reason": "按当天动线就近安排午餐。"})
        if len(spots) > 2:
            stops.append({**spots[2], "category": "spot", "time": times[3]})
        stops.append({**dinner, "category": "restaurant", "time": times[4], "ticket": 0, "duration": 90, "reason": "晚餐后方便返回酒店或继续夜游。"})
        return stops

    def _preference_text(self, preferences: list[str]) -> str:
        return "、".join(preferences) if preferences else "经典路线"

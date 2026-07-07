from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapPlaceSearchTool, DestinationDataTool


class RestaurantAgent(Agent):
    """Recommends restaurants by cuisine preferences and destination."""

    def __init__(self) -> None:
        super().__init__(
            name="餐饮推荐专家",
            system_prompt="根据目的地、偏好和菜系推荐餐厅，并估算餐饮预算。",
        )
        self.add_tool(DestinationDataTool())
        self.add_tool(AmapPlaceSearchTool())

    def run(self, destination: str, preferences: list[str] | None = None, budget_level: str = "舒适", limit: int = 8) -> dict[str, Any]:
        preferences = preferences or []
        self.remember_user_input(f"搜索{destination}餐厅，偏好={preferences}，预算={budget_level}")
        restaurants = self._search_amap(destination, preferences, budget_level, limit) or self._search_local(destination, preferences, limit)
        source = "amap" if restaurants and restaurants[0].get("source") == "amap" else "local"
        result = {
            "agent": self.name,
            "destination": destination,
            "restaurants": restaurants,
            "source": source,
            "message": f"已为{destination}匹配{len(restaurants)}个餐饮候选，预算档位为{budget_level}。",
        }
        self.remember_answer(result["message"])
        return result

    def _search_amap(self, destination: str, preferences: list[str], budget_level: str, limit: int) -> list[dict[str, Any]]:
        tool = self.tools.get("amap_place_search")
        if not getattr(tool, "enabled", False):
            return []
        keyword = self._keyword(preferences)
        try:
            restaurants = tool.run(
                keywords=keyword,
                city=destination,
                citylimit="true",
                offset=limit,
                default_category="restaurant",
            )
        except ToolError:
            return []
        price = self._price(budget_level)
        return [
            {**item, "category": "restaurant", "price": price, "ticket": 0, "duration": 70, "reason": f"根据{keyword}偏好从高德POI筛选。"}
            for item in restaurants
            if item.get("lat") and item.get("lng")
        ][:limit]

    def _search_local(self, destination: str, preferences: list[str], limit: int) -> list[dict[str, Any]]:
        data = self.tools.get("destination_data").run(destination=destination)
        restaurants = data.get("restaurants", [])
        return sorted(restaurants, key=lambda item: self._score(item, preferences), reverse=True)[:limit]

    def _keyword(self, preferences: list[str]) -> str:
        if "美食" in preferences:
            return "特色餐厅"
        if "亲子" in preferences:
            return "亲子餐厅"
        if "文化" in preferences:
            return "老字号餐厅"
        return "餐厅"

    def _price(self, budget_level: str) -> int:
        return {"经济": 45, "舒适": 90, "品质": 180}.get(budget_level, 90)

    def _score(self, restaurant: dict[str, Any], preferences: list[str]) -> int:
        tags = set(restaurant.get("tags", []))
        return sum(2 for item in preferences if item in tags)

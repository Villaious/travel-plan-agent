from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapPlaceSearchTool, DestinationDataTool


class HotelAgent(Agent):
    """Recommends hotels that match the user's budget level."""

    def __init__(self) -> None:
        super().__init__(
            name="酒店推荐专家",
            system_prompt="根据目的地和住宿档位推荐酒店，输出必须服务于旅行计划。",
        )
        self.add_tool(DestinationDataTool())
        self.add_tool(AmapPlaceSearchTool())

    def run(self, destination: str, budget_level: str = "舒适") -> dict[str, Any]:
        self.remember_user_input(f"搜索{destination}的{budget_level}酒店")
        hotels = self._search_amap(destination, budget_level) or self._search_local(destination, budget_level)
        source = "amap" if hotels and hotels[0].get("source") == "amap" else "local"
        result = {
            "agent": self.name,
            "destination": destination,
            "budget_level": budget_level,
            "hotels": hotels,
            "source": source,
            "message": f"已优先推荐{destination}{budget_level}档酒店，共{len(hotels)}个候选。",
        }
        self.remember_answer(result["message"])
        return result

    def _search_amap(self, destination: str, budget_level: str) -> list[dict[str, Any]]:
        tool = self.tools.get("amap_place_search")
        if not getattr(tool, "enabled", False):
            return []
        try:
            hotels = tool.run(
                keywords=f"{budget_level}酒店",
                city=destination,
                citylimit="true",
                offset=10,
                default_category="hotel",
            )
        except ToolError:
            return []
        normalized = []
        for hotel in hotels:
            if not hotel["lat"] or not hotel["lng"]:
                continue
            normalized.append({**hotel, "level": budget_level, "price": self._estimate_price(budget_level)})
        return normalized

    def _search_local(self, destination: str, budget_level: str) -> list[dict[str, Any]]:
        data = self.tools.get("destination_data").run(destination=destination)
        return sorted(data["hotels"], key=lambda item: 0 if item["level"] == budget_level else 1)

    def _estimate_price(self, budget_level: str) -> int:
        return {"经济": 320, "舒适": 520, "品质": 900}.get(budget_level, 520)

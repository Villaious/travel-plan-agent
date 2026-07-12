from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapPlaceSearchTool, DestinationDataTool, QdrantAttractionRagTool


class AttractionSearchAgent(Agent):
    """Searches and ranks attractions for a destination."""

    def __init__(self) -> None:
        super().__init__(
            name="景点搜索专家",
            system_prompt="根据目的地和用户偏好搜索景点，不能编造无关信息。",
        )
        self.add_tool(DestinationDataTool())
        self.add_tool(AmapPlaceSearchTool())

    def run(self, destination: str, preferences: list[str] | None = None, limit: int = 8) -> dict[str, Any]:
        preferences = preferences or []
        self.remember_user_input(f"搜索{destination}景点，偏好={preferences}")
        spots = self._search_amap(destination, preferences, limit) or self._search_local(destination, preferences, limit)
        source = "amap" if spots and spots[0].get("source") == "amap" else "local"
        result = {
            "agent": self.name,
            "destination": destination,
            "attractions": spots,
            "source": source,
            "message": f"已根据{destination}和{self._preference_text(preferences)}筛选出{len(spots)}个候选景点。",
        }
        self.remember_answer(result["message"])
        return result


    def _search_rag(self, destination: str, preferences: list[str], limit: int) -> list[dict[str, Any]]:
        tool = self.tools.get("qdrant_attraction_rag")
        if not getattr(tool, "enabled", False):
            return []
        return tool.run(destination=destination, preferences=preferences, limit=limit)
    def _search_amap(self, destination: str, preferences: list[str], limit: int) -> list[dict[str, Any]]:
        tool = self.tools.get("amap_place_search")
        if not getattr(tool, "enabled", False):
            return []
        keywords = self._keyword(preferences)
        try:
            spots = tool.run(
                keywords=keywords,
                city=destination,
                citylimit="true",
                offset=limit,
                default_category="spot",
            )
        except ToolError:
            return []
        return [item for item in spots if item["lat"] and item["lng"]][:limit]

    def _search_local(self, destination: str, preferences: list[str], limit: int) -> list[dict[str, Any]]:
        data = self.tools.get("destination_data").run(destination=destination)
        return sorted(data["spots"], key=lambda item: self._score(item, preferences), reverse=True)[:limit]

    def _keyword(self, preferences: list[str]) -> str:
        if "美食" in preferences:
            return "景点"
        if "文化" in preferences:
            return "博物馆"
        if "自然" in preferences:
            return "公园"
        return "景点"

    def _score(self, spot: dict[str, Any], preferences: list[str]) -> int:
        tags = set(spot.get("tags", []))
        return sum(3 for item in preferences if item in tags) + (1 if spot.get("ticket", 0) == 0 else 0)

    def _preference_text(self, preferences: list[str]) -> str:
        return "、".join(preferences) if preferences else "经典旅行偏好"


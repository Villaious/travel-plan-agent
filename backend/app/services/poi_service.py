from __future__ import annotations

from functools import lru_cache

from backend.app.models.schemas import POISearchRequest
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapPlaceSearchTool, DestinationDataTool


class POIService:
    def __init__(self) -> None:
        self.amap = AmapPlaceSearchTool()
        self.local = DestinationDataTool()

    def search(self, request: POISearchRequest) -> list[dict]:
        if self.amap.enabled:
            try:
                return self.amap.run(
                    keywords=request.keywords,
                    city=request.city,
                    citylimit=str(request.citylimit).lower(),
                    offset=request.offset,
                    default_category="spot",
                )
            except ToolError:
                pass
        data = self.local.run(destination=request.city)
        pools = data.get("spots", []) + data.get("restaurants", []) + data.get("hotels", [])
        keyword = request.keywords.lower()
        return [item for item in pools if keyword in item.get("name", "").lower() or request.keywords in str(item.get("tags", []))][: request.offset]


@lru_cache(maxsize=1)
def get_poi_service() -> POIService:
    return POIService()

from typing import Any

from travel_agent.tools.base import BaseTool


class ExportPayloadTool(BaseTool):
    name = "export_payload"
    description = "Prepare serializable data for PDF or image export."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "title": f"{kwargs['itinerary']['destination']}旅行计划",
            "itinerary": kwargs["itinerary"],
            "budget": kwargs["budget"],
            "map": kwargs["map"],
        }

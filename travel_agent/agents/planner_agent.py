from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.core.config import get_bool_env
from travel_agent.core.exceptions import AgentError
from travel_agent.core.llm import OpenAICompatibleLLM
from travel_agent.tools import BudgetTool, DestinationDataTool, ExportPayloadTool, ItineraryTool, MapRouteTool


class PlannerAgent(Agent):
    """Integrates specialist outputs into the final trip plan."""

    def __init__(self) -> None:
        super().__init__(
            name="行程规划专家",
            system_prompt="整合景点、天气、酒店与用户需求，生成完整旅行计划。",
        )
        for tool in [DestinationDataTool(), ItineraryTool(), BudgetTool(), MapRouteTool(), ExportPayloadTool()]:
            self.add_tool(tool)
        self.llm = OpenAICompatibleLLM()
        self.use_llm = get_bool_env("TRAVEL_AGENT_USE_LLM", True)

    def run(
        self,
        request: dict[str, Any],
        attractions: dict[str, Any],
        weather: dict[str, Any],
        hotels: dict[str, Any],
        restaurants: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        destination = request["destination"]
        self.remember_user_input(self._build_planner_query(request, attractions, weather, hotels))
        base_data = self.tools.get("destination_data").run(destination=destination)
        selected_hotels = hotels["hotels"] or base_data["hotels"]
        selected_restaurants = (restaurants or {}).get("restaurants") or base_data["restaurants"]
        planner_data = {
            **base_data,
            "spots": attractions["attractions"] or base_data["spots"],
            "hotels": selected_hotels,
            "restaurants": selected_restaurants,
        }
        itinerary = self.tools.get("itinerary").run(
            data=planner_data,
            destination=destination,
            start_date=request["start_date"],
            days=request["days"],
            preferences=request.get("preferences", []),
            budget_level=request.get("budget_level", "舒适"),
        )
        itinerary["transportation"] = request.get("transportation", "公共交通")
        itinerary["weather_info"] = weather["weather"]
        itinerary["overall_suggestions"] = self._build_suggestions(weather["weather"])
        budget = self.tools.get("budget").run(itinerary=itinerary, people=request.get("people", 1), transport_per_day=self._transport_cost_per_day(request.get("transportation", "公共交通")))
        map_payload = self.tools.get("map_route").run(itinerary=itinerary, center=planner_data["center"])
        self._enhance_with_llm(itinerary, budget, attractions, hotels)
        export_payload = self.tools.get("export_payload").run(itinerary=itinerary, budget=budget, map=map_payload)
        result = {**export_payload, "summary": itinerary["summary"], "transportation": request.get("transportation", "公共交通")}
        self.remember_answer(result["summary"])
        return result

    def _build_planner_query(
        self,
        request: dict[str, Any],
        attractions: dict[str, Any],
        weather: dict[str, Any],
        hotels: dict[str, Any],
    ) -> str:
        return (
            f"请根据以下信息生成{request['destination']}的{request['days']}日旅行计划。"
            f"用户偏好={request.get('preferences', [])}; "
            f"景点数={len(attractions.get('attractions', []))}; "
            f"天气天数={len(weather.get('weather', []))}; "
            f"酒店数={len(hotels.get('hotels', []))}。"
        )


    def _transport_cost_per_day(self, transportation: str) -> int:
        if any(keyword in transportation for keyword in ["驾车", "自驾", "开车", "打车", "出租"]):
            return 120
        if any(keyword in transportation for keyword in ["步行", "徒步"]):
            return 20
        return 50
    def _enhance_with_llm(
        self,
        itinerary: dict[str, Any],
        budget: dict[str, Any],
        attractions: dict[str, Any],
        hotels: dict[str, Any],
    ) -> None:
        if not self.use_llm or not self.llm.enabled:
            itinerary["llm_used"] = False
            return
        prompt = (
            "你是旅行规划专家。请基于结构化行程生成一段简洁中文总结和实用建议，"
            "不要改变JSON结构，不要编造不在输入中的城市。\n"
            f"目的地：{itinerary['destination']}\n"
            f"偏好：{itinerary.get('preferences', [])}\n"
            f"景点来源：{attractions.get('source', 'unknown')}，酒店来源：{hotels.get('source', 'unknown')}\n"
            f"天气：{itinerary.get('weather_info', [])}\n"
            f"预算：{budget}\n"
            "请输出两行：第一行以 SUMMARY: 开头，第二行以 SUGGESTIONS: 开头。"
        )
        try:
            content = self.llm.chat(
                [
                    {"role": "system", "content": "你只处理旅行规划，不讨论无关话题。"},
                    {"role": "user", "content": prompt},
                ]
            )
        except AgentError as exc:
            itinerary["llm_used"] = False
            itinerary["llm_error"] = str(exc)
            return
        summary, suggestions = self._parse_llm_content(content)
        if summary:
            itinerary["summary"] = summary
        if suggestions:
            itinerary["overall_suggestions"] = suggestions
        itinerary["llm_used"] = True

    def _parse_llm_content(self, content: str) -> tuple[str, str]:
        summary = ""
        suggestions = ""
        for line in content.splitlines():
            line = line.strip()
            if line.upper().startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()
            elif line.upper().startswith("SUGGESTIONS:"):
                suggestions = line.split(":", 1)[1].strip()
        return summary, suggestions

    def _build_suggestions(self, weather: list[dict[str, Any]]) -> str:
        rainy_days = [item["date"] for item in weather if "雨" in item["weather"]]
        if rainy_days:
            return f"{ '、'.join(rainy_days) }可能有雨，建议保留室内景点和雨具。"
        return "天气整体适合出行，建议把户外景点安排在上午或傍晚。"



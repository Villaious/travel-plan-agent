from __future__ import annotations

from typing import Any

from travel_agent.agents.attraction_search_agent import AttractionSearchAgent
from travel_agent.agents.hotel_agent import HotelAgent
from travel_agent.agents.planner_agent import PlannerAgent
from travel_agent.agents.restaurant_agent import RestaurantAgent
from travel_agent.agents.scenic_search_agent import ScenicSearchAgent
from travel_agent.agents.topic_guard_agent import TopicGuardAgent
from travel_agent.agents.weather_query_agent import WeatherQueryAgent
from travel_agent.core.agent import Agent
from travel_agent.core.exceptions import AgentError
from travel_agent.core.memory import TravelMemory


class TravelPlannerAgent(Agent):
    """Coordinator that runs the chapter-13 style multi-agent workflow."""

    def __init__(self) -> None:
        super().__init__(
            name="多Agent旅游规划总控",
            system_prompt="分解旅行规划任务，协调景点、景区资料、天气、酒店、餐饮、行程规划与主题检查Agent。",
        )
        self.attraction_agent = AttractionSearchAgent()
        self.scenic_search_agent = ScenicSearchAgent()
        self.weather_agent = WeatherQueryAgent()
        self.hotel_agent = HotelAgent()
        self.restaurant_agent = RestaurantAgent()
        self.planner_agent = PlannerAgent()
        self.topic_guard_agent = TopicGuardAgent()
        self.memory = TravelMemory()

    def run(
        self,
        destination: str,
        start_date: str,
        days: int,
        preferences: list[str] | None = None,
        budget_level: str = "舒适",
        people: int = 1,
        transportation: str = "公共交通",
    ) -> dict[str, Any]:
        request = {
            "destination": destination,
            "start_date": start_date,
            "days": max(1, int(days)),
            "preferences": preferences or [],
            "budget_level": budget_level,
            "people": max(1, int(people)),
            "transportation": transportation,
        }
        memory_before = self.memory.suggest()
        self.remember_user_input(
            f"目的地={destination}; 日期={start_date}; 天数={days}; 偏好={preferences}; 预算={budget_level}; 交通={transportation}"
        )

        attraction_input = f"搜索{destination}景点，偏好={request['preferences']}"
        attraction_response = self.attraction_agent.run(destination, request["preferences"])
        attraction_check = self._guard(request, attraction_response)

        scenic_input = f"搜索并整合{destination}景区资料，补充优点和适合人群"
        scenic_response = self.scenic_search_agent.run(destination, attraction_response.get("attractions", []), request["preferences"])
        attraction_response = self._merge_scenic_insights(attraction_response, scenic_response)
        scenic_check = self._guard(request, scenic_response)

        weather_input = f"查询{destination}从{start_date}开始{request['days']}天的天气"
        weather_response = self.weather_agent.run(destination, start_date, request["days"])
        weather_check = self._guard(request, weather_response)

        hotel_input = f"搜索{destination}的{budget_level}档酒店"
        hotel_response = self.hotel_agent.run(destination, budget_level)
        hotel_check = self._guard(request, hotel_response)

        restaurant_input = f"搜索{destination}餐厅，偏好={request['preferences']}，预算={budget_level}"
        restaurant_response = self.restaurant_agent.run(destination, request["preferences"], budget_level)
        restaurant_check = self._guard(request, restaurant_response)

        planner_input = self.planner_agent._build_planner_query(request, attraction_response, weather_response, hotel_response)
        plan = self.planner_agent.run(request, attraction_response, weather_response, hotel_response, restaurant_response)
        planner_check = self._guard(request, plan)

        memory_after = self.memory.remember(destination, request["preferences"], budget_level)
        plan["memory_suggestions"] = memory_before
        plan["memory_snapshot"] = memory_after
        plan["scenic_insights"] = scenic_response.get("scenic_insights", [])

        topic_checks = [attraction_check, scenic_check, weather_check, hotel_check, restaurant_check, planner_check]
        plan["topic_checks"] = topic_checks
        plan["collaboration_trace"] = [
            {"step": 1, "agent": self.attraction_agent.name, "input": attraction_input, "output": attraction_response["message"], "status": "ok"},
            {"step": 2, "agent": self.scenic_search_agent.name, "input": scenic_input, "output": scenic_response["message"], "status": "ok"},
            {"step": 3, "agent": self.weather_agent.name, "input": weather_input, "output": weather_response["message"], "status": "ok"},
            {"step": 4, "agent": self.hotel_agent.name, "input": hotel_input, "output": hotel_response["message"], "status": "ok"},
            {"step": 5, "agent": self.restaurant_agent.name, "input": restaurant_input, "output": restaurant_response["message"], "status": "ok"},
            {"step": 6, "agent": self.planner_agent.name, "input": planner_input, "output": plan["summary"], "status": "ok"},
            {"step": 7, "agent": "记忆模块", "input": "保存目的地、偏好和预算档位", "output": f"当前常用偏好：{', '.join(self.memory.suggest().get('favorite_preferences', [])) or '暂无'}", "status": "ok"},
            {"step": 8, "agent": self.topic_guard_agent.name, "input": "检查所有Agent输出是否围绕原始旅行规划主题", "output": "所有Agent输出均通过主题一致性检查。", "status": "ok"},
        ]
        self.remember_answer(plan["summary"])
        return plan

    def _merge_scenic_insights(self, attraction_response: dict[str, Any], scenic_response: dict[str, Any]) -> dict[str, Any]:
        insights = {item.get("name"): item for item in scenic_response.get("scenic_insights", [])}
        for attraction in attraction_response.get("attractions", []):
            insight = insights.get(attraction.get("name"))
            if not insight:
                continue
            attraction["advantages"] = insight.get("advantages", [])
            attraction["suitable_for"] = insight.get("suitable_for", [])
            attraction["scenic_intro"] = insight.get("content", "")
            attraction["reason"] = f"{attraction.get('reason', '')} {insight.get('content', '')}".strip()
        attraction_response["scenic_insights"] = scenic_response.get("scenic_insights", [])
        return attraction_response

    def _guard(self, request: dict[str, Any], output: Any) -> dict[str, Any]:
        agent_name = output.get("agent", "行程规划专家") if isinstance(output, dict) else "未知Agent"
        report = self.topic_guard_agent.run(agent_name=agent_name, original_topic=request, agent_output=output)
        if not report["on_topic"]:
            raise AgentError(f"{agent_name} 输出未通过主题检查: {report['reason']}")
        return report

from __future__ import annotations

from functools import lru_cache

from backend.app.models.schemas import RouteRecommendationRequest
from travel_agent.agents import RoutePlanningAgent, TopicGuardAgent
from travel_agent.core.exceptions import AgentError


class RouteRecommendationService:
    def __init__(self) -> None:
        self.agent = RoutePlanningAgent()
        self.guard = TopicGuardAgent()

    def recommend(self, request: RouteRecommendationRequest) -> dict:
        result = self.agent.run(
            city=request.city,
            origin=request.origin.model_dump(),
            destination=request.destination.model_dump(),
            selected_modes=list(request.selected_modes),
            priority=request.priority,
            people=request.people,
        )
        check = self.guard.run(
            agent_name=self.agent.name,
            original_topic={"destination": request.city, "task": "比较两个旅行地点之间的交通方式"},
            agent_output=result,
        )
        if not check["on_topic"]:
            raise AgentError(f"路线规划专家输出未通过主题检查: {check['reason']}")
        result["topic_check"] = check
        return result


@lru_cache(maxsize=1)
def get_route_recommendation_service() -> RouteRecommendationService:
    return RouteRecommendationService()
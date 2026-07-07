from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.app.models.schemas import TripPlanRequest
from travel_agent import TravelPlannerAgent


@lru_cache(maxsize=1)
def get_trip_planner_agent() -> TravelPlannerAgent:
    return TravelPlannerAgent()


class TripPlannerService:
    def __init__(self) -> None:
        self.agent = get_trip_planner_agent()

    def plan(self, request: TripPlanRequest) -> dict[str, Any]:
        return self.agent.run(
            destination=request.destination,
            start_date=request.start_date.isoformat(),
            days=request.days,
            preferences=request.preferences,
            budget_level=request.budget_level,
            people=request.people,
        )


@lru_cache(maxsize=1)
def get_trip_planner_service() -> TripPlannerService:
    return TripPlannerService()

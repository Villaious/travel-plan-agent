from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.tools.builtin.weather import WeatherTool


class WeatherQueryAgent(Agent):
    """Queries weather information for the requested destination and dates."""

    def __init__(self) -> None:
        super().__init__(
            name="天气查询专家",
            system_prompt="只查询旅行目的地天气，并给出与行程相关的建议。",
        )
        self.add_tool(WeatherTool())

    def run(self, destination: str, start_date: str, days: int) -> dict[str, Any]:
        self.remember_user_input(f"查询{destination}从{start_date}开始{days}天的天气")
        forecast = self.tools.get("weather").run(destination=destination, start_date=start_date, days=days)
        result = {
            "agent": self.name,
            "destination": destination,
            "weather": forecast,
            "message": f"已生成{destination}{days}天旅行天气参考。",
        }
        self.remember_answer(result["message"])
        return result

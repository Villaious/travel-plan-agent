from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from time import sleep
from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.core.exceptions import ToolError
from travel_agent.tools import AmapDistanceTool, AmapRoutePlanningTool


MODE_LABELS = {
    "transit": "公共交通",
    "driving": "驾车",
    "walking": "步行",
    "cycling": "共享单车",
}


class RoutePlanningAgent(Agent):
    """Compares route modes between two places and recommends the best option."""

    def __init__(self) -> None:
        super().__init__(
            name="路线规划专家",
            system_prompt="比较两点之间多种交通方式的时间、费用和适用性，推荐最佳出行方案。",
        )
        self.add_tool(AmapRoutePlanningTool())
        self.add_tool(AmapDistanceTool())

    def run(
        self,
        city: str,
        origin: dict[str, Any],
        destination: dict[str, Any],
        selected_modes: list[str],
        priority: str = "balanced",
        people: int = 1,
    ) -> dict[str, Any]:
        modes = list(dict.fromkeys(mode for mode in selected_modes if mode in MODE_LABELS))
        if not modes:
            raise ValueError("至少选择一种交通方式")
        if origin.get("lat") == destination.get("lat") and origin.get("lng") == destination.get("lng"):
            raise ValueError("起点和终点不能相同")

        self.remember_user_input(
            f"比较{origin.get('name', '起点')}到{destination.get('name', '终点')}的交通方式={modes}，偏好={priority}"
        )
        baseline_distance = self._baseline_distance(origin, destination)
        options = [self._route_option(city, origin, destination, mode, max(1, people), baseline_distance) for mode in modes]
        self._score_options(options, priority)
        options.sort(key=lambda item: item["score"], reverse=True)
        options[0]["recommended"] = True
        result = {
            "agent": self.name,
            "city": city,
            "origin": origin,
            "destination": destination,
            "priority": priority,
            "recommended_mode": options[0]["mode"],
            "recommended_label": options[0]["label"],
            "recommendation": self._recommendation(options[0], priority),
            "options": options,
            "message": f"已比较{len(options)}种交通方式，推荐{options[0]['label']}。",
        }
        self.remember_answer(result["message"])
        return result

    def _baseline_distance(self, origin: dict[str, Any], destination: dict[str, Any]) -> float:
        tool = self.tools.get("amap_distance")
        if tool.enabled:
            try:
                results = tool.run(origins=[origin], destination=destination, distance_type=0)
                if results and results[0].get("distance_km"):
                    return float(results[0]["distance_km"])
            except ToolError:
                pass
        return self._distance(origin, destination)
    def _route_option(
        self,
        city: str,
        origin: dict[str, Any],
        destination: dict[str, Any],
        mode: str,
        people: int,
        baseline_distance: float,
    ) -> dict[str, Any]:
        route = self._query_route(city, origin, destination, mode, baseline_distance)
        distance = float(route.get("distance_km") or self._distance(origin, destination))
        duration = int(route.get("duration_minutes") or self._estimated_minutes(distance, mode))
        cost = self._estimated_cost(distance, duration, mode, people)
        pros, cons = self._pros_cons(mode, distance, duration)
        return {
            "mode": mode,
            "label": MODE_LABELS[mode],
            "distance_km": round(distance, 2),
            "duration_minutes": max(1, duration),
            "estimated_cost": cost,
            "cost_per_person": round(cost / people, 2),
            "comfort_score": self._comfort(mode, distance),
            "source": route.get("source", "local_fallback"),
            "polyline": route.get("polyline", []),
            "description": route.get("description", "使用距离和平均速度估算。"),
            "pros": pros,
            "cons": cons,
            "score": 0.0,
            "recommended": False,
        }

    def _query_route(self, city: str, origin: dict[str, Any], destination: dict[str, Any], mode: str, baseline_distance: float) -> dict[str, Any]:
        tool = self.tools.get("amap_route_planning")
        if tool.enabled:
            for attempt in range(1, 6):
                try:
                    result = tool.run(origin=origin, destination=destination, route_type=mode, city=city)
                    result["attempts"] = attempt
                    return result
                except ToolError:
                    if attempt < 5:
                        sleep(min(0.2 * attempt, 1.0))
        distance = baseline_distance
        return {
            "route_type": mode,
            "source": "local_fallback",
            "distance_km": round(distance, 2),
            "duration_minutes": self._estimated_minutes(distance, mode),
            "description": "高德路线不可用，使用距离、平均速度和常见计费规则估算。",
            "polyline": [
                [float(origin["lng"]), float(origin["lat"])],
                [float(destination["lng"]), float(destination["lat"])],
            ],
        }

    def _score_options(self, options: list[dict[str, Any]], priority: str) -> None:
        durations = [item["duration_minutes"] for item in options]
        costs = [item["estimated_cost"] for item in options]
        for item in options:
            time_score = self._inverse_score(item["duration_minutes"], min(durations), max(durations))
            cost_score = self._inverse_score(item["estimated_cost"], min(costs), max(costs))
            comfort_score = float(item["comfort_score"])
            if priority == "time":
                score = time_score * 0.75 + cost_score * 0.10 + comfort_score * 0.15
            elif priority == "cost":
                score = cost_score * 0.75 + time_score * 0.15 + comfort_score * 0.10
            else:
                score = time_score * 0.42 + cost_score * 0.38 + comfort_score * 0.20
            item["score"] = round(score, 1)

    def _inverse_score(self, value: float, minimum: float, maximum: float) -> float:
        if maximum == minimum:
            return 100.0
        return 100.0 - (value - minimum) / (maximum - minimum) * 100.0

    def _estimated_minutes(self, distance: float, mode: str) -> int:
        speed = {"walking": 4.5, "cycling": 13.0, "transit": 20.0, "driving": 30.0}[mode]
        fixed = {"walking": 0, "cycling": 4, "transit": 10, "driving": 6}[mode]
        return max(1, round(distance / speed * 60 + fixed))

    def _estimated_cost(self, distance: float, duration: int, mode: str, people: int) -> float:
        if mode == "walking":
            return 0.0
        if mode == "cycling":
            half_hours = max(1, (duration + 29) // 30)
            return float(half_hours * 1.5 * people)
        if mode == "transit":
            per_person = min(12.0, max(2.0, 2.0 + distance * 0.35))
            return round(per_person * people, 2)
        return round(15.0 + distance * 1.25, 2)

    def _comfort(self, mode: str, distance: float) -> int:
        if mode == "driving":
            return 88
        if mode == "transit":
            return 76
        if mode == "cycling":
            return 82 if distance <= 5 else 62 if distance <= 10 else 35
        return 78 if distance <= 2 else 55 if distance <= 5 else 25

    def _pros_cons(self, mode: str, distance: float, duration: int) -> tuple[list[str], list[str]]:
        if mode == "walking":
            return ["零费用", "无需等待，适合沿途游览"], (["距离较远，体力消耗较大"] if distance > 3 else [])
        if mode == "cycling":
            cons = ["受天气、停车点和车辆供应影响"]
            if distance > 8:
                cons.append("距离较长，不建议连续骑行")
            return ["费用较低", "短途灵活，通常比步行更快"], cons
        if mode == "transit":
            return ["费用稳定", "适合中长距离和多人分别出行"], ["可能需要候车和换乘"]
        return ["时间可控", "携带行李更方便"], ["费用较高，可能受拥堵和停车影响"]

    def _recommendation(self, option: dict[str, Any], priority: str) -> str:
        priority_label = {"balanced": "综合性价比", "time": "最短时间", "cost": "最低费用"}.get(priority, "综合性价比")
        return (
            f"按{priority_label}评估，推荐{option['label']}：约{option['duration_minutes']}分钟，"
            f"预计费用¥{option['estimated_cost']:.2f}，距离{option['distance_km']:.2f}公里。"
        )

    def _distance(self, origin: dict[str, Any], destination: dict[str, Any]) -> float:
        lat1, lng1 = float(origin["lat"]), float(origin["lng"])
        lat2, lng2 = float(destination["lat"]), float(destination["lng"])
        radius = 6371.0
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        value = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        return radius * 2 * atan2(sqrt(value), sqrt(1 - value))
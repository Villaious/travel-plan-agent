from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent


class TopicGuardAgent(Agent):
    """Checks whether each specialist agent stays within the travel-planning topic."""

    TRAVEL_KEYWORDS = {
        "旅行", "旅游", "行程", "景点", "酒店", "天气", "餐饮", "预算", "路线", "地图",
        "门票", "交通", "目的地", "游览", "住宿", "城市", "偏好",
    }
    OFF_TOPIC_KEYWORDS = {
        "股票", "基金", "编程作业", "游戏攻略", "医疗诊断", "法律诉讼", "电影剧情", "小说创作",
    }

    def __init__(self) -> None:
        super().__init__(
            name="主题检查Agent",
            system_prompt="检查其他Agent的输出是否仍围绕用户最初的旅行规划需求。",
        )

    def run(self, agent_name: str, original_topic: dict[str, Any], agent_output: Any) -> dict[str, Any]:
        text = self._flatten(agent_output)
        destination = str(original_topic.get("destination", ""))
        preferences = [str(item) for item in original_topic.get("preferences", [])]
        has_destination = bool(destination and destination in text)
        has_preference = any(item and item in text for item in preferences)
        travel_hits = sum(1 for keyword in self.TRAVEL_KEYWORDS if keyword in text)
        off_topic_hits = [keyword for keyword in self.OFF_TOPIC_KEYWORDS if keyword in text]
        on_topic = not off_topic_hits and (has_destination or has_preference or travel_hits >= 2)
        report = {
            "agent": agent_name,
            "on_topic": on_topic,
            "reason": "输出围绕旅行规划需求。" if on_topic else "输出疑似脱离原始旅行规划话题。",
            "travel_keyword_hits": travel_hits,
            "off_topic_keywords": off_topic_hits,
        }
        self.history.append(self._make_message(report))
        return report

    def _flatten(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(f"{key} {self._flatten(item)}" for key, item in value.items())
        if isinstance(value, list):
            return " ".join(self._flatten(item) for item in value)
        return str(value)

    def _make_message(self, report: dict[str, Any]):
        from travel_agent.core.message import Message

        return Message.assistant(f"{report['agent']}: {report['reason']}")

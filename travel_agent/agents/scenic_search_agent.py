from __future__ import annotations

from typing import Any

from travel_agent.core.agent import Agent
from travel_agent.tools import QdrantAttractionRagTool, SerpApiSearchTool


class ScenicSearchAgent(Agent):
    """Searches scenic information, summarizes advantages and writes knowledge into RAG."""

    def __init__(self) -> None:
        super().__init__(
            name="景区搜索专家",
            system_prompt="使用搜索结果整合景区介绍，说明优点和适合人群，并沉淀到RAG知识库。",
        )
        self.add_tool(SerpApiSearchTool())
        self.add_tool(QdrantAttractionRagTool())

    def run(self, destination: str, attractions: list[dict[str, Any]], preferences: list[str] | None = None, limit: int = 4) -> dict[str, Any]:
        preferences = preferences or []
        selected = attractions[:limit]
        self.remember_user_input(f"搜索{destination}景区资料，景点={[item.get('name') for item in selected]}，偏好={preferences}")
        insights = []
        for attraction in selected:
            insight = self._build_insight(destination, attraction, preferences)
            if insight:
                insights.append(insight)
        added = self.tools.get("qdrant_attraction_rag").add_documents(insights)
        result = {
            "agent": self.name,
            "destination": destination,
            "scenic_insights": insights,
            "rag_added": added,
            "source": "serpapi" if self.tools.get("serpapi_search").enabled else "rule_fallback",
            "message": f"已整合{len(insights)}个景区介绍，并写入{added}条RAG知识。",
        }
        self.remember_answer(result["message"])
        return result

    def _build_insight(self, destination: str, attraction: dict[str, Any], preferences: list[str]) -> dict[str, Any]:
        name = attraction.get("name", "未命名景点")
        query = f"{destination} {name} 景点 优点 适合人群 游玩攻略"
        search = self.tools.get("serpapi_search").run(query=query, location=destination, num=5)
        snippets = [item.get("snippet", "") for item in search.get("results", []) if item.get("snippet")]
        summary_text = " ".join(snippets) or attraction.get("reason", "") or f"{name}是{destination}的代表性景点。"
        advantages = self._advantages(summary_text, attraction, preferences)
        suitable_for = self._suitable_for(summary_text, attraction, preferences)
        content = self._content(name, summary_text, advantages, suitable_for)
        return {
            "destination": destination,
            "name": name,
            "type": attraction.get("type") or attraction.get("category", "景区"),
            "lat": attraction.get("lat", 0),
            "lng": attraction.get("lng", 0),
            "ticket": attraction.get("ticket", 0),
            "duration": attraction.get("duration", 90),
            "tags": list(dict.fromkeys([*(attraction.get("tags", []) or []), *preferences])),
            "advantages": advantages,
            "suitable_for": suitable_for,
            "content": content,
            "source_links": [item.get("link", "") for item in search.get("results", []) if item.get("link")][:3],
            "source": search.get("source", "rule_fallback"),
        }

    def _advantages(self, text: str, attraction: dict[str, Any], preferences: list[str]) -> list[str]:
        tags = set(attraction.get("tags", []) or []) | set(preferences)
        advantages = []
        if {"文化", "历史", "博物馆", "建筑"} & tags or any(word in text for word in ["历史", "文化", "博物馆", "建筑"]):
            advantages.append("文化信息密度高，适合了解城市历史与代表性建筑。")
        if {"摄影", "夜景", "城市漫步"} & tags or any(word in text for word in ["夜景", "拍照", "风景", "天际线"]):
            advantages.append("观景和拍照条件好，适合安排城市漫步。")
        if {"自然", "公园"} & tags or any(word in text for word in ["公园", "园林", "湖", "自然"]):
            advantages.append("空间开阔、节奏舒缓，适合轻松游览。")
        if "美食" in tags or "小吃" in text:
            advantages.append("周边餐饮选择丰富，方便和美食行程组合。")
        if not advantages:
            advantages.append("辨识度高，适合作为目的地经典行程节点。")
        return advantages[:3]

    def _suitable_for(self, text: str, attraction: dict[str, Any], preferences: list[str]) -> list[str]:
        tags = set(attraction.get("tags", []) or []) | set(preferences)
        people = []
        if {"文化", "历史", "博物馆", "建筑"} & tags:
            people.append("文化历史爱好者")
        if {"摄影", "夜景", "城市漫步"} & tags:
            people.append("摄影和城市漫步游客")
        if "亲子" in tags or any(word in text for word in ["亲子", "儿童", "家庭"]):
            people.append("亲子家庭")
        if "美食" in tags:
            people.append("美食体验型游客")
        if not people:
            people.append("首次到访的普通游客")
        return people[:3]

    def _content(self, name: str, summary_text: str, advantages: list[str], suitable_for: list[str]) -> str:
        short_summary = summary_text[:160].strip()
        return f"{name}介绍：{short_summary} 优点：{'；'.join(advantages)} 适合人群：{'、'.join(suitable_for)}。"

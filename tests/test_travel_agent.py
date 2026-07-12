from fastapi.testclient import TestClient

from backend.app.main import app
from travel_agent import TravelPlannerAgent
from travel_agent.agents.restaurant_agent import RestaurantAgent
from travel_agent.agents.scenic_search_agent import ScenicSearchAgent
from travel_agent.agents.topic_guard_agent import TopicGuardAgent
from travel_agent.core.memory import TravelMemory


def test_travel_planner_generates_complete_plan():
    agent = TravelPlannerAgent()
    plan = agent.run(
        destination="上海",
        start_date="2026-08-01",
        days=2,
        preferences=["文化", "美食"],
        budget_level="舒适",
        people=2,
    )

    assert plan["itinerary"]["destination"] == "上海"
    assert len(plan["itinerary"]["days"]) == 2
    assert len(plan["itinerary"]["weather_info"]) == 2
    assert plan["budget"]["total"] > 0
    assert len(plan["map"]["markers"]) > 0
    assert plan["title"] == "上海旅行计划"
    assert len(plan["collaboration_trace"]) == 8
    assert plan["collaboration_trace"][1]["agent"] == "景区搜索专家"
    assert plan["collaboration_trace"][4]["agent"] == "餐饮推荐专家"
    assert plan["scenic_insights"]
    assert "memory_suggestions" in plan
    assert all(item["on_topic"] for item in plan["topic_checks"])




def test_scenic_search_agent_summarizes_and_falls_back():
    agent = ScenicSearchAgent()
    result = agent.run(
        "上海",
        [{"name": "外滩", "type": "城市漫步", "lat": 31.24, "lng": 121.49, "tags": ["摄影", "城市漫步"], "reason": "经典城市景观。"}],
        ["摄影"],
        limit=1,
    )

    assert result["agent"] == "景区搜索专家"
    assert result["scenic_insights"]
    assert result["scenic_insights"][0]["advantages"]
    assert result["scenic_insights"][0]["suitable_for"]

def test_restaurant_agent_returns_restaurants():
    agent = RestaurantAgent()
    result = agent.run("上海", ["美食"], "舒适")
    assert result["restaurants"]
    assert result["agent"] == "餐饮推荐专家"


def test_memory_module_persists_preferences():
    import tempfile
    from pathlib import Path

    memory = TravelMemory(Path(tempfile.mkdtemp()) / "memory.json")
    memory.remember("上海", ["文化", "美食"], "舒适")
    suggestions = memory.suggest()
    assert suggestions["favorite_destination"] == "上海"
    assert "文化" in suggestions["favorite_preferences"]


def test_topic_guard_blocks_unrelated_agent_output():
    guard = TopicGuardAgent()
    report = guard.run(
        agent_name="测试Agent",
        original_topic={"destination": "上海", "preferences": ["文化"]},
        agent_output="这里是一段股票基金投资建议，和出行无关。",
    )

    assert report["on_topic"] is False
    assert "股票" in report["off_topic_keywords"]


def _sample_plan(client: TestClient) -> dict:
    response = client.post(
        "/api/plan",
        json={
            "destination": "上海",
            "start_date": "2026-08-01",
            "days": 2,
            "preferences": ["文化", "美食"],
            "budget_level": "舒适",
            "people": 2,
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_fastapi_plan_endpoint_returns_typed_wrapped_trip_plan():
    client = TestClient(app)
    data = _sample_plan(client)
    assert data["itinerary"]["destination"] == "上海"
    assert data["itinerary"]["days"][0]["stops"][0]["name"]
    assert data["budget"]["total"] > 0
    assert data["map"]["markers"]
    assert data["collaboration_trace"][0]["input"]
    assert data["topic_checks"]


def test_fastapi_reference_style_trip_path_is_supported():
    client = TestClient(app)
    response = client.post(
        "/api/trip/plan",
        json={
            "destination": "北京",
            "start_date": "2026-08-01",
            "days": 1,
            "preferences": ["文化"],
            "budget_level": "经济",
            "people": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["itinerary"]["destination"] == "北京"


def test_validation_error_has_explicit_code():
    client = TestClient(app)
    response = client.post(
        "/api/plan",
        json={
            "destination": "上海",
            "start_date": "2026-08-01",
            "days": 0,
            "preferences": [],
            "budget_level": "舒适",
            "people": 1,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_health_returns_config_status():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()["data"]
    assert "amap_api_key_configured" in data
    assert "amap_js_api_key_configured" in data
    assert "amap_js_mode" in data
    assert "llm_api_key_configured" in data
    assert "qdrant_configured" in data
    assert "rag_mode" in data
    assert "serpapi_configured" in data
    assert "scenic_search_mode" in data
    assert data["amap_mode"] in {"api", "local_fallback"}
    assert data["llm_mode"] in {"api", "rule_fallback", "disabled"}


def test_poi_and_real_route_fallback_routes():
    client = TestClient(app)
    poi_response = client.get("/api/poi/search", params={"keywords": "博物馆", "city": "上海"})
    assert poi_response.status_code == 200
    assert poi_response.json()["success"] is True

    route_response = client.post(
        "/api/map/route-summary",
        json={"route_type": "walking", "city": "上海", "points": [{"lat": 31.23, "lng": 121.47}, {"lat": 31.24, "lng": 121.49}]},
    )
    assert route_response.status_code == 200
    assert route_response.json()["data"]["distance_km"] > 0
    assert route_response.json()["data"]["segments"]


def test_trip_edit_and_export_endpoints():
    client = TestClient(app)
    plan = _sample_plan(client)
    edit_response = client.post(
        "/api/trip/edit",
        json={"plan": plan, "action": "delete", "day_index": 0, "stop_index": 0},
    )
    assert edit_response.status_code == 200
    edited = edit_response.json()["data"]
    assert edited["budget"]["total"] >= 0

    pdf_response = client.post("/api/export/pdf", json={"plan": edited})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"

    image_response = client.post("/api/export/image", json={"plan": edited})
    assert image_response.status_code == 200
    assert "image/svg+xml" in image_response.headers["content-type"]

def test_amap_js_config_endpoint_returns_frontend_map_settings():
    client = TestClient(app)
    response = client.get("/api/map/js-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "enabled" in data
    assert "key" in data
    assert "expose_security" in data

def test_qdrant_rag_tool_disabled_without_config(monkeypatch):
    from travel_agent.tools.builtin.attraction_rag import QdrantAttractionRagTool

    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("QDRANT_API_KEY", "")
    tool = QdrantAttractionRagTool()

    assert tool.enabled is False
    assert tool.run(destination="上海", preferences=["文化"], limit=2) == []




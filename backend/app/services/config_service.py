from __future__ import annotations

from backend.app.models.schemas import AmapJsConfigModel, ConfigStatusModel
from travel_agent.core.config import get_bool_env, get_env, get_int_env
from travel_agent.core.rate_limit import AMAP_JS_HARD_LIMIT, AMAP_WEB_HARD_LIMIT, clamp_limit


def get_config_status() -> ConfigStatusModel:
    amap_key = bool(get_env("AMAP_API_KEY"))
    amap_js_key = bool(get_env("AMAP_JS_API_KEY"))
    amap_js_security = bool(get_env("AMAP_JS_SECURITY_CODE"))
    amap_js_expose = get_bool_env("AMAP_JS_EXPOSE_SECURITY", False)
    llm_key = bool(get_env("LLM_API_KEY") or get_env("OPENAI_API_KEY"))
    qdrant_url = get_env("QDRANT_URL")
    qdrant_key = get_env("QDRANT_API_KEY")
    qdrant_configured = bool(qdrant_url and qdrant_key and "your-cluster" not in qdrant_url and qdrant_key != "your_qdrant_api_key_here")
    serpapi_key = get_env("SERPAPI_API_KEY")
    serpapi_configured = bool(serpapi_key and serpapi_key != "your_serpapi_api_key_here")
    use_llm = get_bool_env("TRAVEL_AGENT_USE_LLM", True)
    return ConfigStatusModel(
        status="ok",
        amap_api_key_configured=amap_key,
        amap_js_api_key_configured=amap_js_key,
        amap_js_security_code_configured=amap_js_security,
        amap_js_expose_security=amap_js_expose,
        llm_api_key_configured=llm_key,
        qdrant_configured=qdrant_configured,
        serpapi_configured=serpapi_configured,
        travel_agent_use_llm=use_llm,
        amap_mode="api" if amap_key else "local_fallback",
        amap_js_mode="js_api" if amap_js_key and (get_env("AMAP_JS_SERVICE_HOST") or (amap_js_security and amap_js_expose)) else "fallback_svg",
        llm_mode="api" if llm_key and use_llm else ("disabled" if not use_llm else "rule_fallback"),
        rag_mode="qdrant_rag" if qdrant_configured else "disabled",
        scenic_search_mode="serpapi" if serpapi_configured else "rule_fallback",
        amap_web_qps_limit=clamp_limit(get_int_env("AMAP_WEB_QPS", 3), AMAP_WEB_HARD_LIMIT),
        amap_route_qps_limit=clamp_limit(get_int_env("AMAP_ROUTE_QPS", 3), AMAP_WEB_HARD_LIMIT),
        amap_search_qps_limit=clamp_limit(get_int_env("AMAP_SEARCH_QPS", 3), AMAP_WEB_HARD_LIMIT),
        amap_weather_qps_limit=clamp_limit(get_int_env("AMAP_WEATHER_QPS", 3), AMAP_WEB_HARD_LIMIT),
        amap_static_map_qps_limit=clamp_limit(get_int_env("AMAP_STATIC_MAP_QPS", 3), AMAP_WEB_HARD_LIMIT),
        amap_js_qps_limit=clamp_limit(get_int_env("AMAP_JS_QPS", 10), AMAP_JS_HARD_LIMIT),
        amap_rate_limit_mode="shared_in_process",
        llm_base_url=get_env("LLM_BASE_URL") or "https://api.openai.com/v1",
        llm_model=get_env("LLM_MODEL") or "gpt-4o-mini",
    )


def get_amap_js_config() -> AmapJsConfigModel:
    key = get_env("AMAP_JS_API_KEY")
    security_code = get_env("AMAP_JS_SECURITY_CODE")
    expose_security = get_bool_env("AMAP_JS_EXPOSE_SECURITY", False)
    service_host = get_env("AMAP_JS_SERVICE_HOST")
    qps_limit = clamp_limit(get_int_env("AMAP_JS_QPS", 10), AMAP_JS_HARD_LIMIT)

    if not key:
        return AmapJsConfigModel(
            enabled=False,
            qps_limit=qps_limit,
            message="未配置 AMAP_JS_API_KEY，前端使用备用SVG地图。",
        )
    if not service_host and (not security_code or not expose_security):
        return AmapJsConfigModel(
            enabled=False,
            key=key,
            qps_limit=qps_limit,
            message="已配置 JS API Key，但缺少可用的 AMAP_JS_SECURITY_CODE 或 AMAP_JS_SERVICE_HOST。",
        )

    return AmapJsConfigModel(
        enabled=True,
        key=key,
        security_js_code=security_code if expose_security and security_code else "",
        expose_security=expose_security,
        service_host=service_host,
        qps_limit=qps_limit,
        message="高德Web端JS API配置可用。",
    )




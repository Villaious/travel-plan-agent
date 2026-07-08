from __future__ import annotations

from backend.app.models.schemas import AmapJsConfigModel, ConfigStatusModel
from travel_agent.core.config import get_bool_env, get_env


def get_config_status() -> ConfigStatusModel:
    amap_key = bool(get_env("AMAP_API_KEY"))
    amap_js_key = bool(get_env("AMAP_JS_API_KEY"))
    amap_js_security = bool(get_env("AMAP_JS_SECURITY_CODE"))
    amap_js_expose = get_bool_env("AMAP_JS_EXPOSE_SECURITY", False)
    llm_key = bool(get_env("LLM_API_KEY") or get_env("OPENAI_API_KEY"))
    use_llm = get_bool_env("TRAVEL_AGENT_USE_LLM", True)
    return ConfigStatusModel(
        status="ok",
        amap_api_key_configured=amap_key,
        amap_js_api_key_configured=amap_js_key,
        amap_js_security_code_configured=amap_js_security,
        amap_js_expose_security=amap_js_expose,
        llm_api_key_configured=llm_key,
        travel_agent_use_llm=use_llm,
        amap_mode="api" if amap_key else "local_fallback",
        amap_js_mode="js_api" if amap_js_key and (get_env("AMAP_JS_SERVICE_HOST") or (amap_js_security and amap_js_expose)) else "fallback_svg",
        llm_mode="api" if llm_key and use_llm else ("disabled" if not use_llm else "rule_fallback"),
        llm_base_url=get_env("LLM_BASE_URL") or "https://api.openai.com/v1",
        llm_model=get_env("LLM_MODEL") or "gpt-4o-mini",
    )


def get_amap_js_config() -> AmapJsConfigModel:
    key = get_env("AMAP_JS_API_KEY")
    security_code = get_env("AMAP_JS_SECURITY_CODE")
    expose_security = get_bool_env("AMAP_JS_EXPOSE_SECURITY", False)
    service_host = get_env("AMAP_JS_SERVICE_HOST")

    if not key:
        return AmapJsConfigModel(
            enabled=False,
            message="未配置 AMAP_JS_API_KEY，前端使用备用SVG地图。",
        )
    if not service_host and (not security_code or not expose_security):
        return AmapJsConfigModel(
            enabled=False,
            key=key,
            message="已配置 JS API Key，但缺少可用的 AMAP_JS_SECURITY_CODE 或 AMAP_JS_SERVICE_HOST。",
        )

    return AmapJsConfigModel(
        enabled=True,
        key=key,
        security_js_code=security_code if expose_security and security_code else "",
        expose_security=expose_security,
        service_host=service_host,
        message="高德Web端JS API配置可用。",
    )


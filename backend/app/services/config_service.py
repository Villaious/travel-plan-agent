from __future__ import annotations

from backend.app.models.schemas import ConfigStatusModel
from travel_agent.core.config import get_bool_env, get_env


def get_config_status() -> ConfigStatusModel:
    amap_key = bool(get_env("AMAP_API_KEY"))
    llm_key = bool(get_env("LLM_API_KEY") or get_env("OPENAI_API_KEY"))
    use_llm = get_bool_env("TRAVEL_AGENT_USE_LLM", True)
    return ConfigStatusModel(
        status="ok",
        amap_api_key_configured=amap_key,
        llm_api_key_configured=llm_key,
        travel_agent_use_llm=use_llm,
        amap_mode="api" if amap_key else "local_fallback",
        llm_mode="api" if llm_key and use_llm else ("disabled" if not use_llm else "rule_fallback"),
        llm_base_url=get_env("LLM_BASE_URL") or "https://api.openai.com/v1",
        llm_model=get_env("LLM_MODEL") or "gpt-4o-mini",
    )

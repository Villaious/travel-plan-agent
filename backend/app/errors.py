from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from travel_agent.core.exceptions import AgentError, ToolError


ERROR_MESSAGES = {
    "VALIDATION_ERROR": "请求参数不合法",
    "TOPIC_GUARD_FAILED": "主题检查未通过",
    "AMAP_API_ERROR": "高德地图服务调用失败",
    "LLM_API_ERROR": "LLM服务调用失败",
    "AGENT_ERROR": "Agent执行失败",
    "INTERNAL_ERROR": "服务内部错误",
}


def classify_error(exc: Exception) -> tuple[int, str, str]:
    text = str(exc)
    if isinstance(exc, AgentError) and "主题检查" in text:
        return 400, "TOPIC_GUARD_FAILED", text
    if isinstance(exc, ToolError) or "Amap" in text or "高德" in text:
        return 502, "AMAP_API_ERROR", text
    if "LLM" in text or "chat/completions" in text:
        return 502, "LLM_API_ERROR", text
    if isinstance(exc, AgentError):
        return 400, "AGENT_ERROR", text
    return 500, "INTERNAL_ERROR", text


def error_payload(code: str, detail: str) -> dict:
    return {
        "success": False,
        "message": ERROR_MESSAGES.get(code, "请求失败"),
        "error": {"code": code, "detail": detail},
        "data": None,
    }


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload("VALIDATION_ERROR", str(exc.errors())),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        code = exc.detail.get("code", "INTERNAL_ERROR")
        detail = exc.detail.get("detail", ERROR_MESSAGES.get(code, "请求失败"))
    else:
        code = "INTERNAL_ERROR" if exc.status_code >= 500 else "AGENT_ERROR"
        detail = str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=error_payload(code, detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code, code, detail = classify_error(exc)
    return JSONResponse(status_code=status_code, content=error_payload(code, detail))

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import AmapJsConfigModel, ApiResponse, RouteRequest
from backend.app.services.config_service import get_amap_js_config
from backend.app.services.map_service import get_map_service

router = APIRouter(prefix="/map", tags=["地图"])


@router.get("/js-config", response_model=ApiResponse[AmapJsConfigModel], summary="获取高德Web端JS地图配置")
def js_config() -> ApiResponse[AmapJsConfigModel]:
    return ApiResponse(success=True, message="地图JS配置读取成功", data=get_amap_js_config())


@router.post("/route-summary", response_model=ApiResponse[dict], summary="计算路线摘要")
def route_summary(request: RouteRequest) -> ApiResponse[dict]:
    try:
        data = get_map_service().summarize_route(request)
        return ApiResponse(success=True, message="路线摘要生成成功", data=data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "AMAP_API_ERROR", "detail": f"路线摘要生成失败: {exc}"}) from exc

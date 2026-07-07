from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import ApiResponse, RouteRequest
from backend.app.services.map_service import get_map_service

router = APIRouter(prefix="/map", tags=["地图"])


@router.post("/route-summary", response_model=ApiResponse[dict], summary="计算路线摘要")
def route_summary(request: RouteRequest) -> ApiResponse[dict]:
    try:
        data = get_map_service().summarize_route(request)
        return ApiResponse(success=True, message="路线摘要生成成功", data=data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "AMAP_API_ERROR", "detail": f"路线摘要生成失败: {exc}"}) from exc

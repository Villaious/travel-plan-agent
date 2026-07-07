from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.app.errors import classify_error
from backend.app.models.schemas import ApiResponse, TripPlanData, TripPlanRequest, TripPlanResponseModel
from backend.app.services.trip_service import get_trip_planner_service

router = APIRouter(tags=["旅行规划"])


def _error(exc: Exception) -> HTTPException:
    status_code, code, detail = classify_error(exc)
    return HTTPException(status_code=status_code, detail={"code": code, "detail": detail})


@router.post("/plan", response_model=ApiResponse[TripPlanResponseModel], summary="生成旅行计划")
def create_plan(request: TripPlanRequest) -> ApiResponse[TripPlanData]:
    try:
        data = get_trip_planner_service().plan(request)
        return ApiResponse(success=True, message="旅行计划生成成功", data=data)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/trip/plan", response_model=ApiResponse[TripPlanResponseModel], summary="生成旅行计划（兼容参考项目路径）")
def create_trip_plan(request: TripPlanRequest) -> ApiResponse[TripPlanData]:
    return create_plan(request)


@router.get("/trip/health", response_model=ApiResponse[dict[str, Any]], summary="旅行规划服务健康检查")
def trip_health() -> ApiResponse[dict[str, Any]]:
    service = get_trip_planner_service()
    return ApiResponse(
        success=True,
        message="旅行规划服务正常",
        data={"agent": service.agent.name, "history_count": len(service.agent.get_history())},
    )

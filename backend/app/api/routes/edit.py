from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import ApiResponse, TripEditRequest, TripPlanResponseModel
from backend.app.services.edit_service import get_trip_edit_service

router = APIRouter(prefix="/trip", tags=["行程编辑"])


@router.post("/edit", response_model=ApiResponse[TripPlanResponseModel], summary="编辑行程并重算预算地图")
def edit_trip(request: TripEditRequest) -> ApiResponse[dict]:
    try:
        data = get_trip_edit_service().edit(request)
        return ApiResponse(success=True, message="行程已更新", data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "detail": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "detail": f"编辑行程失败: {exc}"}) from exc

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.errors import classify_error
from backend.app.models.schemas import ApiResponse, RouteRecommendationModel, RouteRecommendationRequest
from backend.app.services.route_recommendation_service import get_route_recommendation_service

router = APIRouter(prefix="/route", tags=["路线推荐"])


@router.post("/recommend", response_model=ApiResponse[RouteRecommendationModel], summary="比较多种交通方式并推荐最佳路线")
def recommend_route(request: RouteRecommendationRequest) -> ApiResponse[RouteRecommendationModel]:
    try:
        data = get_route_recommendation_service().recommend(request)
        return ApiResponse(success=True, message="路线规划专家比较完成", data=data)
    except Exception as exc:
        status_code, code, detail = classify_error(exc)
        raise HTTPException(status_code=status_code, detail={"code": code, "detail": detail}) from exc
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import ApiResponse, POISearchRequest
from backend.app.services.poi_service import get_poi_service

router = APIRouter(prefix="/poi", tags=["POI"])


@router.get("/search", response_model=ApiResponse[list[dict]], summary="搜索POI")
def search_poi(
    keywords: str = Query(..., min_length=1, description="搜索关键词"),
    city: str = Query("上海", description="城市"),
    citylimit: bool = Query(True, description="是否限制城市范围"),
    offset: int = Query(10, ge=1, le=25, description="返回数量"),
) -> ApiResponse[list[dict]]:
    try:
        data = get_poi_service().search(POISearchRequest(keywords=keywords, city=city, citylimit=citylimit, offset=offset))
        return ApiResponse(success=True, message="POI搜索成功", data=data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"POI搜索失败: {exc}") from exc

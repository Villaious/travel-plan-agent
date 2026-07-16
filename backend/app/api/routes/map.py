from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import (
    AmapJsConfigModel,
    ApiResponse,
    CoordinateConvertRequest,
    DistanceMeasureRequest,
    RouteRequest,
)
from backend.app.services.amap_geo_service import get_amap_geo_service
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
@router.post("/distance", response_model=ApiResponse[list[dict]], summary="高德距离测量")
def measure_distance(request: DistanceMeasureRequest) -> ApiResponse[list[dict]]:
    try:
        return ApiResponse(success=True, message="距离测量成功", data=get_amap_geo_service().distance(request))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"距离测量失败: {exc}"}) from exc


@router.get("/geocode", response_model=ApiResponse[dict], summary="高德地理编码")
def geocode(address: str = Query(..., min_length=1), city: str = "") -> ApiResponse[dict]:
    try:
        return ApiResponse(success=True, message="地理编码成功", data=get_amap_geo_service().geocode(address, city))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"地理编码失败: {exc}"}) from exc


@router.get("/reverse-geocode", response_model=ApiResponse[dict], summary="高德逆地理编码")
def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(default=1000, ge=0, le=3000),
) -> ApiResponse[dict]:
    try:
        return ApiResponse(success=True, message="逆地理编码成功", data=get_amap_geo_service().reverse_geocode(lat, lng, radius))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"逆地理编码失败: {exc}"}) from exc


@router.post("/coordinate-convert", response_model=ApiResponse[list[dict]], summary="高德坐标转换")
def coordinate_convert(request: CoordinateConvertRequest) -> ApiResponse[list[dict]]:
    try:
        return ApiResponse(success=True, message="坐标转换成功", data=get_amap_geo_service().convert(request))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"坐标转换失败: {exc}"}) from exc


@router.get("/district", response_model=ApiResponse[list[dict]], summary="高德行政区域查询")
def district(
    keywords: str = Query(default="中国", min_length=1),
    subdistrict: int = Query(default=1, ge=0, le=3),
) -> ApiResponse[list[dict]]:
    try:
        return ApiResponse(success=True, message="行政区域查询成功", data=get_amap_geo_service().district(keywords, subdistrict))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"行政区域查询失败: {exc}"}) from exc


@router.get("/ip-location", response_model=ApiResponse[dict], summary="高德IP定位")
def ip_location(ip: str = "") -> ApiResponse[dict]:
    try:
        return ApiResponse(success=True, message="IP定位成功", data=get_amap_geo_service().ip_location(ip))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "AMAP_API_ERROR", "detail": f"IP定位失败: {exc}"}) from exc

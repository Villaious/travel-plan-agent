from __future__ import annotations

from fastapi import APIRouter

from backend.app.models.schemas import ApiResponse, DestinationGroupModel
from travel_agent.data import CHINA_DESTINATION_GROUPS

router = APIRouter(tags=["目的地"])


@router.get("/destinations", response_model=ApiResponse[list[DestinationGroupModel]], summary="获取可选择的中国城市目录")
def list_destinations() -> ApiResponse[list[DestinationGroupModel]]:
    groups = [DestinationGroupModel(**group) for group in CHINA_DESTINATION_GROUPS]
    return ApiResponse(success=True, message="目的地目录读取成功", data=groups)
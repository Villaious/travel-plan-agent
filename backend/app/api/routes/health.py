from __future__ import annotations

from fastapi import APIRouter

from backend.app.models.schemas import ApiResponse, ConfigStatusModel
from backend.app.services.config_service import get_config_status

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=ApiResponse[ConfigStatusModel], summary="健康检查与配置状态")
def health() -> ApiResponse[ConfigStatusModel]:
    return ApiResponse(success=True, message="服务正常", data=get_config_status())

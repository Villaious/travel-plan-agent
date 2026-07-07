from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from backend.app.models.schemas import ExportRequest
from backend.app.services.export_service import get_export_service

router = APIRouter(prefix="/export", tags=["导出"])


@router.post("/pdf", summary="导出PDF")
def export_pdf(request: ExportRequest) -> Response:
    data = get_export_service().build_pdf(request.plan)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="travel-plan.pdf"'},
    )


@router.post("/image", summary="导出路线图片SVG")
def export_image(request: ExportRequest) -> Response:
    svg = get_export_service().build_svg(request.plan)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": 'attachment; filename="travel-route.svg"'},
    )

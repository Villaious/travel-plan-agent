from __future__ import annotations

from functools import lru_cache

from backend.app.models.schemas import CoordinateConvertRequest, DistanceMeasureRequest
from travel_agent.tools import (
    AmapCoordinateConvertTool,
    AmapDistanceTool,
    AmapDistrictTool,
    AmapGeocodeTool,
    AmapIPLocationTool,
    AmapReverseGeocodeTool,
)


class AmapGeoService:
    def __init__(self) -> None:
        self.distance_tool = AmapDistanceTool()
        self.geocode_tool = AmapGeocodeTool()
        self.reverse_geocode_tool = AmapReverseGeocodeTool()
        self.convert_tool = AmapCoordinateConvertTool()
        self.district_tool = AmapDistrictTool()
        self.ip_tool = AmapIPLocationTool()

    def distance(self, request: DistanceMeasureRequest) -> list[dict]:
        return self.distance_tool.run(
            origins=[point.model_dump() for point in request.origins],
            destination=request.destination.model_dump(),
            distance_type=request.distance_type,
        )

    def geocode(self, address: str, city: str = "") -> dict:
        return self.geocode_tool.run(address=address, city=city)

    def reverse_geocode(self, lat: float, lng: float, radius: int = 1000) -> dict:
        return self.reverse_geocode_tool.run(location={"lat": lat, "lng": lng}, radius=radius)

    def convert(self, request: CoordinateConvertRequest) -> list[dict]:
        return self.convert_tool.run(
            locations=[point.model_dump() for point in request.locations],
            coordsys=request.coordsys,
        )

    def district(self, keywords: str = "中国", subdistrict: int = 1) -> list[dict]:
        return self.district_tool.run(keywords=keywords, subdistrict=subdistrict)

    def ip_location(self, ip: str = "") -> dict:
        return self.ip_tool.run(ip=ip)


@lru_cache(maxsize=1)
def get_amap_geo_service() -> AmapGeoService:
    return AmapGeoService()
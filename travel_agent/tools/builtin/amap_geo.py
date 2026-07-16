from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from travel_agent.core.config import get_env, get_int_env
from travel_agent.core.exceptions import ToolError
from travel_agent.core.rate_limit import amap_web_limiter
from travel_agent.tools.base import BaseTool


class _AmapWebTool(BaseTool):
    endpoint = ""

    def __init__(self) -> None:
        self.api_key = get_env("AMAP_API_KEY")
        self.timeout = get_int_env("AMAP_TIMEOUT", 10)
        self.qps = get_int_env("AMAP_WEB_QPS", 3)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ToolError("AMAP_API_KEY is not configured.")
        query = {"key": self.api_key, "output": "JSON", **params}
        try:
            with amap_web_limiter(self.name, self.qps).acquire():
                with urlopen(f"{self.endpoint}?{urlencode(query)}", timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ToolError(f"Amap request failed: {exc}") from exc
        if payload.get("status") != "1":
            raise ToolError(f"Amap request error: {payload.get('info', 'UNKNOWN')}")
        return payload

    def _location(self, point: dict[str, Any]) -> str:
        return f"{float(point['lng']):.6f},{float(point['lat']):.6f}"


class AmapDistanceTool(_AmapWebTool):
    name = "amap_distance"
    description = "Measure straight, driving or walking distance through Amap."
    endpoint = "https://restapi.amap.com/v3/distance"

    def run(self, **kwargs: Any) -> list[dict[str, Any]]:
        origins = kwargs.get("origins", [])
        destination = kwargs["destination"]
        distance_type = int(kwargs.get("distance_type", 0))
        payload = self._request(
            {
                "origins": "|".join(self._location(point) for point in origins),
                "destination": self._location(destination),
                "type": distance_type,
            }
        )
        return [
            {
                "origin_id": int(item.get("origin_id", index + 1)),
                "destination_id": int(item.get("dest_id", 1)),
                "distance_m": int(float(item.get("distance") or 0)),
                "distance_km": round(float(item.get("distance") or 0) / 1000, 2),
                "duration_seconds": int(float(item.get("duration") or 0)),
                "source": "amap",
            }
            for index, item in enumerate(payload.get("results", []))
        ]


class AmapGeocodeTool(_AmapWebTool):
    name = "amap_geocode"
    description = "Convert an address into GCJ-02 coordinates through Amap."
    endpoint = "https://restapi.amap.com/v3/geocode/geo"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        payload = self._request({"address": kwargs["address"], "city": kwargs.get("city", "")})
        items = payload.get("geocodes", [])
        if not items:
            return {}
        item = items[0]
        lng, lat = self._parse_location(item.get("location", ""))
        return {
            "formatted_address": item.get("formatted_address", ""),
            "province": item.get("province", ""),
            "city": item.get("city", ""),
            "district": item.get("district", ""),
            "adcode": item.get("adcode", ""),
            "lat": lat,
            "lng": lng,
            "level": item.get("level", ""),
            "source": "amap",
        }

    def _parse_location(self, location: str) -> tuple[float, float]:
        if "," not in location:
            return 0.0, 0.0
        lng, lat = location.split(",", 1)
        return float(lng), float(lat)


class AmapReverseGeocodeTool(_AmapWebTool):
    name = "amap_reverse_geocode"
    description = "Convert GCJ-02 coordinates into address information through Amap."
    endpoint = "https://restapi.amap.com/v3/geocode/regeo"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        payload = self._request(
            {
                "location": self._location(kwargs["location"]),
                "extensions": kwargs.get("extensions", "base"),
                "radius": int(kwargs.get("radius", 1000)),
            }
        )
        regeocode = payload.get("regeocode", {})
        component = regeocode.get("addressComponent", {})
        return {
            "formatted_address": regeocode.get("formatted_address", ""),
            "province": component.get("province", ""),
            "city": component.get("city", ""),
            "district": component.get("district", ""),
            "township": component.get("township", ""),
            "adcode": component.get("adcode", ""),
            "source": "amap",
        }


class AmapCoordinateConvertTool(_AmapWebTool):
    name = "amap_coordinate_convert"
    description = "Convert supported coordinate systems into Amap GCJ-02 coordinates."
    endpoint = "https://restapi.amap.com/v3/assistant/coordinate/convert"

    def run(self, **kwargs: Any) -> list[dict[str, float]]:
        locations = kwargs.get("locations", [])
        payload = self._request(
            {
                "locations": "|".join(self._location(point) for point in locations),
                "coordsys": kwargs.get("coordsys", "gps"),
            }
        )
        output = []
        for raw in str(payload.get("locations", "")).split(";"):
            if "," not in raw:
                continue
            lng, lat = raw.split(",", 1)
            output.append({"lng": float(lng), "lat": float(lat)})
        return output


class AmapDistrictTool(_AmapWebTool):
    name = "amap_district"
    description = "Query administrative divisions through Amap."
    endpoint = "https://restapi.amap.com/v3/config/district"

    def run(self, **kwargs: Any) -> list[dict[str, Any]]:
        payload = self._request(
            {
                "keywords": kwargs.get("keywords", "中国"),
                "subdistrict": int(kwargs.get("subdistrict", 1)),
                "extensions": kwargs.get("extensions", "base"),
            }
        )
        return payload.get("districts", [])


class AmapIPLocationTool(_AmapWebTool):
    name = "amap_ip_location"
    description = "Locate a domestic IP address through Amap."
    endpoint = "https://restapi.amap.com/v3/ip"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        params = {}
        if kwargs.get("ip"):
            params["ip"] = kwargs["ip"]
        payload = self._request(params)
        rectangle = payload.get("rectangle", "")
        return {
            "province": payload.get("province", ""),
            "city": payload.get("city", ""),
            "adcode": payload.get("adcode", ""),
            "rectangle": rectangle,
            "source": "amap",
        }
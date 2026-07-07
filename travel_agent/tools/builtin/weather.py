from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from travel_agent.core.config import get_env, get_int_env
from travel_agent.tools.base import BaseTool


WEATHER_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "上海": [
        {"weather": "多云", "temperature": 28, "suggestion": "适合城市漫步，午后注意补水。"},
        {"weather": "阵雨", "temperature": 27, "suggestion": "建议把博物馆、商场等室内点位放在下午。"},
        {"weather": "晴", "temperature": 30, "suggestion": "早晚适合外滩和街区摄影。"},
    ],
    "北京": [
        {"weather": "晴", "temperature": 29, "suggestion": "适合故宫、景山等户外路线。"},
        {"weather": "多云", "temperature": 27, "suggestion": "适合颐和园和胡同慢行。"},
        {"weather": "小雨", "temperature": 24, "suggestion": "建议增加博物馆等室内备选。"},
    ],
}

CITY_ADCODES = {
    "北京": "110000",
    "上海": "310000",
    "广州": "440100",
    "深圳": "440300",
    "杭州": "330100",
    "南京": "320100",
    "成都": "510100",
    "重庆": "500000",
    "西安": "610100",
    "武汉": "420100",
}


class WeatherTool(BaseTool):
    name = "weather"
    description = "Query Amap weather forecast, with local fallback when API is unavailable."

    endpoint = "https://restapi.amap.com/v3/weather/weatherInfo"

    def __init__(self) -> None:
        self.api_key = get_env("AMAP_API_KEY")
        self.timeout = get_int_env("AMAP_TIMEOUT", 10)

    def run(self, **kwargs: Any) -> list[dict[str, Any]]:
        destination = kwargs.get("destination", "上海")
        days = max(1, int(kwargs.get("days", 1)))
        start_date = datetime.strptime(kwargs["start_date"], "%Y-%m-%d").date()
        if self.api_key:
            forecast = self._amap_forecast(destination, days)
            if forecast:
                return forecast[:days]
        return self._local_forecast(destination, start_date, days)

    def _amap_forecast(self, destination: str, days: int) -> list[dict[str, Any]]:
        city = CITY_ADCODES.get(destination, destination)
        params = {
            "key": self.api_key,
            "city": city,
            "extensions": "all",
            "output": "JSON",
        }
        url = f"{self.endpoint}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return []
        if payload.get("status") != "1" or not payload.get("forecasts"):
            return []
        casts = payload["forecasts"][0].get("casts", [])
        forecast = []
        for item in casts[:days]:
            temperature = self._average_temp(item.get("daytemp"), item.get("nighttemp"))
            weather = item.get("dayweather") or item.get("nightweather") or "未知"
            forecast.append(
                {
                    "date": item.get("date", ""),
                    "weather": weather,
                    "temperature": temperature,
                    "day_weather": item.get("dayweather", ""),
                    "night_weather": item.get("nightweather", ""),
                    "wind": item.get("daywind", ""),
                    "source": "amap",
                    "suggestion": self._suggestion(weather),
                }
            )
        return forecast

    def _local_forecast(self, destination: str, start_date: Any, days: int) -> list[dict[str, Any]]:
        pattern = WEATHER_PATTERNS.get(destination, WEATHER_PATTERNS["上海"])
        forecast = []
        for index in range(days):
            item = pattern[index % len(pattern)]
            forecast.append({"date": str(start_date + timedelta(days=index)), "source": "local", **item})
        return forecast

    def _average_temp(self, daytemp: Any, nighttemp: Any) -> int:
        try:
            return round((int(daytemp) + int(nighttemp)) / 2)
        except (TypeError, ValueError):
            try:
                return int(daytemp)
            except (TypeError, ValueError):
                return 0

    def _suggestion(self, weather: str) -> str:
        if "雨" in weather:
            return "建议携带雨具，并保留室内景点备选。"
        if "晴" in weather:
            return "适合户外游览，注意防晒和补水。"
        return "适合常规游览，建议按体力调整节奏。"

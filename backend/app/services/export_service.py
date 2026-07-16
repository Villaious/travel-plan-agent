from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from io import BytesIO
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from backend.app.models.schemas import RouteRequest
from backend.app.services.map_service import get_map_service
from travel_agent.core.config import get_env, get_int_env
from travel_agent.core.rate_limit import amap_web_limiter


ROUTE_STYLES = {
    "transit": {"color": "#2f5fd0", "label": "公共交通"},
    "driving": {"color": "#d84e2f", "label": "驾车"},
    "walking": {"color": "#2f8f5b", "label": "步行"},
}


class ExportService:
    def build_pdf(self, plan: dict[str, Any]) -> bytes:
        text_lines = self._plain_lines(plan)[:42]
        commands = ["BT", "/F1 12 Tf", "50 800 Td", "16 TL"]
        for index, line in enumerate(text_lines):
            if index:
                commands.append("T*")
            commands.append(f"<{self._pdf_hex(line)}> Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")

        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >> endobj\n",
            f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
            b"6 0 obj << /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> /FontDescriptor 7 0 R >> endobj\n",
            b"7 0 obj << /Type /FontDescriptor /FontName /STSong-Light /Flags 4 /Ascent 880 /Descent -120 /CapHeight 700 /ItalicAngle 0 /StemV 80 >> endobj\n",
        ]
        return self._assemble_pdf(objects)

    def build_svg(self, plan: dict[str, Any]) -> str:
        markers = self._valid_markers(plan.get("map", {}).get("markers", []))
        title = plan.get("title") or plan.get("summary") or "旅行路线"
        route_type = self._route_type(plan.get("transportation") or plan.get("itinerary", {}).get("transportation", "公共交通"))
        style = ROUTE_STYLES[route_type]
        route_line = self._route_polyline(plan, markers)
        projected_route = self._project_points(route_line or [[item["lng"], item["lat"]] for item in markers])
        marker_points = self._project_points([[item["lng"], item["lat"]] for item in markers])
        polyline = " ".join(f"{x},{y}" for x, y in projected_route)
        background = self._static_map_image(markers, route_line)
        background_node = f'<image href="{background}" x="0" y="0" width="960" height="680" preserveAspectRatio="xMidYMid slice" opacity="0.82"/>' if background else self._fallback_background()
        marker_nodes = []
        for marker, (x, y) in zip(markers, marker_points):
            color = "#b84d7a" if marker.get("category") == "hotel" else "#b87900" if marker.get("category") == "restaurant" else "#394b59"
            marker_nodes.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="white" stroke-width="2"/>')
            marker_nodes.append(f'<text x="{x + 10}" y="{y + 4}" font-size="12" font-family="Microsoft YaHei, Arial" fill="#1f2933" paint-order="stroke" stroke="white" stroke-width="3">{escape(marker.get("name", ""))}</text>')
        arrows = self._route_arrows(projected_route, style["color"])
        legend = self._legend_svg()
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="680" viewBox="0 0 960 680">
  <defs>
    <marker id="routeArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" fill="{style['color']}"/></marker>
  </defs>
  {background_node}
  <rect x="0" y="0" width="960" height="100" fill="rgba(255,255,255,0.88)"/>
  <text x="40" y="42" font-size="24" font-family="Microsoft YaHei, Arial" fill="#1f2933">{escape(title)}</text>
  <text x="40" y="72" font-size="14" font-family="Microsoft YaHei, Arial" fill="#52616b">当前路线：{escape(style['label'])}</text>
  {legend}
  <polyline points="{polyline}" fill="none" stroke="rgba(255,255,255,0.88)" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <polyline points="{polyline}" fill="none" stroke="{style['color']}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#routeArrow)"/>
  {arrows}
  {''.join(marker_nodes)}
</svg>'''

    def _legend_svg(self) -> str:
        items = [("#2f5fd0", "公共交通"), ("#d84e2f", "驾车"), ("#2f8f5b", "步行")]
        nodes = []
        x = 635
        for color, label in items:
            nodes.append(f'<line x1="{x}" y1="40" x2="{x + 28}" y2="40" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
            nodes.append(f'<text x="{x + 36}" y="45" font-size="13" font-family="Microsoft YaHei, Arial" fill="#1f2933">{label}</text>')
            x += 105
        return "".join(nodes)

    def _route_arrows(self, points: list[tuple[int, int]], color: str) -> str:
        nodes = []
        for index, point in enumerate(points[1:-1], start=1):
            if index % 18 != 0:
                continue
            previous = points[index - 1]
            angle = self._angle(previous, point)
            nodes.append(f'<path d="M -5 -3 L 4 0 L -5 3" transform="translate({point[0]} {point[1]}) rotate({angle})" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>')
        return "".join(nodes)

    def _angle(self, previous: tuple[int, int], current: tuple[int, int]) -> float:
        import math

        return math.degrees(math.atan2(current[1] - previous[1], current[0] - previous[0]))

    def _static_map_image(self, markers: list[dict[str, Any]], route_line: list[list[float]]) -> str:
        api_key = get_env("AMAP_API_KEY")
        if not api_key or not markers:
            return ""
        center = self._center(route_line or [[item["lng"], item["lat"]] for item in markers])
        path_points = route_line[:80] if route_line else [[float(item["lng"]), float(item["lat"])] for item in markers]
        params = {
            "key": api_key,
            "location": f"{center[0]:.6f},{center[1]:.6f}",
            "zoom": "12",
            "size": "960*680",
            "scale": "2",
            "paths": "3,0x666666,0.35,,,:" + ";".join(f"{point[0]:.6f},{point[1]:.6f}" for point in path_points),
            "markers": "|".join(f"mid,,{index + 1}:{float(item['lng']):.6f},{float(item['lat']):.6f}" for index, item in enumerate(markers[:10])),
        }
        url = "https://restapi.amap.com/v3/staticmap?" + urlencode(params)
        try:
            timeout = get_int_env("AMAP_TIMEOUT", 10)
            qps = get_int_env("AMAP_STATIC_MAP_QPS", 3)
            with amap_web_limiter("amap_static_map", qps).acquire():
                with urlopen(url, timeout=timeout) as response:
                    data = response.read()
            return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
        except Exception:
            return ""

    def _fallback_background(self) -> str:
        return '<rect width="960" height="680" fill="#eef2f1"/><path d="M 0 120 H 960 M 0 220 H 960 M 0 320 H 960 M 0 420 H 960 M 0 520 H 960 M 160 0 V 680 M 320 0 V 680 M 480 0 V 680 M 640 0 V 680 M 800 0 V 680" stroke="#d4dfdc" stroke-width="1"/>'

    def _center(self, points: list[list[float]]) -> tuple[float, float]:
        lngs = [float(item[0]) for item in points]
        lats = [float(item[1]) for item in points]
        return (sum(lngs) / len(lngs), sum(lats) / len(lats))

    def _assemble_pdf(self, objects: list[bytes]) -> bytes:
        pdf = BytesIO()
        pdf.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(pdf.tell())
            pdf.write(obj)
        xref = pdf.tell()
        pdf.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
        for offset in offsets[1:]:
            pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
        return pdf.getvalue()

    def _plain_lines(self, plan: dict[str, Any]) -> list[str]:
        itinerary = plan.get("itinerary", {})
        lines = [plan.get("title", "旅行计划"), plan.get("summary", "")]
        lines.append(f"交通方式：{plan.get('transportation') or itinerary.get('transportation', '公共交通')}")
        budget = plan.get("budget", {})
        lines.append(f"预算合计：{budget.get('total', 0)} {budget.get('currency', 'CNY')}")
        for day in itinerary.get("days", []):
            lines.append(f"第 {day.get('day')} 天：{day.get('date')}")
            hotel = day.get("hotel", {})
            if hotel:
                lines.append(f"酒店：{hotel.get('name', '待定酒店')}")
            for stop in day.get("stops", []):
                lines.append(f"- {stop.get('time', '')} {stop.get('name', '')}")
        return lines

    def _pdf_hex(self, text: str) -> str:
        return str(text).encode("utf-16-be", errors="replace").hex().upper()

    def _route_polyline(self, plan: dict[str, Any], markers: list[dict[str, Any]]) -> list[list[float]]:
        if len(markers) < 2:
            return []
        route_type = self._route_type(plan.get("transportation") or plan.get("itinerary", {}).get("transportation", "公共交通"))
        try:
            summary = get_map_service().summarize_route(
                RouteRequest(
                    route_type=route_type,
                    city=plan.get("itinerary", {}).get("destination", ""),
                    points=[{"name": item.get("name", ""), "lat": float(item["lat"]), "lng": float(item["lng"])} for item in markers],
                )
            )
            return summary.get("polyline", [])
        except Exception:
            return [[float(item["lng"]), float(item["lat"])] for item in markers]

    def _route_type(self, transportation: str) -> str:
        if any(keyword in transportation for keyword in ["驾车", "自驾", "开车", "打车", "出租"]):
            return "driving"
        if any(keyword in transportation for keyword in ["步行", "徒步"]):
            return "walking"
        return "transit"

    def _valid_markers(self, markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in markers if item.get("lat") and item.get("lng")]

    def _project_points(self, points: list[list[float]]) -> list[tuple[int, int]]:
        if not points:
            return []
        lngs = [float(item[0]) for item in points]
        lats = [float(item[1]) for item in points]
        min_lng, max_lng = min(lngs), max(lngs)
        min_lat, max_lat = min(lats), max(lats)
        projected = []
        for lng, lat in points:
            x = 60 + ((float(lng) - min_lng) / max(0.001, max_lng - min_lng)) * 820
            y = 100 + ((max_lat - float(lat)) / max(0.001, max_lat - min_lat)) * 500
            projected.append((round(x), round(y)))
        return projected


@lru_cache(maxsize=1)
def get_export_service() -> ExportService:
    return ExportService()

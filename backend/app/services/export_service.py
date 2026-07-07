from __future__ import annotations

from functools import lru_cache
from html import escape
from io import BytesIO
from typing import Any


class ExportService:
    def build_pdf(self, plan: dict[str, Any]) -> bytes:
        text_lines = self._plain_lines(plan)
        content = "BT /F1 12 Tf 50 800 Td 16 TL "
        safe_lines = [self._pdf_text(line) for line in text_lines[:42]]
        content += " T* ".join(f"({line}) Tj" for line in safe_lines)
        content += " ET"
        stream = content.encode("latin-1", errors="replace")
        objects = []
        objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
        objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
        objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
        objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n")
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

    def build_svg(self, plan: dict[str, Any]) -> str:
        markers = plan.get("map", {}).get("markers", [])
        title = plan.get("title") or plan.get("summary") or "旅行路线"
        points = self._project(markers)
        polyline = " ".join(f"{x},{y}" for x, y in points)
        marker_nodes = []
        for marker, (x, y) in zip(markers, points):
            color = "#c65b7c" if marker.get("category") == "hotel" else "#087f8c"
            marker_nodes.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{color}" stroke="white" stroke-width="3"/>')
            marker_nodes.append(f'<text x="{x + 12}" y="{y + 4}" font-size="13" fill="#20242a">{escape(marker.get("name", ""))}</text>')
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="680" viewBox="0 0 960 680">
  <rect width="960" height="680" fill="#eef6f4"/>
  <text x="40" y="48" font-size="24" font-family="Arial" fill="#20242a">{escape(title)}</text>
  <polyline points="{polyline}" fill="none" stroke="#087f8c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  {''.join(marker_nodes)}
</svg>'''

    def _plain_lines(self, plan: dict[str, Any]) -> list[str]:
        itinerary = plan.get("itinerary", {})
        lines = [plan.get("title", "Travel Plan"), plan.get("summary", "")]
        budget = plan.get("budget", {})
        lines.append(f"Budget total: {budget.get('total', 0)} {budget.get('currency', 'CNY')}")
        for day in itinerary.get("days", []):
            lines.append(f"Day {day.get('day')}: {day.get('date')}")
            for stop in day.get("stops", []):
                lines.append(f"- {stop.get('time', '')} {stop.get('name', '')}")
        return lines

    def _pdf_text(self, text: str) -> str:
        return str(text).encode("latin-1", errors="replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _project(self, markers: list[dict[str, Any]]) -> list[tuple[int, int]]:
        valid = [item for item in markers if item.get("lat") and item.get("lng")]
        if not valid:
            return []
        lats = [float(item["lat"]) for item in valid]
        lngs = [float(item["lng"]) for item in valid]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        points = []
        for item in valid:
            x = 60 + ((float(item["lng"]) - min_lng) / max(0.001, max_lng - min_lng)) * 820
            y = 90 + ((max_lat - float(item["lat"])) / max(0.001, max_lat - min_lat)) * 520
            points.append((round(x), round(y)))
        return points


@lru_cache(maxsize=1)
def get_export_service() -> ExportService:
    return ExportService()

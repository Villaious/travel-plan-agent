from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TravelMemory:
    """Small JSON-backed memory for user travel preferences."""

    def __init__(self, path: str | Path = "data/travel_memory.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"destinations": {}, "budget_levels": {}, "preferences": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"destinations": {}, "budget_levels": {}, "preferences": {}}

    def remember(self, destination: str, preferences: list[str], budget_level: str) -> dict[str, Any]:
        data = self.load()
        self._count(data.setdefault("destinations", {}), destination)
        self._count(data.setdefault("budget_levels", {}), budget_level)
        pref_counts = data.setdefault("preferences", {})
        for preference in preferences:
            self._count(pref_counts, preference)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def suggest(self) -> dict[str, Any]:
        data = self.load()
        return {
            "favorite_destination": self._top(data.get("destinations", {})),
            "favorite_budget_level": self._top(data.get("budget_levels", {})),
            "favorite_preferences": [item for item, _ in sorted(data.get("preferences", {}).items(), key=lambda pair: pair[1], reverse=True)[:5]],
        }

    def _count(self, bucket: dict[str, int], key: str) -> None:
        if not key:
            return
        bucket[key] = int(bucket.get(key, 0)) + 1

    def _top(self, bucket: dict[str, int]) -> str:
        if not bucket:
            return ""
        return max(bucket.items(), key=lambda pair: pair[1])[0]

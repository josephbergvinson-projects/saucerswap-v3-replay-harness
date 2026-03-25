from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PublishedBenchmarkStatus:
    source: str
    market: str
    status: str
    headline_metrics: dict[str, Any]
    notes: str

    @property
    def comparable(self) -> bool:
        if self.status.strip().lower() in {'placeholder', 'incomplete', 'missing'}:
            return False
        return bool(self.headline_metrics)


def load_published_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def load_published_benchmark_status(path: Path) -> PublishedBenchmarkStatus:
    payload = load_published_results(path)
    headline_metrics = payload.get('headline_metrics')
    if not isinstance(headline_metrics, dict):
        headline_metrics = {}
    return PublishedBenchmarkStatus(
        source=str(payload.get('source', 'Lambdaplex published benchmark panel')),
        market=str(payload.get('market', 'unknown')),
        status=str(payload.get('status', 'missing')),
        headline_metrics=headline_metrics,
        notes=str(payload.get('notes', '')).strip(),
    )

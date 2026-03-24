from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookLevel:
    spread_bps: float
    size_usd: float


def allocate_depth(total_depth_usd: float, levels: list[tuple[float, float]]) -> list[BookLevel]:
    total_weight = sum(weight for _, weight in levels)
    return [
        BookLevel(spread_bps=spread, size_usd=total_depth_usd * (weight / total_weight))
        for spread, weight in levels
    ]

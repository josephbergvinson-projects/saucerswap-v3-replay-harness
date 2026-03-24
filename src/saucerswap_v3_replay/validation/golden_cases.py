from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenCase:
    name: str
    expected_completion_ratio: float
    expected_admissibility: bool | None

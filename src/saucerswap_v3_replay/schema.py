from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReplayUnit:
    replay_unit_id: str
    timestamp: str
    tx_id: str
    event_index: int
    side: str
    requested_size: float
    requested_notional: float
    reference_price: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionRecord:
    lane: str
    replay_unit_id: str
    side: str
    requested_size: float
    requested_notional: float
    filled_size: float
    filled_notional: float
    completion_ratio: float
    reference_price: float
    avg_execution_price: float
    fees_paid: float = 0.0
    remainder_size: float = 0.0
    route_breakdown: dict[str, float] = field(default_factory=dict)
    admissibility_passed: bool | None = None

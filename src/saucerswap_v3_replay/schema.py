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
    trade_row_id: int | None = None
    swap_event_id: str | None = None
    trade_timestamp_seconds: int | None = None
    reference_price_source: str | None = None
    reference_price_fallback: bool = False
    swap_metadata_covered: bool = False
    fee_covered: bool = False


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
    fee_contract_version: str = ''
    fee_scenario_id: str = ''
    v3_min_order_ineligible: bool = False
    fee_basis_filled_notional_usd: float = 0.0
    trader_fee_paid_usd: float = 0.0
    protocol_fee_earned_usd: float = 0.0
    active_lp_fee_earned_usd: float = 0.0
    maker_rebate_earned_usd: float = 0.0
    remainder_size: float = 0.0
    route_breakdown: dict[str, float] = field(default_factory=dict)
    fee_route_breakdown: dict[str, Any] = field(default_factory=dict)
    admissibility_passed: bool | None = None

from __future__ import annotations

from dataclasses import dataclass

from ..metrics.core import completion_ratio
from ..schema import ExecutionRecord, ReplayUnit
from .book_profile import BookLevel


@dataclass(frozen=True)
class SimulatedFill:
    filled_size: float
    avg_execution_price: float
    remainder_size: float


def walk_replenishing_book(unit: ReplayUnit, levels: list[BookLevel]) -> SimulatedFill:
    remaining_notional = unit.requested_notional
    weighted_price = 0.0
    filled_notional = 0.0

    for level in levels:
        if remaining_notional <= 0:
            break
        take = min(level.size_usd, remaining_notional)
        direction = 1 if unit.side == 'buy' else -1
        exec_price = unit.reference_price * (1 + direction * level.spread_bps / 10_000)
        weighted_price += take * exec_price
        filled_notional += take
        remaining_notional -= take

    if filled_notional == 0:
        return SimulatedFill(filled_size=0.0, avg_execution_price=unit.reference_price, remainder_size=unit.requested_size)

    fill_ratio = filled_notional / unit.requested_notional if unit.requested_notional else 0.0
    filled_size = unit.requested_size * fill_ratio
    avg_execution_price = weighted_price / filled_notional
    remainder_size = max(unit.requested_size - filled_size, 0.0)
    return SimulatedFill(filled_size=filled_size, avg_execution_price=avg_execution_price, remainder_size=remainder_size)


def simulate_pure_book(unit: ReplayUnit, levels: list[BookLevel]) -> ExecutionRecord:
    fill = walk_replenishing_book(unit, levels)
    filled_notional = fill.filled_size * fill.avg_execution_price
    return ExecutionRecord(
        lane='3a_pure_book',
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=fill.filled_size,
        filled_notional=filled_notional,
        completion_ratio=completion_ratio(fill.filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=fill.avg_execution_price,
        remainder_size=fill.remainder_size,
        route_breakdown={'pure_book': fill.filled_size},
    )

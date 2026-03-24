from __future__ import annotations

from ..metrics.core import completion_ratio
from ..schema import ExecutionRecord, ReplayUnit


def build_v2_realized_record(unit: ReplayUnit, execution_price: float, fees_paid: float = 0.0) -> ExecutionRecord:
    filled_size = unit.requested_size
    filled_notional = filled_size * execution_price
    return ExecutionRecord(
        lane='v2_realized',
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=filled_size,
        filled_notional=filled_notional,
        completion_ratio=completion_ratio(filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=execution_price,
        fees_paid=fees_paid,
        remainder_size=0.0,
        route_breakdown={'v2': filled_size},
        admissibility_passed=True,
    )

from __future__ import annotations

from ..backstop.v2_residual import ResidualQuote
from ..metrics.core import completion_ratio
from ..rules.admissibility import passes_slippage_cap
from ..schema import ExecutionRecord, ReplayUnit
from .book_profile import BookLevel
from .pure_book import walk_replenishing_book


def simulate_hybrid(unit: ReplayUnit, levels: list[BookLevel], residual_quote: ResidualQuote | None, max_slippage_bps: float) -> ExecutionRecord:
    book_fill = walk_replenishing_book(unit, levels)
    filled_size = book_fill.filled_size
    weighted_notional = book_fill.filled_size * book_fill.avg_execution_price
    route_breakdown = {'pure_book': book_fill.filled_size}
    admissibility_passed = None

    if book_fill.remainder_size > 0 and residual_quote is not None:
        admissibility_passed = passes_slippage_cap(
            side=unit.side,
            reference_price=unit.reference_price,
            execution_price=residual_quote.execution_price,
            max_slippage_bps=max_slippage_bps,
        )
        if admissibility_passed:
            routed_size = min(book_fill.remainder_size, residual_quote.available_size)
            filled_size += routed_size
            weighted_notional += routed_size * residual_quote.execution_price
            route_breakdown['v2_backstop'] = routed_size

    avg_execution_price = weighted_notional / filled_size if filled_size else unit.reference_price
    remainder_size = max(unit.requested_size - filled_size, 0.0)
    return ExecutionRecord(
        lane='3b_hybrid',
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=filled_size,
        filled_notional=filled_size * avg_execution_price,
        completion_ratio=completion_ratio(filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=avg_execution_price,
        remainder_size=remainder_size,
        route_breakdown=route_breakdown,
        admissibility_passed=admissibility_passed,
    )

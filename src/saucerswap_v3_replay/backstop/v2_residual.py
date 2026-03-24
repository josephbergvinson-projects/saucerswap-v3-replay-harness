from __future__ import annotations

from dataclasses import dataclass

from ..normalize.events import parse_float, parse_int


@dataclass(frozen=True)
class ResidualQuote:
    execution_price: float
    available_size: float
    source: str = 'historical_v2_proxy'
    replay_unit_id: str | None = None
    trade_row_id: int | None = None
    swap_event_id: str | None = None
    trade_timestamp_seconds: int | None = None


def residual_quote_from_v2_row(row: dict[str, str]) -> ResidualQuote | None:
    execution_price_text = row.get('avg_execution_price') or row.get('execution_price') or ''
    available_size_text = row.get('filled_size') or row.get('available_size') or ''
    if not execution_price_text or not available_size_text:
        return None

    execution_price = parse_float(execution_price_text)
    available_size = parse_float(available_size_text)
    if execution_price <= 0 or available_size <= 0:
        return None

    trade_row_id_text = row.get('tradeRowId') or ''
    trade_timestamp_seconds_text = row.get('tradeTimestampSeconds') or ''
    return ResidualQuote(
        execution_price=execution_price,
        available_size=available_size,
        source=row.get('lane') or 'historical_v2_proxy',
        replay_unit_id=row.get('replay_unit_id') or None,
        trade_row_id=parse_int(trade_row_id_text) if trade_row_id_text else None,
        swap_event_id=row.get('swapEventId') or None,
        trade_timestamp_seconds=(
            parse_int(trade_timestamp_seconds_text) if trade_timestamp_seconds_text else None
        ),
    )

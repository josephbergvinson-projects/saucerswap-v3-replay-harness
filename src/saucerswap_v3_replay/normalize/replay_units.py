from __future__ import annotations

from typing import Iterable

from ..schema import ReplayUnit


def materialize_replay_units(events: Iterable[ReplayUnit]) -> list[ReplayUnit]:
    return sorted(events, key=_replay_unit_ordering_key)


def collapse_by_tx_side(events: Iterable[ReplayUnit]) -> list[ReplayUnit]:
    """Compatibility shim for the older API.

    RH-03 locks the harness to one replay unit per observed trade row, so this
    function now preserves event-level rows rather than collapsing them.
    """

    return materialize_replay_units(events)


def _replay_unit_ordering_key(unit: ReplayUnit) -> tuple[int, int, int]:
    trade_timestamp_seconds = (
        unit.trade_timestamp_seconds if unit.trade_timestamp_seconds is not None else 0
    )
    swap_event_id = unit.swap_event_id or unit.tx_id
    return (
        trade_timestamp_seconds,
        _numeric_key(swap_event_id),
        unit.trade_row_id if unit.trade_row_id is not None else unit.event_index,
    )


def _numeric_key(value: str | int | None) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).replace(',', ''))
    except ValueError:
        return 0

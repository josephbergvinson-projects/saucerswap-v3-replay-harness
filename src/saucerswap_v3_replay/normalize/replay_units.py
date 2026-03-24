from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..schema import ReplayUnit


def collapse_by_tx_side(events: Iterable[ReplayUnit]) -> list[ReplayUnit]:
    grouped: dict[tuple[str, str], list[ReplayUnit]] = defaultdict(list)
    for event in events:
        grouped[(event.tx_id, event.side)].append(event)

    out: list[ReplayUnit] = []
    for (_, _), items in grouped.items():
        items = sorted(items, key=lambda item: item.event_index)
        head = items[0]
        out.append(
            ReplayUnit(
                replay_unit_id=head.replay_unit_id,
                timestamp=head.timestamp,
                tx_id=head.tx_id,
                event_index=head.event_index,
                side=head.side,
                requested_size=sum(item.requested_size for item in items),
                requested_notional=sum(item.requested_notional for item in items),
                reference_price=head.reference_price,
                metadata={'collapsed_events': len(items)},
            )
        )
    return sorted(out, key=lambda item: (item.timestamp, item.event_index))

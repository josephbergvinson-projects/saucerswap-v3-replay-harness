from __future__ import annotations

from collections import defaultdict

from ..schema import ExecutionRecord


def aggregate_by_lane(records: list[ExecutionRecord]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[ExecutionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.lane].append(record)

    summary: dict[str, dict[str, float]] = {}
    for lane, items in grouped.items():
        summary[lane] = {
            'count': float(len(items)),
            'avg_completion_ratio': sum(item.completion_ratio for item in items) / len(items),
            'avg_execution_price': sum(item.avg_execution_price for item in items) / len(items),
        }
    return summary

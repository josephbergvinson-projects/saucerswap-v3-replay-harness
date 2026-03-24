from __future__ import annotations


def reconcile_totals(raw_count: int, normalized_count: int) -> dict[str, int | bool]:
    return {
        'raw_count': raw_count,
        'normalized_count': normalized_count,
        'counts_match': raw_count == normalized_count,
    }

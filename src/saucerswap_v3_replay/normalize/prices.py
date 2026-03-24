from __future__ import annotations


def midpoint(bid: float, ask: float) -> float:
    if bid <= 0 or ask <= 0:
        raise ValueError('Bid and ask must be positive')
    return (bid + ask) / 2.0

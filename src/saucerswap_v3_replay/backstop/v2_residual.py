from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResidualQuote:
    execution_price: float
    available_size: float
    source: str = 'historical_v2_proxy'

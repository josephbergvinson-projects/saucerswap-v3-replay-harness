from __future__ import annotations

from bisect import bisect_right
import csv
from dataclasses import dataclass
from pathlib import Path

from .events import parse_float, parse_int


@dataclass(frozen=True)
class ReferencePriceMatch:
    trade_timestamp_seconds: int
    source_timestamp_seconds: int
    reference_price: float
    source: str
    fallback: bool


class ReferencePriceIndex:
    def __init__(self, timestamps: list[int], reference_prices: list[float]) -> None:
        if len(timestamps) != len(reference_prices):
            raise ValueError('Reference price timestamps and values must align')
        self._timestamps = timestamps
        self._reference_prices = reference_prices

    @classmethod
    def from_csv(cls, path: str | Path) -> 'ReferencePriceIndex':
        timestamps: list[int] = []
        reference_prices: list[float] = []
        with Path(path).open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                timestamps.append(parse_int(row['timestampSeconds']))
                reference_prices.append(normalize_raw_reference_price(parse_float(row['price'])))
        return cls(timestamps=timestamps, reference_prices=reference_prices)

    @property
    def row_count(self) -> int:
        return len(self._timestamps)

    @property
    def min_timestamp_seconds(self) -> int | None:
        return self._timestamps[0] if self._timestamps else None

    @property
    def max_timestamp_seconds(self) -> int | None:
        return self._timestamps[-1] if self._timestamps else None

    def lookup(self, trade_timestamp_seconds: int) -> ReferencePriceMatch:
        if not self._timestamps:
            raise ValueError('Reference price index is empty')
        idx = bisect_right(self._timestamps, trade_timestamp_seconds) - 1
        if idx >= 0:
            return ReferencePriceMatch(
                trade_timestamp_seconds=trade_timestamp_seconds,
                source_timestamp_seconds=self._timestamps[idx],
                reference_price=self._reference_prices[idx],
                source='at_or_before',
                fallback=False,
            )
        return ReferencePriceMatch(
            trade_timestamp_seconds=trade_timestamp_seconds,
            source_timestamp_seconds=self._timestamps[0],
            reference_price=self._reference_prices[0],
            source='nearest_later',
            fallback=True,
        )


def midpoint(bid: float, ask: float) -> float:
    if bid <= 0 or ask <= 0:
        raise ValueError('Bid and ask must be positive')
    return (bid + ask) / 2.0


def normalize_raw_reference_price(raw_hbar_per_usdc: float) -> float:
    if raw_hbar_per_usdc <= 0:
        raise ValueError('Raw reference price must be positive')
    return 1.0 / raw_hbar_per_usdc

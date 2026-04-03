from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Callable, Iterable

from ..fees import bps
from ..normalize.events import parse_float, parse_int
from .fee_views import execution_shortfall_usd


@dataclass(frozen=True)
class SpreadCaptureObservation:
    lane: str
    side: str
    requested_notional: float
    requested_notional_raw: int
    resting_book_filled_size: float
    resting_book_filled_notional_usd: float
    gross_spread_capture_usd: float


@dataclass(frozen=True)
class SpreadCaptureRollupSummary:
    row_count: int
    requested_notional_raw_total: int
    resting_book_filled_size_total: float
    resting_book_filled_notional_total: float
    gross_spread_capture_total: float
    resting_book_fill_rows: int
    zero_resting_book_fill_rows: int

    @property
    def requested_notional_total(self) -> float:
        return self.requested_notional_raw_total / 1_000_000

    @property
    def gross_spread_capture_bps_on_requested_notional(self) -> float:
        return bps(self.gross_spread_capture_total, self.requested_notional_total)

    @property
    def gross_spread_capture_bps_on_resting_book_filled_notional(self) -> float:
        return bps(self.gross_spread_capture_total, self.resting_book_filled_notional_total)


@dataclass
class _SpreadCaptureRollupAccumulator:
    row_count: int = 0
    requested_notional_raw_total: int = 0
    resting_book_filled_size_total: float = 0.0
    resting_book_filled_notional_total: float = 0.0
    gross_spread_capture_total: float = 0.0
    resting_book_fill_rows: int = 0
    zero_resting_book_fill_rows: int = 0

    def add(self, observation: SpreadCaptureObservation) -> None:
        self.row_count += 1
        self.requested_notional_raw_total += observation.requested_notional_raw
        self.resting_book_filled_size_total += observation.resting_book_filled_size
        self.resting_book_filled_notional_total += observation.resting_book_filled_notional_usd
        self.gross_spread_capture_total += observation.gross_spread_capture_usd
        if observation.resting_book_filled_size > 0.0:
            self.resting_book_fill_rows += 1
        else:
            self.zero_resting_book_fill_rows += 1

    def finalize(self) -> SpreadCaptureRollupSummary:
        return SpreadCaptureRollupSummary(
            row_count=self.row_count,
            requested_notional_raw_total=self.requested_notional_raw_total,
            resting_book_filled_size_total=self.resting_book_filled_size_total,
            resting_book_filled_notional_total=self.resting_book_filled_notional_total,
            gross_spread_capture_total=self.gross_spread_capture_total,
            resting_book_fill_rows=self.resting_book_fill_rows,
            zero_resting_book_fill_rows=self.zero_resting_book_fill_rows,
        )


def gross_spread_capture_usd(
    *,
    side: str,
    reference_price: float,
    filled_size: float,
    filled_notional: float,
) -> float:
    return execution_shortfall_usd(
        side=side,
        reference_price=reference_price,
        filled_size=filled_size,
        filled_notional=filled_notional,
    )


def roll_up_spread_capture_observations(
    observations: Iterable[SpreadCaptureObservation],
    *,
    bucket_label: Callable[[SpreadCaptureObservation], str] | None = None,
) -> tuple[SpreadCaptureRollupSummary, dict[str, SpreadCaptureRollupSummary], dict[str, SpreadCaptureRollupSummary]]:
    aggregate = _SpreadCaptureRollupAccumulator()
    by_side: dict[str, _SpreadCaptureRollupAccumulator] = {}
    by_bucket: dict[str, _SpreadCaptureRollupAccumulator] = {}

    for observation in observations:
        aggregate.add(observation)

        side_accumulator = by_side.setdefault(observation.side, _SpreadCaptureRollupAccumulator())
        side_accumulator.add(observation)

        if bucket_label is not None:
            label = bucket_label(observation)
            bucket_accumulator = by_bucket.setdefault(label, _SpreadCaptureRollupAccumulator())
            bucket_accumulator.add(observation)

    return (
        aggregate.finalize(),
        {key: value.finalize() for key, value in by_side.items()},
        {key: value.finalize() for key, value in by_bucket.items()},
    )


def spread_capture_observation_from_row(row: dict[str, str]) -> SpreadCaptureObservation:
    resting_book_filled_size, resting_book_filled_notional = resting_book_leg_from_row(row)
    return SpreadCaptureObservation(
        lane=row['lane'],
        side=row['side'],
        requested_notional=parse_float(row['requested_notional']),
        requested_notional_raw=parse_int(row['baseVolumeRaw']),
        resting_book_filled_size=resting_book_filled_size,
        resting_book_filled_notional_usd=resting_book_filled_notional,
        gross_spread_capture_usd=gross_spread_capture_usd(
            side=row['side'],
            reference_price=parse_float(row['reference_price']),
            filled_size=resting_book_filled_size,
            filled_notional=resting_book_filled_notional,
        ),
    )


def resting_book_leg_from_row(row: dict[str, str]) -> tuple[float, float]:
    lane = row['lane']
    if lane == '3a_pure_book':
        return parse_float(row['filled_size']), parse_float(row['filled_notional'])
    if lane == '3b_hybrid':
        route_breakdown = _parse_route_breakdown(row.get('route_breakdown'))
        pure_book_size_hint = parse_float(str(route_breakdown.get('pure_book', 0.0) or 0.0))

        fee_route_breakdown = _parse_route_breakdown(row.get('fee_route_breakdown'))
        pure_book_route = fee_route_breakdown.get('pure_book')
        if isinstance(pure_book_route, dict):
            return (
                parse_float(str(pure_book_route.get('filled_size', pure_book_size_hint) or pure_book_size_hint)),
                parse_float(str(pure_book_route.get('filled_notional_usd', 0.0) or 0.0)),
            )

        if pure_book_size_hint <= 0.0:
            return 0.0, 0.0

        total_filled_size = parse_float(row['filled_size'])
        if math.isclose(pure_book_size_hint, total_filled_size, rel_tol=1e-12, abs_tol=1e-12):
            return pure_book_size_hint, parse_float(row['filled_notional'])

        raise ValueError(
            'Hybrid spread-capture rollup requires fee_route_breakdown.pure_book '
            'when the row includes both pure-book and backstop execution.'
        )
    raise ValueError(f'Unsupported spread-capture lane: {lane}')


def _parse_route_breakdown(value: str | None) -> dict[str, object]:
    text = '' if value is None else str(value).strip()
    if not text:
        return {}
    payload = json.loads(text)
    if not isinstance(payload, dict):
        return {}
    return payload

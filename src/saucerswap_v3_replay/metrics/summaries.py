from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Callable, Iterable

from ..schema import ExecutionRecord

FULL_FILL_TOLERANCE = 1e-9


@dataclass(frozen=True)
class LaneObservation:
    lane: str
    side: str
    requested_size: float
    requested_notional: float
    requested_size_raw: int
    requested_notional_raw: int
    filled_size: float
    filled_notional: float
    completion_ratio: float
    remainder_size: float
    slippage_bps: float
    fee_covered: bool
    admissibility_passed: bool | None = None


@dataclass(frozen=True)
class RollupSummary:
    row_count: int
    requested_size_raw_total: int
    requested_notional_raw_total: int
    filled_size_total: float
    filled_notional_total: float
    remainder_size_total: float
    fill_rate: float
    avg_completion_ratio: float
    avg_slippage_bps: float
    avg_abs_slippage_bps: float
    finite_slippage_rows: int
    non_finite_slippage_rows: int
    full_fill_rows: int
    partial_fill_rows: int
    zero_fill_rows: int
    fee_covered_rows: int
    fee_missing_rows: int
    admissibility_pass_rows: int
    admissibility_fail_rows: int
    admissibility_unknown_rows: int


@dataclass
class _RollupAccumulator:
    row_count: int = 0
    requested_size_total: float = 0.0
    requested_notional_total: float = 0.0
    requested_size_raw_total: int = 0
    requested_notional_raw_total: int = 0
    filled_size_total: float = 0.0
    filled_notional_total: float = 0.0
    remainder_size_total: float = 0.0
    completion_ratio_sum: float = 0.0
    slippage_sum_bps: float = 0.0
    slippage_abs_sum_bps: float = 0.0
    finite_slippage_rows: int = 0
    non_finite_slippage_rows: int = 0
    full_fill_rows: int = 0
    partial_fill_rows: int = 0
    zero_fill_rows: int = 0
    fee_covered_rows: int = 0
    fee_missing_rows: int = 0
    admissibility_pass_rows: int = 0
    admissibility_fail_rows: int = 0
    admissibility_unknown_rows: int = 0

    def add(self, observation: LaneObservation) -> None:
        self.row_count += 1
        self.requested_size_total += observation.requested_size
        self.requested_notional_total += observation.requested_notional
        self.requested_size_raw_total += observation.requested_size_raw
        self.requested_notional_raw_total += observation.requested_notional_raw
        self.filled_size_total += observation.filled_size
        self.filled_notional_total += observation.filled_notional
        self.remainder_size_total += observation.remainder_size
        self.completion_ratio_sum += observation.completion_ratio

        if observation.filled_size <= 0:
            self.zero_fill_rows += 1
        elif observation.remainder_size > 0.0:
            self.partial_fill_rows += 1
        else:
            self.full_fill_rows += 1

        if observation.fee_covered:
            self.fee_covered_rows += 1
        else:
            self.fee_missing_rows += 1

        if observation.admissibility_passed is True:
            self.admissibility_pass_rows += 1
        elif observation.admissibility_passed is False:
            self.admissibility_fail_rows += 1
        else:
            self.admissibility_unknown_rows += 1

        if math.isfinite(observation.slippage_bps):
            self.finite_slippage_rows += 1
            self.slippage_sum_bps += observation.slippage_bps
            self.slippage_abs_sum_bps += abs(observation.slippage_bps)
        else:
            self.non_finite_slippage_rows += 1

    def finalize(self) -> RollupSummary:
        fill_rate = 0.0
        if self.requested_size_total > 0:
            fill_rate = round(self.filled_size_total / self.requested_size_total, 12)
        return RollupSummary(
            row_count=self.row_count,
            requested_size_raw_total=self.requested_size_raw_total,
            requested_notional_raw_total=self.requested_notional_raw_total,
            filled_size_total=self.filled_size_total,
            filled_notional_total=self.filled_notional_total,
            remainder_size_total=self.remainder_size_total,
            fill_rate=fill_rate,
            avg_completion_ratio=_safe_average(self.completion_ratio_sum, self.row_count),
            avg_slippage_bps=_safe_average(self.slippage_sum_bps, self.finite_slippage_rows),
            avg_abs_slippage_bps=_safe_average(self.slippage_abs_sum_bps, self.finite_slippage_rows),
            finite_slippage_rows=self.finite_slippage_rows,
            non_finite_slippage_rows=self.non_finite_slippage_rows,
            full_fill_rows=self.full_fill_rows,
            partial_fill_rows=self.partial_fill_rows,
            zero_fill_rows=self.zero_fill_rows,
            fee_covered_rows=self.fee_covered_rows,
            fee_missing_rows=self.fee_missing_rows,
            admissibility_pass_rows=self.admissibility_pass_rows,
            admissibility_fail_rows=self.admissibility_fail_rows,
            admissibility_unknown_rows=self.admissibility_unknown_rows,
        )


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


def roll_up_observations(
    observations: Iterable[LaneObservation],
    *,
    bucket_label: Callable[[LaneObservation], str] | None = None,
) -> tuple[RollupSummary, dict[str, RollupSummary], dict[str, RollupSummary]]:
    aggregate = _RollupAccumulator()
    by_side: dict[str, _RollupAccumulator] = {}
    by_bucket: dict[str, _RollupAccumulator] = {}

    for observation in observations:
        aggregate.add(observation)

        side_accumulator = by_side.setdefault(observation.side, _RollupAccumulator())
        side_accumulator.add(observation)

        if bucket_label is not None:
            label = bucket_label(observation)
            bucket_accumulator = by_bucket.setdefault(label, _RollupAccumulator())
            bucket_accumulator.add(observation)

    return (
        aggregate.finalize(),
        {key: value.finalize() for key, value in by_side.items()},
        {key: value.finalize() for key, value in by_bucket.items()},
    )


def _safe_average(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 12)

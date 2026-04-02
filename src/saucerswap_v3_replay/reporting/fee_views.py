from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Callable, Iterable

from ..fees import bps
from ..normalize.events import parse_float, parse_int


@dataclass(frozen=True)
class FeeObservation:
    lane: str
    side: str
    requested_notional: float
    requested_notional_raw: int
    fee_basis_filled_notional_usd: float
    trader_fee_paid_usd: float
    protocol_fee_earned_usd: float
    active_lp_fee_earned_usd: float
    maker_rebate_earned_usd: float
    execution_shortfall_usd: float
    all_in_trader_cost_usd: float
    v3_min_order_ineligible: bool


@dataclass(frozen=True)
class FeeRollupSummary:
    row_count: int
    requested_notional_raw_total: int
    fee_basis_filled_notional_total: float
    trader_fee_paid_total: float
    protocol_fee_earned_total: float
    active_lp_fee_earned_total: float
    maker_rebate_earned_total: float
    execution_shortfall_total: float
    all_in_trader_cost_total: float
    v3_min_order_ineligible_rows: int

    @property
    def requested_notional_total(self) -> float:
        return self.requested_notional_raw_total / 1_000_000

    @property
    def liquidity_side_fee_earned_total(self) -> float:
        return self.active_lp_fee_earned_total + self.maker_rebate_earned_total

    @property
    def trader_fee_paid_bps_on_requested_notional(self) -> float:
        return bps(self.trader_fee_paid_total, self.requested_notional_total)

    @property
    def trader_fee_paid_bps_on_filled_notional(self) -> float:
        return bps(self.trader_fee_paid_total, self.fee_basis_filled_notional_total)

    @property
    def protocol_fee_earned_bps_on_requested_notional(self) -> float:
        return bps(self.protocol_fee_earned_total, self.requested_notional_total)

    @property
    def protocol_fee_earned_bps_on_filled_notional(self) -> float:
        return bps(self.protocol_fee_earned_total, self.fee_basis_filled_notional_total)

    @property
    def active_lp_fee_earned_bps_on_requested_notional(self) -> float:
        return bps(self.active_lp_fee_earned_total, self.requested_notional_total)

    @property
    def active_lp_fee_earned_bps_on_filled_notional(self) -> float:
        return bps(self.active_lp_fee_earned_total, self.fee_basis_filled_notional_total)

    @property
    def maker_rebate_earned_bps_on_requested_notional(self) -> float:
        return bps(self.maker_rebate_earned_total, self.requested_notional_total)

    @property
    def maker_rebate_earned_bps_on_filled_notional(self) -> float:
        return bps(self.maker_rebate_earned_total, self.fee_basis_filled_notional_total)

    @property
    def liquidity_side_fee_earned_bps_on_requested_notional(self) -> float:
        return bps(self.liquidity_side_fee_earned_total, self.requested_notional_total)

    @property
    def liquidity_side_fee_earned_bps_on_filled_notional(self) -> float:
        return bps(self.liquidity_side_fee_earned_total, self.fee_basis_filled_notional_total)

    @property
    def execution_shortfall_bps_on_requested_notional(self) -> float:
        return bps(self.execution_shortfall_total, self.requested_notional_total)

    @property
    def execution_shortfall_bps_on_filled_notional(self) -> float:
        return bps(self.execution_shortfall_total, self.fee_basis_filled_notional_total)

    @property
    def all_in_trader_cost_bps_on_requested_notional(self) -> float:
        return bps(self.all_in_trader_cost_total, self.requested_notional_total)

    @property
    def all_in_trader_cost_bps_on_filled_notional(self) -> float:
        return bps(self.all_in_trader_cost_total, self.fee_basis_filled_notional_total)


@dataclass
class _FeeRollupAccumulator:
    row_count: int = 0
    requested_notional_raw_total: int = 0
    fee_basis_filled_notional_total: float = 0.0
    trader_fee_paid_total: float = 0.0
    protocol_fee_earned_total: float = 0.0
    active_lp_fee_earned_total: float = 0.0
    maker_rebate_earned_total: float = 0.0
    execution_shortfall_total: float = 0.0
    all_in_trader_cost_total: float = 0.0
    v3_min_order_ineligible_rows: int = 0

    def add(self, observation: FeeObservation) -> None:
        self.row_count += 1
        self.requested_notional_raw_total += observation.requested_notional_raw
        self.fee_basis_filled_notional_total += observation.fee_basis_filled_notional_usd
        self.trader_fee_paid_total += observation.trader_fee_paid_usd
        self.protocol_fee_earned_total += observation.protocol_fee_earned_usd
        self.active_lp_fee_earned_total += observation.active_lp_fee_earned_usd
        self.maker_rebate_earned_total += observation.maker_rebate_earned_usd
        self.execution_shortfall_total += observation.execution_shortfall_usd
        self.all_in_trader_cost_total += observation.all_in_trader_cost_usd
        if observation.v3_min_order_ineligible:
            self.v3_min_order_ineligible_rows += 1

    def finalize(self) -> FeeRollupSummary:
        return FeeRollupSummary(
            row_count=self.row_count,
            requested_notional_raw_total=self.requested_notional_raw_total,
            fee_basis_filled_notional_total=self.fee_basis_filled_notional_total,
            trader_fee_paid_total=self.trader_fee_paid_total,
            protocol_fee_earned_total=self.protocol_fee_earned_total,
            active_lp_fee_earned_total=self.active_lp_fee_earned_total,
            maker_rebate_earned_total=self.maker_rebate_earned_total,
            execution_shortfall_total=self.execution_shortfall_total,
            all_in_trader_cost_total=self.all_in_trader_cost_total,
            v3_min_order_ineligible_rows=self.v3_min_order_ineligible_rows,
        )


def roll_up_fee_observations(
    observations: Iterable[FeeObservation],
    *,
    bucket_label: Callable[[FeeObservation], str] | None = None,
) -> tuple[FeeRollupSummary, dict[str, FeeRollupSummary], dict[str, FeeRollupSummary]]:
    aggregate = _FeeRollupAccumulator()
    by_side: dict[str, _FeeRollupAccumulator] = {}
    by_bucket: dict[str, _FeeRollupAccumulator] = {}

    for observation in observations:
        aggregate.add(observation)

        side_accumulator = by_side.setdefault(observation.side, _FeeRollupAccumulator())
        side_accumulator.add(observation)

        if bucket_label is not None:
            label = bucket_label(observation)
            bucket_accumulator = by_bucket.setdefault(label, _FeeRollupAccumulator())
            bucket_accumulator.add(observation)

    return (
        aggregate.finalize(),
        {key: value.finalize() for key, value in by_side.items()},
        {key: value.finalize() for key, value in by_bucket.items()},
    )


def execution_shortfall_usd(
    *,
    side: str,
    reference_price: float,
    filled_size: float,
    filled_notional: float,
) -> float:
    reference_notional = reference_price * filled_size
    if side == 'buy':
        return filled_notional - reference_notional
    if side == 'sell':
        return reference_notional - filled_notional
    raise ValueError(f'Unsupported side: {side}')


def fee_rollup_from_summary_payload(
    *,
    row_count: int,
    requested_notional_raw_total: int,
    execution_shortfall_total: float,
    v3_min_order_ineligible_rows: int,
    payload: dict[str, str | float | int],
) -> FeeRollupSummary:
    trader_fee_paid_total = parse_float(str(payload.get('trader_fee_paid_usd', '0')))
    return FeeRollupSummary(
        row_count=row_count,
        requested_notional_raw_total=requested_notional_raw_total,
        fee_basis_filled_notional_total=parse_float(str(payload.get('fee_basis_filled_notional_usd', '0'))),
        trader_fee_paid_total=trader_fee_paid_total,
        protocol_fee_earned_total=parse_float(str(payload.get('protocol_fee_earned_usd', '0'))),
        active_lp_fee_earned_total=parse_float(str(payload.get('active_lp_fee_earned_usd', '0'))),
        maker_rebate_earned_total=parse_float(str(payload.get('maker_rebate_earned_usd', '0'))),
        execution_shortfall_total=execution_shortfall_total,
        all_in_trader_cost_total=execution_shortfall_total + trader_fee_paid_total,
        v3_min_order_ineligible_rows=v3_min_order_ineligible_rows,
    )


def fee_observation_from_row(row: dict[str, str]) -> FeeObservation:
    trader_fee_paid_usd = parse_float(row.get('trader_fee_paid_usd', '0') or '0')
    execution_shortfall = execution_shortfall_usd(
        side=row['side'],
        reference_price=parse_float(row['reference_price']),
        filled_size=parse_float(row['filled_size']),
        filled_notional=parse_float(row['filled_notional']),
    )
    return FeeObservation(
        lane=row['lane'],
        side=row['side'],
        requested_notional=parse_float(row['requested_notional']),
        requested_notional_raw=parse_int(row['baseVolumeRaw']),
        fee_basis_filled_notional_usd=parse_float(row.get('fee_basis_filled_notional_usd', '0') or '0'),
        trader_fee_paid_usd=trader_fee_paid_usd,
        protocol_fee_earned_usd=parse_float(row.get('protocol_fee_earned_usd', '0') or '0'),
        active_lp_fee_earned_usd=parse_float(row.get('active_lp_fee_earned_usd', '0') or '0'),
        maker_rebate_earned_usd=parse_float(row.get('maker_rebate_earned_usd', '0') or '0'),
        execution_shortfall_usd=execution_shortfall,
        all_in_trader_cost_usd=execution_shortfall + trader_fee_paid_usd,
        v3_min_order_ineligible=parse_bool_text_relaxed(row.get('v3_min_order_ineligible')),
    )


def parse_bool_text_relaxed(value: str | None) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes'}:
        return True
    if text in {'false', '0', 'no', ''}:
        return False
    raise ValueError(f'Unsupported boolean text: {value!r}')


def approximately_matches_fee_rollup(
    actual: FeeRollupSummary,
    expected: FeeRollupSummary,
    *,
    tolerance: float = 1e-6,
) -> bool:
    if actual.row_count != expected.row_count:
        return False
    if actual.requested_notional_raw_total != expected.requested_notional_raw_total:
        return False
    if actual.v3_min_order_ineligible_rows != expected.v3_min_order_ineligible_rows:
        return False
    return all(
        math.isclose(a, b, rel_tol=1e-12, abs_tol=tolerance)
        for a, b in (
            (actual.fee_basis_filled_notional_total, expected.fee_basis_filled_notional_total),
            (actual.trader_fee_paid_total, expected.trader_fee_paid_total),
            (actual.protocol_fee_earned_total, expected.protocol_fee_earned_total),
            (actual.active_lp_fee_earned_total, expected.active_lp_fee_earned_total),
            (actual.maker_rebate_earned_total, expected.maker_rebate_earned_total),
            (actual.execution_shortfall_total, expected.execution_shortfall_total),
            (actual.all_in_trader_cost_total, expected.all_in_trader_cost_total),
        )
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..fees import bps
from ..normalize.events import parse_float, parse_int
from .spread_capture_views import gross_spread_capture_usd, resting_book_leg_from_row


V2_LANE = 'v2_realized'
V3_MAKER_LANES = {'3a_pure_book', '3b_hybrid'}
PROVIDER_ECON_LANES = {V2_LANE, *V3_MAKER_LANES}


@dataclass(frozen=True)
class ProviderEconomicsObservation:
    lane: str
    side: str
    requested_notional: float
    requested_notional_raw: int
    next_event_reference_available: bool
    lp_fee_accrual_usd: float
    lp_divergence_loss_proxy_usd: float
    lp_net_provider_economics_proxy_usd: float
    maker_rebate_usd: float
    resting_book_filled_size: float
    resting_book_filled_notional_usd: float
    gross_spread_capture_usd: float
    maker_markout_loss_proxy_usd: float
    maker_net_provider_economics_proxy_usd: float

    @property
    def explicit_protocol_transfer_usd(self) -> float:
        return self.lp_fee_accrual_usd + self.maker_rebate_usd

    @property
    def gross_provider_revenue_proxy_usd(self) -> float:
        return self.lp_fee_accrual_usd + self.maker_rebate_usd + self.gross_spread_capture_usd

    @property
    def net_provider_economics_proxy_usd(self) -> float:
        return self.lp_net_provider_economics_proxy_usd + self.maker_net_provider_economics_proxy_usd


@dataclass(frozen=True)
class ProviderEconomicsRollupSummary:
    row_count: int
    requested_notional_raw_total: int
    next_event_horizon_supported_rows: int
    next_event_horizon_unavailable_rows: int
    lp_fee_accrual_total: float
    lp_divergence_loss_proxy_total: float
    lp_net_provider_economics_proxy_total: float
    maker_rebate_total: float
    resting_book_filled_size_total: float
    resting_book_filled_notional_total: float
    gross_spread_capture_total: float
    maker_markout_loss_proxy_total: float
    maker_net_provider_economics_proxy_total: float

    @property
    def requested_notional_total(self) -> float:
        return self.requested_notional_raw_total / 1_000_000

    @property
    def explicit_protocol_transfer_total(self) -> float:
        return self.lp_fee_accrual_total + self.maker_rebate_total

    @property
    def gross_provider_revenue_proxy_total(self) -> float:
        return self.lp_fee_accrual_total + self.maker_rebate_total + self.gross_spread_capture_total

    @property
    def net_provider_economics_proxy_total(self) -> float:
        return self.lp_net_provider_economics_proxy_total + self.maker_net_provider_economics_proxy_total

    @property
    def explicit_protocol_transfer_bps_on_requested_notional(self) -> float:
        return bps(self.explicit_protocol_transfer_total, self.requested_notional_total)

    @property
    def gross_provider_revenue_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.gross_provider_revenue_proxy_total, self.requested_notional_total)

    @property
    def net_provider_economics_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.net_provider_economics_proxy_total, self.requested_notional_total)

    @property
    def lp_fee_accrual_bps_on_requested_notional(self) -> float:
        return bps(self.lp_fee_accrual_total, self.requested_notional_total)

    @property
    def lp_divergence_loss_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.lp_divergence_loss_proxy_total, self.requested_notional_total)

    @property
    def lp_net_provider_economics_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.lp_net_provider_economics_proxy_total, self.requested_notional_total)

    @property
    def maker_rebate_bps_on_requested_notional(self) -> float:
        return bps(self.maker_rebate_total, self.requested_notional_total)

    @property
    def gross_spread_capture_bps_on_requested_notional(self) -> float:
        return bps(self.gross_spread_capture_total, self.requested_notional_total)

    @property
    def gross_spread_capture_bps_on_resting_book_filled_notional(self) -> float:
        return bps(self.gross_spread_capture_total, self.resting_book_filled_notional_total)

    @property
    def maker_markout_loss_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.maker_markout_loss_proxy_total, self.requested_notional_total)

    @property
    def maker_markout_loss_proxy_bps_on_resting_book_filled_notional(self) -> float:
        return bps(self.maker_markout_loss_proxy_total, self.resting_book_filled_notional_total)

    @property
    def maker_net_provider_economics_proxy_bps_on_requested_notional(self) -> float:
        return bps(self.maker_net_provider_economics_proxy_total, self.requested_notional_total)

    @property
    def maker_net_provider_economics_proxy_bps_on_resting_book_filled_notional(self) -> float:
        return bps(self.maker_net_provider_economics_proxy_total, self.resting_book_filled_notional_total)


@dataclass
class _ProviderEconomicsRollupAccumulator:
    row_count: int = 0
    requested_notional_raw_total: int = 0
    next_event_horizon_supported_rows: int = 0
    next_event_horizon_unavailable_rows: int = 0
    lp_fee_accrual_total: float = 0.0
    lp_divergence_loss_proxy_total: float = 0.0
    lp_net_provider_economics_proxy_total: float = 0.0
    maker_rebate_total: float = 0.0
    resting_book_filled_size_total: float = 0.0
    resting_book_filled_notional_total: float = 0.0
    gross_spread_capture_total: float = 0.0
    maker_markout_loss_proxy_total: float = 0.0
    maker_net_provider_economics_proxy_total: float = 0.0

    def add(self, observation: ProviderEconomicsObservation) -> None:
        self.row_count += 1
        self.requested_notional_raw_total += observation.requested_notional_raw
        if observation.next_event_reference_available:
            self.next_event_horizon_supported_rows += 1
        else:
            self.next_event_horizon_unavailable_rows += 1
        self.lp_fee_accrual_total += observation.lp_fee_accrual_usd
        self.lp_divergence_loss_proxy_total += observation.lp_divergence_loss_proxy_usd
        self.lp_net_provider_economics_proxy_total += observation.lp_net_provider_economics_proxy_usd
        self.maker_rebate_total += observation.maker_rebate_usd
        self.resting_book_filled_size_total += observation.resting_book_filled_size
        self.resting_book_filled_notional_total += observation.resting_book_filled_notional_usd
        self.gross_spread_capture_total += observation.gross_spread_capture_usd
        self.maker_markout_loss_proxy_total += observation.maker_markout_loss_proxy_usd
        self.maker_net_provider_economics_proxy_total += observation.maker_net_provider_economics_proxy_usd

    def finalize(self) -> ProviderEconomicsRollupSummary:
        return ProviderEconomicsRollupSummary(
            row_count=self.row_count,
            requested_notional_raw_total=self.requested_notional_raw_total,
            next_event_horizon_supported_rows=self.next_event_horizon_supported_rows,
            next_event_horizon_unavailable_rows=self.next_event_horizon_unavailable_rows,
            lp_fee_accrual_total=self.lp_fee_accrual_total,
            lp_divergence_loss_proxy_total=self.lp_divergence_loss_proxy_total,
            lp_net_provider_economics_proxy_total=self.lp_net_provider_economics_proxy_total,
            maker_rebate_total=self.maker_rebate_total,
            resting_book_filled_size_total=self.resting_book_filled_size_total,
            resting_book_filled_notional_total=self.resting_book_filled_notional_total,
            gross_spread_capture_total=self.gross_spread_capture_total,
            maker_markout_loss_proxy_total=self.maker_markout_loss_proxy_total,
            maker_net_provider_economics_proxy_total=self.maker_net_provider_economics_proxy_total,
        )


def adverse_reference_move_usd(
    *,
    side: str,
    current_reference_price: float,
    next_reference_price: float | None,
    filled_size: float,
) -> float:
    if next_reference_price is None or filled_size <= 0.0:
        return 0.0
    if side == 'buy':
        return max((next_reference_price - current_reference_price) * filled_size, 0.0)
    if side == 'sell':
        return max((current_reference_price - next_reference_price) * filled_size, 0.0)
    raise ValueError(f'Unsupported side: {side}')


def lp_lvr_loss_proxy_usd(
    *,
    side: str,
    filled_size: float,
    filled_notional: float,
    next_reference_price: float | None,
) -> float:
    if next_reference_price is None or filled_size <= 0.0:
        return 0.0
    next_reference_notional = next_reference_price * filled_size
    if side == 'buy':
        return max(next_reference_notional - filled_notional, 0.0)
    if side == 'sell':
        return max(filled_notional - next_reference_notional, 0.0)
    raise ValueError(f'Unsupported side: {side}')


def maker_markout_loss_proxy_usd(
    *,
    side: str,
    current_reference_price: float,
    next_reference_price: float | None,
    resting_book_filled_size: float,
) -> float:
    return adverse_reference_move_usd(
        side=side,
        current_reference_price=current_reference_price,
        next_reference_price=next_reference_price,
        filled_size=resting_book_filled_size,
    )


def lp_lvr_loss_proxy_from_row(row: dict[str, str], *, next_reference_price: float | None) -> float:
    lane = row['lane']
    if lane != V2_LANE:
        raise ValueError(f'Unsupported V2 provider-economics lane: {lane}')
    return lp_lvr_loss_proxy_usd(
        side=row['side'],
        filled_size=parse_float(row['filled_size']),
        filled_notional=parse_float(row['filled_notional']),
        next_reference_price=next_reference_price,
    )


def maker_markout_loss_proxy_from_row(row: dict[str, str], *, next_reference_price: float | None) -> float:
    lane = row['lane']
    if lane not in V3_MAKER_LANES:
        raise ValueError(f'Unsupported V3 maker provider-economics lane: {lane}')
    resting_book_filled_size, _ = resting_book_leg_from_row(row)
    return maker_markout_loss_proxy_usd(
        side=row['side'],
        current_reference_price=parse_float(row['reference_price']),
        next_reference_price=next_reference_price,
        resting_book_filled_size=resting_book_filled_size,
    )


def provider_economics_observation_from_row(
    row: dict[str, str],
    *,
    next_reference_price: float | None,
) -> ProviderEconomicsObservation:
    lane = row['lane']
    if lane == V2_LANE:
        lp_fee_accrual = parse_float(row.get('active_lp_fee_earned_usd', '0') or '0')
        lp_loss = lp_lvr_loss_proxy_from_row(row, next_reference_price=next_reference_price)
        return ProviderEconomicsObservation(
            lane=lane,
            side=row['side'],
            requested_notional=parse_float(row['requested_notional']),
            requested_notional_raw=parse_int(row['baseVolumeRaw']),
            next_event_reference_available=next_reference_price is not None,
            lp_fee_accrual_usd=lp_fee_accrual,
            lp_divergence_loss_proxy_usd=lp_loss,
            lp_net_provider_economics_proxy_usd=lp_fee_accrual - lp_loss,
            maker_rebate_usd=0.0,
            resting_book_filled_size=0.0,
            resting_book_filled_notional_usd=0.0,
            gross_spread_capture_usd=0.0,
            maker_markout_loss_proxy_usd=0.0,
            maker_net_provider_economics_proxy_usd=0.0,
        )

    if lane in V3_MAKER_LANES:
        resting_book_filled_size, resting_book_filled_notional = resting_book_leg_from_row(row)
        maker_rebate = parse_float(row.get('maker_rebate_earned_usd', '0') or '0')
        gross_spread_capture = gross_spread_capture_usd(
            side=row['side'],
            reference_price=parse_float(row['reference_price']),
            filled_size=resting_book_filled_size,
            filled_notional=resting_book_filled_notional,
        )
        maker_markout_loss = maker_markout_loss_proxy_usd(
            side=row['side'],
            current_reference_price=parse_float(row['reference_price']),
            next_reference_price=next_reference_price,
            resting_book_filled_size=resting_book_filled_size,
        )
        return ProviderEconomicsObservation(
            lane=lane,
            side=row['side'],
            requested_notional=parse_float(row['requested_notional']),
            requested_notional_raw=parse_int(row['baseVolumeRaw']),
            next_event_reference_available=next_reference_price is not None,
            lp_fee_accrual_usd=0.0,
            lp_divergence_loss_proxy_usd=0.0,
            lp_net_provider_economics_proxy_usd=0.0,
            maker_rebate_usd=maker_rebate,
            resting_book_filled_size=resting_book_filled_size,
            resting_book_filled_notional_usd=resting_book_filled_notional,
            gross_spread_capture_usd=gross_spread_capture,
            maker_markout_loss_proxy_usd=maker_markout_loss,
            maker_net_provider_economics_proxy_usd=gross_spread_capture + maker_rebate - maker_markout_loss,
        )

    raise ValueError(f'Unsupported provider-economics lane: {lane}')


def roll_up_provider_economics_observations(
    observations: Iterable[ProviderEconomicsObservation],
    *,
    bucket_label: Callable[[ProviderEconomicsObservation], str] | None = None,
) -> tuple[
    ProviderEconomicsRollupSummary,
    dict[str, ProviderEconomicsRollupSummary],
    dict[str, ProviderEconomicsRollupSummary],
]:
    aggregate = _ProviderEconomicsRollupAccumulator()
    by_side: dict[str, _ProviderEconomicsRollupAccumulator] = {}
    by_bucket: dict[str, _ProviderEconomicsRollupAccumulator] = {}

    for observation in observations:
        aggregate.add(observation)

        side_accumulator = by_side.setdefault(observation.side, _ProviderEconomicsRollupAccumulator())
        side_accumulator.add(observation)

        if bucket_label is not None:
            label = bucket_label(observation)
            bucket_accumulator = by_bucket.setdefault(label, _ProviderEconomicsRollupAccumulator())
            bucket_accumulator.add(observation)

    return (
        aggregate.finalize(),
        {key: value.finalize() for key, value in by_side.items()},
        {key: value.finalize() for key, value in by_bucket.items()},
    )

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..metrics.core import (
    completion_ratio,
    reconstruct_amm_pre_trade_spot_reference,
    slippage_bps,
    symmetric_reference_denominator_bps,
)
from ..normalize.events import (
    format_bool,
    format_decimal,
    format_scaled_int,
    parse_float,
    parse_int,
    parse_optional_float,
)
from ..schema import ExecutionRecord, ReplayUnit
from ..validation.reconcile import reconcile_totals

LANE_NAME = 'v2_realized'
REPLAY_UNITS_FILENAME = 'replay_units.csv'
NORMALIZED_EVENTS_FILENAME = 'normalized_events.csv'
LANE_OUTPUT_FILENAME = 'lane_v2_baseline.csv'
SUMMARY_FILENAME = 'v2_baseline_summary.json'
MANIFEST_FILENAME = 'v2_baseline_manifest.json'

BASELINE_OUTPUT_FIELDNAMES = [
    'lane',
    'replay_unit_id',
    'timestamp',
    'side',
    'requested_size',
    'requested_notional',
    'filled_size',
    'filled_notional',
    'completion_ratio',
    'reference_price',
    'amm_pre_trade_spot_reference_price',
    'avg_execution_price',
    'realized_slippage_bps',
    'amm_pre_trade_spot_gross_slippage_bps',
    'fees_paid',
    'fee_methodology',
    'fee_precision',
    'fee_covered',
    'remainder_size',
    'route_breakdown',
    'admissibility_passed',
    'tradeRowId',
    'swapEventId',
    'tradeTimestampSeconds',
    'source_ordering_key',
    'baseId',
    'targetId',
    'baseVolumeRaw',
    'targetVolumeRaw',
    'reference_price_source',
    'reference_price_fallback',
    'swap_metadata_covered',
]

FEE_METHODOLOGY = (
    'historical fee inputs are only available at pool/day coverage granularity in the current '
    'materialized dataset; the lane preserves fee coverage visibility but does not allocate '
    'unguarded per-replay-unit fees'
)
FEE_PRECISION = 'not_allocated_per_replay_unit'
FEE_CAVEAT = (
    'Per-replay-unit historical fees are not recoverable from the current Gigabrain fee inputs. '
    'Lane records set fees_paid to 0.0 and expose fee_covered/day-coverage visibility explicitly '
    'instead of silently imputing swap-level fees.'
)


class ReplayUnitMappingError(ValueError):
    pass


@dataclass(frozen=True)
class ObservedEventContext:
    replay_unit_id: str
    source_ordering_key: str
    observed_execution_price: float
    base_id: str
    target_id: str
    base_volume_raw: int
    target_volume_raw: int
    trade_row_id: int
    swap_event_id: str
    trade_timestamp_seconds: int
    reference_price_source: str
    reference_price_fallback: bool
    swap_metadata_covered: bool
    fee_covered: bool
    amount_a: float | None
    amount_b: float | None
    sqrt_ratio_x96: float | None
    liquidity: float | None


@dataclass(frozen=True)
class V2RealizedBuildResult:
    lane_output_path: Path
    summary_path: Path
    manifest_path: Path
    summary: dict[str, Any]
    manifest: dict[str, Any]


@dataclass
class BaselineStats:
    row_count: int = 0
    replay_projection_verified_rows: int = 0
    replay_projection_missing_tail_rows: int = 0
    buy_rows: int = 0
    sell_rows: int = 0
    requested_size_raw_total: int = 0
    requested_notional_raw_total: int = 0
    filled_size_raw_total: int = 0
    filled_notional_raw_total: int = 0
    full_fill_rows: int = 0
    partial_fill_rows: int = 0
    zero_fill_rows: int = 0
    completion_ratio_sum: float = 0.0
    fee_covered_rows: int = 0
    fee_missing_rows: int = 0
    precise_fee_rows: int = 0
    reference_price_fallback_rows: int = 0
    swap_metadata_covered_rows: int = 0
    swap_metadata_missing_rows: int = 0
    slippage_sum_bps: float = 0.0
    slippage_abs_sum_bps: float = 0.0
    finite_slippage_rows: int = 0
    infinite_slippage_rows: int = 0
    slippage_min_bps: float | None = None
    slippage_max_bps: float | None = None
    slippage_positive_rows: int = 0
    slippage_negative_rows: int = 0
    slippage_zero_rows: int = 0
    amm_pre_trade_spot_supported_rows: int = 0
    amm_pre_trade_spot_missing_rows: int = 0
    amm_pre_trade_spot_slippage_sum_bps: float = 0.0
    amm_pre_trade_spot_slippage_abs_sum_bps: float = 0.0
    amm_pre_trade_spot_finite_slippage_rows: int = 0
    amm_pre_trade_spot_infinite_slippage_rows: int = 0
    amm_pre_trade_spot_slippage_min_bps: float | None = None
    amm_pre_trade_spot_slippage_max_bps: float | None = None
    first_replay_unit_id: str | None = None
    last_replay_unit_id: str | None = None
    first_source_ordering_key: str | None = None
    last_source_ordering_key: str | None = None


@dataclass(frozen=True)
class BaselineRow:
    record: ExecutionRecord
    context: ObservedEventContext
    realized_slippage_bps: float
    amm_pre_trade_spot_reference_price: float | None
    amm_pre_trade_spot_gross_slippage_bps: float | None
    replay_projection_verified: bool = True


@dataclass(frozen=True)
class AlignmentState:
    replay_unit: ReplayUnit
    context: ObservedEventContext
    row_number: int
    replay_projection_verified: bool


def build_v2_realized_record(
    unit: ReplayUnit,
    execution_price: float,
    fees_paid: float = 0.0,
    *,
    filled_notional: float | None = None,
) -> ExecutionRecord:
    filled_size = unit.requested_size
    if filled_notional is None:
        filled_notional = unit.requested_notional
    return ExecutionRecord(
        lane=LANE_NAME,
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=filled_size,
        filled_notional=filled_notional,
        completion_ratio=completion_ratio(filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=execution_price,
        fees_paid=fees_paid,
        remainder_size=0.0,
        route_breakdown={'v2': filled_size},
        admissibility_passed=True,
    )


def build_baseline_row(
    unit: ReplayUnit,
    context: ObservedEventContext,
    *,
    replay_projection_verified: bool = True,
) -> BaselineRow:
    record = build_v2_realized_record(
        unit,
        execution_price=context.observed_execution_price,
        filled_notional=unit.requested_notional,
    )
    realized_slippage = slippage_bps(unit.reference_price, record.avg_execution_price, unit.side)
    amm_pre_trade_spot_reference = reconstruct_amm_pre_trade_spot_reference(
        side=unit.side,
        sqrt_ratio_x96=context.sqrt_ratio_x96,
        liquidity=context.liquidity,
        amount_a=context.amount_a,
        amount_b=context.amount_b,
    )
    amm_pre_trade_spot_gross_slippage = None
    if amm_pre_trade_spot_reference is not None:
        amm_pre_trade_spot_gross_slippage = symmetric_reference_denominator_bps(
            amm_pre_trade_spot_reference.pre_trade_spot_price,
            record.avg_execution_price,
            unit.side,
        )
    return BaselineRow(
        record=record,
        context=context,
        realized_slippage_bps=realized_slippage,
        amm_pre_trade_spot_reference_price=(
            None if amm_pre_trade_spot_reference is None else amm_pre_trade_spot_reference.pre_trade_spot_price
        ),
        amm_pre_trade_spot_gross_slippage_bps=amm_pre_trade_spot_gross_slippage,
        replay_projection_verified=replay_projection_verified,
    )


def run_v2_realized_baseline(root: str | Path) -> V2RealizedBuildResult:
    repo_root = Path(root).resolve()
    interim_dir = repo_root / 'data' / 'interim'
    replay_units_path = interim_dir / REPLAY_UNITS_FILENAME
    normalized_events_path = interim_dir / NORMALIZED_EVENTS_FILENAME
    _require_inputs([replay_units_path, normalized_events_path])

    processed_dir = repo_root / 'data' / 'processed'
    processed_dir.mkdir(parents=True, exist_ok=True)
    lane_output_path = processed_dir / LANE_OUTPUT_FILENAME
    summary_path = processed_dir / SUMMARY_FILENAME
    manifest_path = processed_dir / MANIFEST_FILENAME

    stats = BaselineStats()
    mapping_fingerprint = hashlib.sha256()

    with lane_output_path.open('w', encoding='utf-8', newline='') as lane_handle:
        writer = csv.DictWriter(lane_handle, fieldnames=BASELINE_OUTPUT_FIELDNAMES)
        writer.writeheader()
        for aligned in iter_aligned_event_rows(replay_units_path, normalized_events_path):
            baseline_row = build_baseline_row(
                aligned.replay_unit,
                aligned.context,
                replay_projection_verified=aligned.replay_projection_verified,
            )
            writer.writerow(render_baseline_row(baseline_row))
            update_stats(stats, baseline_row)
            mapping_fingerprint.update(
                (
                    f'{aligned.context.source_ordering_key}|{aligned.replay_unit.replay_unit_id}|'
                    f'{aligned.context.trade_row_id}|{aligned.context.swap_event_id}\n'
                ).encode('utf-8')
            )

    summary = build_summary(
        replay_units_path=replay_units_path,
        normalized_events_path=normalized_events_path,
        lane_output_path=lane_output_path,
        stats=stats,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )
    manifest = build_manifest(
        replay_units_path=replay_units_path,
        normalized_events_path=normalized_events_path,
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        stats=stats,
        summary=summary,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )

    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return V2RealizedBuildResult(
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
        summary=summary,
        manifest=manifest,
    )


def iter_aligned_event_rows(
    replay_units_path: str | Path,
    normalized_events_path: str | Path,
) -> Iterator[AlignmentState]:
    replay_path = Path(replay_units_path)
    normalized_path = Path(normalized_events_path)
    with replay_path.open('r', encoding='utf-8', newline='') as replay_handle, normalized_path.open(
        'r', encoding='utf-8', newline=''
    ) as normalized_handle:
        replay_reader = csv.DictReader(replay_handle)
        normalized_reader = csv.DictReader(normalized_handle)
        replay_exhausted = False

        for row_number, normalized_row in enumerate(normalized_reader, start=1):
            context = observed_event_context_from_row(normalized_row)
            normalized_unit = replay_unit_from_normalized_row(normalized_row)
            replay_projection_verified = False

            if not replay_exhausted:
                replay_row = next(replay_reader, None)
                if replay_row is None:
                    replay_exhausted = True
                else:
                    replay_unit = replay_unit_from_row(replay_row)
                    _assert_aligned(replay_unit, context, row_number=row_number)
                    _assert_projection_matches(replay_unit, normalized_unit, row_number=row_number)
                    replay_projection_verified = True

            yield AlignmentState(
                replay_unit=normalized_unit,
                context=context,
                row_number=row_number,
                replay_projection_verified=replay_projection_verified,
            )

        trailing_replay_row = next(replay_reader, None)
        if trailing_replay_row is not None:
            raise ReplayUnitMappingError(
                'Replay-unit projection has extra rows beyond normalized_events.csv; '
                'baseline requires normalized event rows for observed execution context'
            )


def replay_unit_from_row(row: dict[str, str]) -> ReplayUnit:
    return ReplayUnit(
        replay_unit_id=row['replay_unit_id'],
        timestamp=row['timestamp'],
        tx_id=row['tx_id'],
        event_index=parse_int(row['event_index']),
        side=row['side'],
        requested_size=parse_float(row['requested_size']),
        requested_notional=parse_float(row['requested_notional']),
        reference_price=parse_float(row['reference_price']),
        trade_row_id=parse_int(row['tradeRowId']),
        swap_event_id=row['swapEventId'],
        trade_timestamp_seconds=parse_int(row['tradeTimestampSeconds']),
        reference_price_source=row.get('reference_price_source') or None,
        reference_price_fallback=parse_bool_text(row.get('reference_price_fallback')),
        swap_metadata_covered=parse_bool_text(row.get('swap_metadata_covered')),
        fee_covered=parse_bool_text(row.get('fee_covered')),
    )


def replay_unit_from_normalized_row(row: dict[str, str]) -> ReplayUnit:
    return ReplayUnit(
        replay_unit_id=row['replay_unit_id'],
        timestamp=row['timestamp'],
        tx_id=row['swapEventId'],
        event_index=parse_int(row['tradeRowId']),
        side=row['side'],
        requested_size=parse_float(row['requested_size']),
        requested_notional=parse_float(row['requested_notional']),
        reference_price=parse_float(row['reference_price']),
        trade_row_id=parse_int(row['tradeRowId']),
        swap_event_id=row['swapEventId'],
        trade_timestamp_seconds=parse_int(row['tradeTimestampSeconds']),
        reference_price_source=row.get('reference_price_source') or None,
        reference_price_fallback=parse_bool_text(row.get('reference_price_fallback')),
        swap_metadata_covered=parse_bool_text(row.get('swap_metadata_covered')),
        fee_covered=parse_bool_text(row.get('fee_covered')),
    )


def observed_event_context_from_row(row: dict[str, str]) -> ObservedEventContext:
    return ObservedEventContext(
        replay_unit_id=row['replay_unit_id'],
        source_ordering_key=row['source_ordering_key'],
        observed_execution_price=parse_float(row['observed_execution_price']),
        base_id=row['baseId'],
        target_id=row['targetId'],
        base_volume_raw=parse_int(row['baseVolumeRaw']),
        target_volume_raw=parse_int(row['targetVolumeRaw']),
        trade_row_id=parse_int(row['tradeRowId']),
        swap_event_id=row['swapEventId'],
        trade_timestamp_seconds=parse_int(row['tradeTimestampSeconds']),
        reference_price_source=row['reference_price_source'],
        reference_price_fallback=parse_bool_text(row['reference_price_fallback']),
        swap_metadata_covered=parse_bool_text(row['swap_metadata_covered']),
        fee_covered=parse_bool_text(row['fee_covered']),
        amount_a=parse_optional_float(row.get('amountA')),
        amount_b=parse_optional_float(row.get('amountB')),
        sqrt_ratio_x96=parse_optional_float(row.get('sqrtRatioX96')),
        liquidity=parse_optional_float(row.get('liquidity')),
    )


def render_baseline_row(row: BaselineRow) -> dict[str, str]:
    record = row.record
    context = row.context
    return {
        'lane': record.lane,
        'replay_unit_id': record.replay_unit_id,
        'timestamp': context_to_timestamp(context),
        'side': record.side,
        'requested_size': format_decimal(record.requested_size),
        'requested_notional': format_decimal(record.requested_notional),
        'filled_size': format_decimal(record.filled_size),
        'filled_notional': format_decimal(record.filled_notional),
        'completion_ratio': format_decimal(record.completion_ratio),
        'reference_price': format_decimal(record.reference_price),
        'amm_pre_trade_spot_reference_price': format_optional_decimal(row.amm_pre_trade_spot_reference_price),
        'avg_execution_price': format_decimal(record.avg_execution_price),
        'realized_slippage_bps': format_decimal(row.realized_slippage_bps),
        'amm_pre_trade_spot_gross_slippage_bps': format_optional_decimal(row.amm_pre_trade_spot_gross_slippage_bps),
        'fees_paid': format_decimal(record.fees_paid),
        'fee_methodology': FEE_METHODOLOGY,
        'fee_precision': FEE_PRECISION,
        'fee_covered': format_bool(context.fee_covered),
        'remainder_size': format_decimal(record.remainder_size),
        'route_breakdown': json.dumps(record.route_breakdown, sort_keys=True),
        'admissibility_passed': format_bool(bool(record.admissibility_passed)),
        'tradeRowId': str(context.trade_row_id),
        'swapEventId': context.swap_event_id,
        'tradeTimestampSeconds': str(context.trade_timestamp_seconds),
        'source_ordering_key': context.source_ordering_key,
        'baseId': context.base_id,
        'targetId': context.target_id,
        'baseVolumeRaw': str(context.base_volume_raw),
        'targetVolumeRaw': str(context.target_volume_raw),
        'reference_price_source': context.reference_price_source,
        'reference_price_fallback': format_bool(context.reference_price_fallback),
        'swap_metadata_covered': format_bool(context.swap_metadata_covered),
    }


def update_stats(stats: BaselineStats, row: BaselineRow) -> None:
    record = row.record
    context = row.context
    stats.row_count += 1
    if stats.first_replay_unit_id is None:
        stats.first_replay_unit_id = record.replay_unit_id
    stats.last_replay_unit_id = record.replay_unit_id
    if stats.first_source_ordering_key is None:
        stats.first_source_ordering_key = context.source_ordering_key
    stats.last_source_ordering_key = context.source_ordering_key

    if row.replay_projection_verified:
        stats.replay_projection_verified_rows += 1
    else:
        stats.replay_projection_missing_tail_rows += 1

    if record.side == 'buy':
        stats.buy_rows += 1
    elif record.side == 'sell':
        stats.sell_rows += 1

    stats.requested_size_raw_total += context.target_volume_raw
    stats.requested_notional_raw_total += context.base_volume_raw
    stats.filled_size_raw_total += context.target_volume_raw
    stats.filled_notional_raw_total += context.base_volume_raw

    if record.filled_size <= 0:
        stats.zero_fill_rows += 1
    elif record.completion_ratio >= 1.0:
        stats.full_fill_rows += 1
    else:
        stats.partial_fill_rows += 1
    stats.completion_ratio_sum += record.completion_ratio

    if context.fee_covered:
        stats.fee_covered_rows += 1
    else:
        stats.fee_missing_rows += 1

    if context.reference_price_fallback:
        stats.reference_price_fallback_rows += 1

    if context.swap_metadata_covered:
        stats.swap_metadata_covered_rows += 1
    else:
        stats.swap_metadata_missing_rows += 1

    if row.realized_slippage_bps > 0:
        stats.slippage_positive_rows += 1
    elif row.realized_slippage_bps < 0:
        stats.slippage_negative_rows += 1
    else:
        stats.slippage_zero_rows += 1

    if math.isfinite(row.realized_slippage_bps):
        stats.finite_slippage_rows += 1
        stats.slippage_sum_bps += row.realized_slippage_bps
        stats.slippage_abs_sum_bps += abs(row.realized_slippage_bps)
        if stats.slippage_min_bps is None or row.realized_slippage_bps < stats.slippage_min_bps:
            stats.slippage_min_bps = row.realized_slippage_bps
        if stats.slippage_max_bps is None or row.realized_slippage_bps > stats.slippage_max_bps:
            stats.slippage_max_bps = row.realized_slippage_bps
    else:
        stats.infinite_slippage_rows += 1

    if row.amm_pre_trade_spot_reference_price is None or row.amm_pre_trade_spot_gross_slippage_bps is None:
        stats.amm_pre_trade_spot_missing_rows += 1
        return

    stats.amm_pre_trade_spot_supported_rows += 1
    if math.isfinite(row.amm_pre_trade_spot_gross_slippage_bps):
        stats.amm_pre_trade_spot_finite_slippage_rows += 1
        stats.amm_pre_trade_spot_slippage_sum_bps += row.amm_pre_trade_spot_gross_slippage_bps
        stats.amm_pre_trade_spot_slippage_abs_sum_bps += abs(row.amm_pre_trade_spot_gross_slippage_bps)
        if (
            stats.amm_pre_trade_spot_slippage_min_bps is None
            or row.amm_pre_trade_spot_gross_slippage_bps < stats.amm_pre_trade_spot_slippage_min_bps
        ):
            stats.amm_pre_trade_spot_slippage_min_bps = row.amm_pre_trade_spot_gross_slippage_bps
        if (
            stats.amm_pre_trade_spot_slippage_max_bps is None
            or row.amm_pre_trade_spot_gross_slippage_bps > stats.amm_pre_trade_spot_slippage_max_bps
        ):
            stats.amm_pre_trade_spot_slippage_max_bps = row.amm_pre_trade_spot_gross_slippage_bps
    else:
        stats.amm_pre_trade_spot_infinite_slippage_rows += 1


def build_summary(
    *,
    replay_units_path: Path,
    normalized_events_path: Path,
    lane_output_path: Path,
    stats: BaselineStats,
    mapping_fingerprint: str,
) -> dict[str, Any]:
    counts_reconciliation = reconcile_totals(stats.row_count, stats.row_count)
    summary = {
        'generated_at_utc': utc_now(),
        'lane': LANE_NAME,
        'contract': {
            'baseline_mode': 'event_level_realized_v2',
            'replay_unit_mapping': 'one_replay_unit_to_one_baseline_record',
            'canonical_ordering': ['tradeTimestampSeconds', 'swapEventId', 'tradeRowId'],
            'slippage_basis': 'reference_price',
            'lambdaplex_parity_proxy_basis': (
                'amm_pre_trade_spot_gross_slippage_bps uses the RH-13 best-supported '
                'AMM pre-trade pool-spot gross convention with a symmetric reference denominator'
            ),
            'completion_basis': 'event_level_realized_unit',
            'fee_treatment': 'flag_and_continue_when_per_swap_fees_are_not_grounded',
        },
        'inputs': {
            'replay_units_path': str(replay_units_path),
            'normalized_events_path': str(normalized_events_path),
        },
        'outputs': {
            'lane_output_path': str(lane_output_path),
        },
        'row_counts': {
            'normalized_event_rows': stats.row_count,
            'baseline_rows': stats.row_count,
            'replay_projection_verified_rows': stats.replay_projection_verified_rows,
            'replay_projection_missing_tail_rows': stats.replay_projection_missing_tail_rows,
            'buy_rows': stats.buy_rows,
            'sell_rows': stats.sell_rows,
        },
        'completion': {
            'full_fill_rows': stats.full_fill_rows,
            'partial_fill_rows': stats.partial_fill_rows,
            'zero_fill_rows': stats.zero_fill_rows,
            'avg_completion_ratio': average(stats.completion_ratio_sum, stats.row_count),
        },
        'slippage_bps': {
            'avg': average(stats.slippage_sum_bps, stats.finite_slippage_rows),
            'avg_abs': average(stats.slippage_abs_sum_bps, stats.finite_slippage_rows),
            'min': round(stats.slippage_min_bps or 0.0, 12),
            'max': round(stats.slippage_max_bps or 0.0, 12),
            'finite_rows': stats.finite_slippage_rows,
            'infinite_rows': stats.infinite_slippage_rows,
            'positive_rows': stats.slippage_positive_rows,
            'negative_rows': stats.slippage_negative_rows,
            'zero_rows': stats.slippage_zero_rows,
        },
        'amm_pre_trade_spot_gross_slippage_bps': {
            'avg': average(stats.amm_pre_trade_spot_slippage_sum_bps, stats.amm_pre_trade_spot_finite_slippage_rows),
            'avg_abs': average(
                stats.amm_pre_trade_spot_slippage_abs_sum_bps,
                stats.amm_pre_trade_spot_finite_slippage_rows,
            ),
            'min': round(stats.amm_pre_trade_spot_slippage_min_bps or 0.0, 12),
            'max': round(stats.amm_pre_trade_spot_slippage_max_bps or 0.0, 12),
            'finite_rows': stats.amm_pre_trade_spot_finite_slippage_rows,
            'infinite_rows': stats.amm_pre_trade_spot_infinite_slippage_rows,
            'supported_rows': stats.amm_pre_trade_spot_supported_rows,
            'missing_rows': stats.amm_pre_trade_spot_missing_rows,
            'reference_basis': 'reconstructed_amm_pre_trade_pool_spot',
            'execution_basis': 'gross_lane_avg_execution_price',
            'denominator': 'symmetric_reference_price',
            'status': 'parity_proxy_only',
        },
        'totals': {
            'requested_size_hbar': format_scaled_int(stats.requested_size_raw_total, 8),
            'requested_notional_usdc': format_scaled_int(stats.requested_notional_raw_total, 6),
            'filled_size_hbar': format_scaled_int(stats.filled_size_raw_total, 8),
            'filled_notional_usdc': format_scaled_int(stats.filled_notional_raw_total, 6),
        },
        'coverage': {
            'reference_price_fallback_rows': stats.reference_price_fallback_rows,
            'swap_metadata_covered_rows': stats.swap_metadata_covered_rows,
            'swap_metadata_missing_rows': stats.swap_metadata_missing_rows,
            'amm_pre_trade_spot_reference_supported_rows': stats.amm_pre_trade_spot_supported_rows,
            'amm_pre_trade_spot_reference_missing_rows': stats.amm_pre_trade_spot_missing_rows,
        },
        'fees': {
            'fee_methodology': FEE_METHODOLOGY,
            'fee_precision': FEE_PRECISION,
            'fee_covered_rows': stats.fee_covered_rows,
            'fee_missing_rows': stats.fee_missing_rows,
            'precise_fee_rows': stats.precise_fee_rows,
            'caveat': FEE_CAVEAT,
        },
        'mapping': {
            'first_replay_unit_id': stats.first_replay_unit_id,
            'last_replay_unit_id': stats.last_replay_unit_id,
            'first_source_ordering_key': stats.first_source_ordering_key,
            'last_source_ordering_key': stats.last_source_ordering_key,
            'fingerprint': mapping_fingerprint,
            'replay_projection_complete': stats.replay_projection_missing_tail_rows == 0,
            'replay_projection_verified_rows': stats.replay_projection_verified_rows,
            'replay_projection_missing_tail_rows': stats.replay_projection_missing_tail_rows,
        },
        'reconciliation': {
            **counts_reconciliation,
            'baseline_count': stats.row_count,
            'requested_size_matches_filled_size': stats.requested_size_raw_total == stats.filled_size_raw_total,
            'requested_notional_matches_filled_notional': stats.requested_notional_raw_total
            == stats.filled_notional_raw_total,
            'replay_projection_complete': stats.replay_projection_missing_tail_rows == 0,
        },
        'caveats': build_caveats(stats),
    }
    return summary


def build_manifest(
    *,
    replay_units_path: Path,
    normalized_events_path: Path,
    lane_output_path: Path,
    summary_path: Path,
    stats: BaselineStats,
    summary: dict[str, Any],
    mapping_fingerprint: str,
) -> dict[str, Any]:
    return {
        'generated_at_utc': utc_now(),
        'lane': LANE_NAME,
        'contract': summary['contract'],
        'inputs': {
            'replay_units_path': str(replay_units_path),
            'replay_units_bytes': replay_units_path.stat().st_size,
            'normalized_events_path': str(normalized_events_path),
            'normalized_events_bytes': normalized_events_path.stat().st_size,
        },
        'outputs': {
            'lane_output_path': str(lane_output_path),
            'lane_output_bytes': lane_output_path.stat().st_size,
            'summary_path': str(summary_path),
            'summary_bytes': len(json.dumps(summary, indent=2).encode('utf-8')) + 1,
            'manifest_path': str(lane_output_path.with_name(MANIFEST_FILENAME)),
        },
        'row_counts': summary['row_counts'],
        'mapping': {
            'fingerprint': mapping_fingerprint,
            'one_to_one_mapping_verified': True,
            'row_count': stats.row_count,
            'replay_projection_complete': stats.replay_projection_missing_tail_rows == 0,
            'replay_projection_verified_rows': stats.replay_projection_verified_rows,
            'replay_projection_missing_tail_rows': stats.replay_projection_missing_tail_rows,
        },
        'reconciliation': summary['reconciliation'],
        'fees': summary['fees'],
        'caveats': build_caveats(stats),
    }


def build_caveats(stats: BaselineStats) -> list[str]:
    caveats = [
        FEE_CAVEAT,
        'Completion is 1.0 by contract for the realized event-level unit because one normalized '
        'replay unit is one observed realized trade row.',
    ]
    if stats.replay_projection_missing_tail_rows > 0:
        caveats.append(
            f'The materialized replay_units.csv projection ends {stats.replay_projection_missing_tail_rows} '
            'row(s) before normalized_events.csv. The baseline therefore derives the missing tail '
            'replay-unit records directly from normalized event rows while preserving replay_unit_id '
            'and source anchors, and records the projection gap explicitly in the manifest.'
        )
    if stats.infinite_slippage_rows > 0:
        caveats.append(
            f'{stats.infinite_slippage_rows} replay unit(s) have non-finite slippage because the '
            'observed execution price is zero while reference_price is positive. These rows are '
            'preserved in the lane output and excluded from finite slippage averages.'
        )
    caveats.append(
        'The added `amm_pre_trade_spot_gross_slippage_bps` field is a Lambdaplex-parity proxy only. '
        'It uses the RH-13 best-supported reconstructed AMM pre-trade pool spot plus a symmetric '
        'reference denominator and does not replace the canonical reference-price study metric.'
    )
    if stats.amm_pre_trade_spot_missing_rows > 0:
        caveats.append(
            f'{stats.amm_pre_trade_spot_missing_rows} replay unit(s) do not have enough raw swap-state '
            'fields to support the AMM pre-trade spot parity proxy and remain blank for that metric family.'
        )
    return caveats


def average(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 12)


def format_optional_decimal(value: float | None, places: int = 12) -> str:
    if value is None:
        return ''
    return format_decimal(value, places=places)


def parse_bool_text(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    text = '' if value is None else str(value).strip().lower()
    if text in {'true', '1', 'yes'}:
        return True
    if text in {'false', '0', 'no', ''}:
        return False
    raise ValueError(f'Unsupported boolean text: {value!r}')


def context_to_timestamp(context: ObservedEventContext) -> str:
    return datetime.fromtimestamp(context.trade_timestamp_seconds, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _assert_aligned(replay_unit: ReplayUnit, context: ObservedEventContext, *, row_number: int) -> None:
    if replay_unit.replay_unit_id != context.replay_unit_id:
        raise ReplayUnitMappingError(
            f'Replay-unit id mismatch at row {row_number}: '
            f'{replay_unit.replay_unit_id} != {context.replay_unit_id}'
        )
    if replay_unit.trade_row_id != context.trade_row_id:
        raise ReplayUnitMappingError(
            f'tradeRowId mismatch at row {row_number}: {replay_unit.trade_row_id} != {context.trade_row_id}'
        )
    if replay_unit.swap_event_id != context.swap_event_id:
        raise ReplayUnitMappingError(
            f'swapEventId mismatch at row {row_number}: {replay_unit.swap_event_id} != {context.swap_event_id}'
        )
    if replay_unit.trade_timestamp_seconds != context.trade_timestamp_seconds:
        raise ReplayUnitMappingError(
            'tradeTimestampSeconds mismatch at row '
            f'{row_number}: {replay_unit.trade_timestamp_seconds} != {context.trade_timestamp_seconds}'
        )


def _assert_projection_matches(replay_unit: ReplayUnit, normalized_unit: ReplayUnit, *, row_number: int) -> None:
    if replay_unit.side != normalized_unit.side:
        raise ReplayUnitMappingError(
            f'side mismatch at row {row_number}: {replay_unit.side} != {normalized_unit.side}'
        )
    if replay_unit.requested_size != normalized_unit.requested_size:
        raise ReplayUnitMappingError(
            'requested_size mismatch at row '
            f'{row_number}: {replay_unit.requested_size} != {normalized_unit.requested_size}'
        )
    if replay_unit.requested_notional != normalized_unit.requested_notional:
        raise ReplayUnitMappingError(
            'requested_notional mismatch at row '
            f'{row_number}: {replay_unit.requested_notional} != {normalized_unit.requested_notional}'
        )
    if replay_unit.reference_price != normalized_unit.reference_price:
        raise ReplayUnitMappingError(
            'reference_price mismatch at row '
            f'{row_number}: {replay_unit.reference_price} != {normalized_unit.reference_price}'
        )


def _require_inputs(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing V2 realized baseline inputs: {", ".join(missing)}')

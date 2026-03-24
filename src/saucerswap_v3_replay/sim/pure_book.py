from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from ..baseline.v2_realized import (
    ObservedEventContext,
    _require_inputs,
    average,
    context_to_timestamp,
    iter_aligned_event_rows,
    utc_now,
)
from ..metrics.core import completion_ratio, slippage_bps
from ..normalize.events import format_bool, format_decimal, format_scaled_int
from ..schema import ExecutionRecord, ReplayUnit
from ..settings import _load_yaml_payload
from ..validation.reconcile import reconcile_totals
from .book_profile import BookLevel, BookProfile, load_book_profile

LANE_NAME = '3a_pure_book'
REPLAY_UNITS_FILENAME = 'replay_units.csv'
NORMALIZED_EVENTS_FILENAME = 'normalized_events.csv'
BOOK_CONFIG_FILENAME = 'lambdaplex_book.yaml'
FEE_CONFIG_FILENAME = 'fees.yaml'
LANE_OUTPUT_FILENAME = 'lane_3a_pure_book.csv'
SUMMARY_FILENAME = 'pure_book_summary.json'
MANIFEST_FILENAME = 'pure_book_manifest.json'
OVERFILL_TOLERANCE = 1e-9

PURE_BOOK_OUTPUT_FIELDNAMES = [
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
    'avg_execution_price',
    'execution_slippage_bps',
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
    'phase-0 fee policy keeps headline comparisons fee-aware, but 3A does not yet define a '
    'separate synthetic fee model; the lane records fees_paid as 0.0 and preserves RH-03 '
    'fee_covered visibility instead of inventing per-replay-unit fee precision'
)
FEE_PRECISION = 'no_synthetic_fee_model'
FEE_CAVEAT = (
    '3A has no separate synthetic fee model in the current Phase 0 config. Lane records set '
    'fees_paid to 0.0 and preserve fee_covered visibility from RH-03 instead of allocating '
    'unguarded synthetic per-replay-unit fees.'
)


@dataclass(frozen=True)
class SimulatedFill:
    filled_size: float
    filled_notional: float
    avg_execution_price: float
    remainder_size: float


@dataclass(frozen=True)
class PureBookRow:
    record: ExecutionRecord
    context: ObservedEventContext
    execution_slippage_bps: float
    replay_projection_verified: bool = True


@dataclass
class PureBookStats:
    row_count: int = 0
    replay_projection_verified_rows: int = 0
    replay_projection_missing_tail_rows: int = 0
    buy_rows: int = 0
    sell_rows: int = 0
    requested_size_raw_total: int = 0
    requested_notional_raw_total: int = 0
    requested_size_total: float = 0.0
    filled_size_total: float = 0.0
    filled_notional_total: float = 0.0
    remainder_size_total: float = 0.0
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
    slippage_excluded_zero_fill_rows: int = 0
    slippage_min_bps: float | None = None
    slippage_max_bps: float | None = None
    slippage_positive_rows: int = 0
    slippage_negative_rows: int = 0
    slippage_zero_rows: int = 0
    overfill_rows: int = 0
    first_replay_unit_id: str | None = None
    last_replay_unit_id: str | None = None
    first_source_ordering_key: str | None = None
    last_source_ordering_key: str | None = None


@dataclass(frozen=True)
class PureBookBuildResult:
    lane_output_path: Path
    summary_path: Path
    manifest_path: Path
    summary: dict[str, Any]
    manifest: dict[str, Any]


def walk_replenishing_book(unit: ReplayUnit, levels: list[BookLevel]) -> SimulatedFill:
    if unit.requested_size <= 0:
        return SimulatedFill(
            filled_size=0.0,
            filled_notional=0.0,
            avg_execution_price=unit.reference_price,
            remainder_size=0.0,
        )

    remaining_size = unit.requested_size
    weighted_notional = 0.0
    filled_size = 0.0

    for level in levels:
        if remaining_size <= 0:
            break
        direction = 1 if unit.side == 'buy' else -1
        exec_price = unit.reference_price * (1 + direction * level.spread_bps / 10_000)
        if exec_price <= 0:
            raise ValueError('Synthetic book execution price must remain positive')
        available_size = level.size_usd / exec_price if level.size_usd > 0 else 0.0
        take_size = min(available_size, remaining_size)
        if take_size <= 0:
            continue
        weighted_notional += take_size * exec_price
        filled_size += take_size
        remaining_size -= take_size

    if filled_size == 0:
        return SimulatedFill(
            filled_size=0.0,
            filled_notional=0.0,
            avg_execution_price=unit.reference_price,
            remainder_size=unit.requested_size,
        )

    avg_execution_price = weighted_notional / filled_size
    overfill = filled_size - unit.requested_size
    if overfill > OVERFILL_TOLERANCE:
        raise ValueError(
            f'Synthetic book overfilled replay unit {unit.replay_unit_id} by {overfill:.12g} size units'
        )
    if overfill > 0:
        filled_size = unit.requested_size
        weighted_notional = avg_execution_price * filled_size
    remainder_size = max(unit.requested_size - filled_size, 0.0)
    return SimulatedFill(
        filled_size=filled_size,
        filled_notional=weighted_notional,
        avg_execution_price=avg_execution_price,
        remainder_size=remainder_size,
    )


def simulate_pure_book(unit: ReplayUnit, levels: list[BookLevel]) -> ExecutionRecord:
    fill = walk_replenishing_book(unit, levels)
    return ExecutionRecord(
        lane=LANE_NAME,
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=fill.filled_size,
        filled_notional=fill.filled_notional,
        completion_ratio=completion_ratio(fill.filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=fill.avg_execution_price,
        fees_paid=0.0,
        remainder_size=fill.remainder_size,
        route_breakdown={'pure_book': fill.filled_size},
        admissibility_passed=None,
    )


def build_pure_book_row(
    unit: ReplayUnit,
    context: ObservedEventContext,
    levels: list[BookLevel],
    *,
    replay_projection_verified: bool = True,
) -> PureBookRow:
    record = simulate_pure_book(unit, levels)
    execution_slippage = 0.0
    if record.filled_size > 0:
        execution_slippage = slippage_bps(unit.reference_price, record.avg_execution_price, unit.side)
    return PureBookRow(
        record=record,
        context=context,
        execution_slippage_bps=execution_slippage,
        replay_projection_verified=replay_projection_verified,
    )


def run_pure_book_lane(root: str | Path) -> PureBookBuildResult:
    repo_root = Path(root).resolve()
    interim_dir = repo_root / 'data' / 'interim'
    replay_units_path = interim_dir / REPLAY_UNITS_FILENAME
    normalized_events_path = interim_dir / NORMALIZED_EVENTS_FILENAME
    book_config_path = repo_root / 'config' / BOOK_CONFIG_FILENAME
    fee_config_path = repo_root / 'config' / FEE_CONFIG_FILENAME
    _require_inputs([replay_units_path, normalized_events_path, book_config_path, fee_config_path])

    book_profile = load_book_profile(book_config_path)
    if not book_profile.replenish_per_replay_unit:
        raise ValueError('3A pure-book lane requires replenish_per_replay_unit=true under the locked Phase 0 contract')

    fee_policy = load_fee_policy(fee_config_path)

    processed_dir = repo_root / 'data' / 'processed'
    processed_dir.mkdir(parents=True, exist_ok=True)
    lane_output_path = processed_dir / LANE_OUTPUT_FILENAME
    summary_path = processed_dir / SUMMARY_FILENAME
    manifest_path = processed_dir / MANIFEST_FILENAME

    stats = PureBookStats()
    mapping_fingerprint = hashlib.sha256()

    with lane_output_path.open('w', encoding='utf-8', newline='') as lane_handle:
        writer = csv.DictWriter(lane_handle, fieldnames=PURE_BOOK_OUTPUT_FIELDNAMES)
        writer.writeheader()
        for aligned in iter_aligned_event_rows(replay_units_path, normalized_events_path):
            pure_book_row = build_pure_book_row(
                aligned.replay_unit,
                aligned.context,
                list(book_profile.levels),
                replay_projection_verified=aligned.replay_projection_verified,
            )
            writer.writerow(render_pure_book_row(pure_book_row))
            update_stats(stats, pure_book_row)
            mapping_fingerprint.update(
                (
                    f'{aligned.context.source_ordering_key}|{aligned.replay_unit.replay_unit_id}|'
                    f'{aligned.context.trade_row_id}|{aligned.context.swap_event_id}\n'
                ).encode('utf-8')
            )

    summary = build_summary(
        replay_units_path=replay_units_path,
        normalized_events_path=normalized_events_path,
        book_config_path=book_config_path,
        fee_config_path=fee_config_path,
        lane_output_path=lane_output_path,
        stats=stats,
        book_profile=book_profile,
        fee_policy=fee_policy,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )
    manifest = build_manifest(
        replay_units_path=replay_units_path,
        normalized_events_path=normalized_events_path,
        book_config_path=book_config_path,
        fee_config_path=fee_config_path,
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        stats=stats,
        book_profile=book_profile,
        fee_policy=fee_policy,
        summary=summary,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )

    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return PureBookBuildResult(
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
        summary=summary,
        manifest=manifest,
    )


def load_fee_policy(path: str | Path) -> dict[str, Any]:
    payload = _load_yaml_payload(Path(path))
    fees = payload.get('fees')
    if not isinstance(fees, dict):
        raise ValueError(f'{path} must define a top-level fees mapping')
    return fees


def render_pure_book_row(row: PureBookRow) -> dict[str, str]:
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
        'avg_execution_price': format_decimal(record.avg_execution_price),
        'execution_slippage_bps': format_decimal(row.execution_slippage_bps),
        'fees_paid': format_decimal(record.fees_paid),
        'fee_methodology': FEE_METHODOLOGY,
        'fee_precision': FEE_PRECISION,
        'fee_covered': format_bool(context.fee_covered),
        'remainder_size': format_decimal(record.remainder_size),
        'route_breakdown': json.dumps(record.route_breakdown, sort_keys=True),
        'admissibility_passed': format_optional_bool(record.admissibility_passed),
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


def update_stats(stats: PureBookStats, row: PureBookRow) -> None:
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
    stats.requested_size_total += record.requested_size
    stats.filled_size_total += record.filled_size
    stats.filled_notional_total += record.filled_notional
    stats.remainder_size_total += record.remainder_size

    if record.filled_size > record.requested_size + OVERFILL_TOLERANCE:
        stats.overfill_rows += 1

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

    if record.filled_size <= 0:
        stats.slippage_excluded_zero_fill_rows += 1
        return

    if row.execution_slippage_bps > 0:
        stats.slippage_positive_rows += 1
    elif row.execution_slippage_bps < 0:
        stats.slippage_negative_rows += 1
    else:
        stats.slippage_zero_rows += 1

    if math.isfinite(row.execution_slippage_bps):
        stats.finite_slippage_rows += 1
        stats.slippage_sum_bps += row.execution_slippage_bps
        stats.slippage_abs_sum_bps += abs(row.execution_slippage_bps)
        if stats.slippage_min_bps is None or row.execution_slippage_bps < stats.slippage_min_bps:
            stats.slippage_min_bps = row.execution_slippage_bps
        if stats.slippage_max_bps is None or row.execution_slippage_bps > stats.slippage_max_bps:
            stats.slippage_max_bps = row.execution_slippage_bps
    else:
        stats.infinite_slippage_rows += 1


def build_summary(
    *,
    replay_units_path: Path,
    normalized_events_path: Path,
    book_config_path: Path,
    fee_config_path: Path,
    lane_output_path: Path,
    stats: PureBookStats,
    book_profile: BookProfile,
    fee_policy: dict[str, Any],
    mapping_fingerprint: str,
) -> dict[str, Any]:
    counts_reconciliation = reconcile_totals(stats.row_count, stats.row_count)
    return {
        'generated_at_utc': utc_now(),
        'lane': LANE_NAME,
        'contract': {
            'lane_mode': 'event_level_pure_book_3a',
            'replay_unit_mapping': 'one_replay_unit_to_one_pure_book_record',
            'canonical_ordering': ['tradeTimestampSeconds', 'swapEventId', 'tradeRowId'],
            'book_fill_basis': 'requested_size',
            'book_reset': 'per_replay_unit',
            'slippage_basis': 'reference_price',
            'completion_basis': 'filled_size_over_requested_size',
            'fee_treatment': 'no_synthetic_fee_model_flag_and_continue',
        },
        'inputs': {
            'replay_units_path': str(replay_units_path),
            'normalized_events_path': str(normalized_events_path),
            'book_config_path': str(book_config_path),
            'fee_config_path': str(fee_config_path),
        },
        'book': build_book_summary(book_profile),
        'outputs': {
            'lane_output_path': str(lane_output_path),
        },
        'row_counts': {
            'normalized_event_rows': stats.row_count,
            'pure_book_rows': stats.row_count,
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
            'excluded_zero_fill_rows': stats.slippage_excluded_zero_fill_rows,
            'positive_rows': stats.slippage_positive_rows,
            'negative_rows': stats.slippage_negative_rows,
            'zero_rows': stats.slippage_zero_rows,
        },
        'totals': {
            'requested_size_hbar': format_scaled_int(stats.requested_size_raw_total, 8),
            'requested_notional_usdc': format_scaled_int(stats.requested_notional_raw_total, 6),
            'filled_size_hbar': format_decimal(stats.filled_size_total),
            'filled_notional_usdc': format_decimal(stats.filled_notional_total),
            'remainder_size_hbar': format_decimal(stats.remainder_size_total),
        },
        'coverage': {
            'reference_price_fallback_rows': stats.reference_price_fallback_rows,
            'swap_metadata_covered_rows': stats.swap_metadata_covered_rows,
            'swap_metadata_missing_rows': stats.swap_metadata_missing_rows,
        },
        'fees': {
            'fee_methodology': FEE_METHODOLOGY,
            'fee_precision': FEE_PRECISION,
            'fee_covered_rows': stats.fee_covered_rows,
            'fee_missing_rows': stats.fee_missing_rows,
            'precise_fee_rows': stats.precise_fee_rows,
            'policy': fee_policy,
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
            'pure_book_count': stats.row_count,
            'filled_plus_remainder_matches_requested_size': nearly_equal(
                stats.filled_size_total + stats.remainder_size_total,
                stats.requested_size_total,
            ),
            'no_overfill_rows': stats.overfill_rows == 0,
            'overfill_rows': stats.overfill_rows,
            'replay_projection_complete': stats.replay_projection_missing_tail_rows == 0,
        },
        'caveats': build_caveats(stats),
    }


def build_manifest(
    *,
    replay_units_path: Path,
    normalized_events_path: Path,
    book_config_path: Path,
    fee_config_path: Path,
    lane_output_path: Path,
    summary_path: Path,
    stats: PureBookStats,
    book_profile: BookProfile,
    fee_policy: dict[str, Any],
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
            'book_config_path': str(book_config_path),
            'book_config_bytes': book_config_path.stat().st_size,
            'fee_config_path': str(fee_config_path),
            'fee_config_bytes': fee_config_path.stat().st_size,
        },
        'outputs': {
            'lane_output_path': str(lane_output_path),
            'lane_output_bytes': lane_output_path.stat().st_size,
            'summary_path': str(summary_path),
            'summary_bytes': len(json.dumps(summary, indent=2).encode('utf-8')) + 1,
            'manifest_path': str(lane_output_path.with_name(MANIFEST_FILENAME)),
        },
        'row_counts': summary['row_counts'],
        'book': build_book_summary(book_profile),
        'mapping': {
            'fingerprint': mapping_fingerprint,
            'one_to_one_mapping_verified': True,
            'row_count': stats.row_count,
            'replay_projection_complete': stats.replay_projection_missing_tail_rows == 0,
            'replay_projection_verified_rows': stats.replay_projection_verified_rows,
            'replay_projection_missing_tail_rows': stats.replay_projection_missing_tail_rows,
        },
        'reconciliation': summary['reconciliation'],
        'fees': {
            **summary['fees'],
            'policy': fee_policy,
        },
        'caveats': build_caveats(stats),
    }


def build_book_summary(book_profile: BookProfile) -> dict[str, Any]:
    return {
        'total_depth_usd': format_decimal(book_profile.total_depth_usd),
        'replenish_per_replay_unit': book_profile.replenish_per_replay_unit,
        'level_count': len(book_profile.levels),
        'levels': [
            {
                'spread_bps': format_decimal(level.spread_bps),
                'size_usd': format_decimal(level.size_usd),
            }
            for level in book_profile.levels
        ],
        'profile_fingerprint': book_profile.fingerprint,
    }


def build_caveats(stats: PureBookStats) -> list[str]:
    caveats = [
        FEE_CAVEAT,
        '3A uses a replenishing synthetic book centered on reference_price and reset per replay unit. '
        'That ladder is a study-owned deterministic assumption, not a reconstruction of live V3 inventory.',
        '3A walks the synthetic ladder against requested_size. requested_notional is preserved from RH-03 '
        'for comparison context and is not forced to match synthetic filled_notional.',
    ]
    not_full_fill_rows = stats.partial_fill_rows + stats.zero_fill_rows
    if not_full_fill_rows > 0:
        caveats.append(
            f'{not_full_fill_rows} replay unit(s) are not fully filled by the configured synthetic book. '
            'completion_ratio and remainder_size preserve that outcome explicitly; the lane does not force completion to 1.0.'
        )
    if stats.slippage_excluded_zero_fill_rows > 0:
        caveats.append(
            f'{stats.slippage_excluded_zero_fill_rows} zero-fill replay unit(s) are excluded from slippage averages '
            'because no synthetic execution occurred.'
        )
    if stats.replay_projection_missing_tail_rows > 0:
        caveats.append(
            f'The materialized replay_units.csv projection ends {stats.replay_projection_missing_tail_rows} row(s) '
            'before normalized_events.csv. The pure-book lane therefore derives the missing tail replay-unit records '
            'directly from normalized event rows while preserving replay_unit_id and source anchors, and records the '
            'projection gap explicitly in the manifest.'
        )
    if stats.infinite_slippage_rows > 0:
        caveats.append(
            f'{stats.infinite_slippage_rows} replay unit(s) have non-finite slippage and are excluded from finite '
            'slippage averages.'
        )
    return caveats


def format_optional_bool(value: bool | None) -> str:
    if value is None:
        return ''
    return format_bool(value)


def nearly_equal(left: float, right: float, *, tolerance: float = 1e-9) -> bool:
    scale = max(1.0, abs(left), abs(right))
    return abs(left - right) <= tolerance * scale

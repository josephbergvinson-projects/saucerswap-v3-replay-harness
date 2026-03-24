from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ..validation.determinism import fingerprint_payload
from ..validation.reconcile import reconcile_totals
from .events import (
    NORMALIZED_EVENT_FIELDNAMES,
    REPLAY_UNIT_FIELDNAMES,
    format_scaled_int,
    has_explicit_side,
    normalize_trade_row,
    parse_int,
    parse_timestamp_seconds,
)
from .prices import ReferencePriceIndex

TRADES_FILENAME = 'hbar_usdc_v2_015_trades.csv'
SWAP_METADATA_FILENAME = 'hbar_usdc_v2_015_swap_metadata.csv'
REFERENCE_PRICES_FILENAME = 'hbar_reference_prices.csv'
FEE_INPUTS_FILENAME = 'v2_fee_inputs.csv'


@dataclass(frozen=True)
class NormalizationResult:
    normalized_events_path: Path
    replay_units_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class MetadataIndex:
    swap_ids: set[str]
    row_count: int
    unique_swap_count: int


@dataclass(frozen=True)
class FeeCoverageIndex:
    covered_days: set[int]
    row_count: int
    covered_row_count: int
    unique_day_count: int


@dataclass(frozen=True)
class RawPaths:
    trades_path: Path
    metadata_path: Path
    reference_prices_path: Path
    fee_inputs_path: Path


class OrderViolationError(ValueError):
    pass


def run_normalization(root: str | Path) -> NormalizationResult:
    repo_root = Path(root).resolve()
    raw_paths = _resolve_raw_paths(repo_root)
    _require_inputs(raw_paths)

    metadata_index = load_metadata_index(raw_paths.metadata_path)
    fee_index = load_fee_coverage_index(raw_paths.fee_inputs_path)
    reference_index = ReferencePriceIndex.from_csv(raw_paths.reference_prices_path)

    interim_dir = repo_root / 'data' / 'interim'
    interim_dir.mkdir(parents=True, exist_ok=True)
    normalized_events_path = interim_dir / 'normalized_events.csv'
    replay_units_path = interim_dir / 'replay_units.csv'
    manifest_path = interim_dir / 'normalization-manifest.json'

    stats: dict[str, Any] = {
        'raw_trade_rows': 0,
        'normalized_event_rows': 0,
        'replay_unit_rows': 0,
        'swap_metadata_covered_rows': 0,
        'swap_metadata_missing_rows': 0,
        'fee_covered_rows': 0,
        'fee_missing_rows': 0,
        'reference_price_at_or_before_rows': 0,
        'reference_price_later_fallback_rows': 0,
        'reference_price_missing_rows': 0,
        'explicit_side_rows': 0,
        'inferred_side_rows': 0,
        'buy_rows': 0,
        'sell_rows': 0,
        'requested_size_raw_total': 0,
        'requested_notional_raw_total': 0,
        'trade_min_timestamp': None,
        'trade_max_timestamp': None,
        'first_ordering_key': None,
        'last_ordering_key': None,
    }

    previous_ordering_key: tuple[int, int, int] | None = None

    with raw_paths.trades_path.open('r', encoding='utf-8', newline='') as trades_handle, normalized_events_path.open(
        'w', encoding='utf-8', newline=''
    ) as normalized_handle, replay_units_path.open('w', encoding='utf-8', newline='') as replay_handle:
        trade_reader = csv.DictReader(trades_handle)
        normalized_writer = csv.DictWriter(normalized_handle, fieldnames=NORMALIZED_EVENT_FIELDNAMES)
        replay_writer = csv.DictWriter(replay_handle, fieldnames=REPLAY_UNIT_FIELDNAMES)
        normalized_writer.writeheader()
        replay_writer.writeheader()

        for row in trade_reader:
            trade_timestamp_seconds = parse_timestamp_seconds(row['tradeTimestampSeconds'])
            swap_event_id = str(parse_int(row['swapEventId']))
            trade_row_id = parse_int(row['tradeRowId'])
            ordering_key = (trade_timestamp_seconds, int(swap_event_id), trade_row_id)
            if previous_ordering_key is not None and ordering_key < previous_ordering_key:
                raise OrderViolationError(
                    f'Non-deterministic ordering detected: {ordering_key} after {previous_ordering_key}'
                )
            previous_ordering_key = ordering_key

            price_match = reference_index.lookup(trade_timestamp_seconds)
            swap_metadata_covered = swap_event_id in metadata_index.swap_ids
            fee_covered = fee_day_start(trade_timestamp_seconds) in fee_index.covered_days

            event = normalize_trade_row(
                row,
                reference_price=price_match.reference_price,
                reference_price_source=price_match.source,
                reference_price_fallback=price_match.fallback,
                swap_metadata_covered=swap_metadata_covered,
                fee_covered=fee_covered,
            )
            replay_unit = event.to_replay_unit()

            normalized_writer.writerow(event.as_normalized_row())
            replay_writer.writerow(event.as_replay_row())

            _update_stats(
                stats,
                row=row,
                event=event,
                price_source=price_match.source,
                price_fallback=price_match.fallback,
            )
            stats['raw_trade_rows'] += 1
            stats['normalized_event_rows'] += 1
            stats['replay_unit_rows'] += 1
            stats['requested_size_raw_total'] += event.target_volume_raw
            stats['requested_notional_raw_total'] += event.base_volume_raw
            _ = replay_unit

    manifest = build_normalization_manifest(
        raw_paths=raw_paths,
        normalized_events_path=normalized_events_path,
        replay_units_path=replay_units_path,
        metadata_index=metadata_index,
        fee_index=fee_index,
        reference_index=reference_index,
        stats=stats,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return NormalizationResult(
        normalized_events_path=normalized_events_path,
        replay_units_path=replay_units_path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_normalization_manifest(
    *,
    raw_paths: RawPaths,
    normalized_events_path: Path,
    replay_units_path: Path,
    metadata_index: MetadataIndex,
    fee_index: FeeCoverageIndex,
    reference_index: ReferencePriceIndex,
    stats: dict[str, Any],
) -> dict[str, Any]:
    reconciliation = reconcile_totals(
        raw_count=stats['raw_trade_rows'],
        normalized_count=stats['normalized_event_rows'],
    )
    manifest = {
        'generated_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'contract': {
            'replay_unit_mode': 'one_trade_row_per_replay_unit',
            'canonical_ordering': ['tradeTimestampSeconds', 'swapEventId', 'tradeRowId'],
        },
        'inputs': {
            'trades_path': str(raw_paths.trades_path),
            'swap_metadata_path': str(raw_paths.metadata_path),
            'reference_prices_path': str(raw_paths.reference_prices_path),
            'fee_inputs_path': str(raw_paths.fee_inputs_path),
            'swap_metadata_rows': metadata_index.row_count,
            'swap_metadata_unique_swap_ids': metadata_index.unique_swap_count,
            'reference_price_rows': reference_index.row_count,
            'fee_input_rows': fee_index.row_count,
            'fee_input_covered_rows': fee_index.covered_row_count,
            'fee_input_unique_covered_days': fee_index.unique_day_count,
        },
        'outputs': {
            'normalized_events_path': str(normalized_events_path),
            'normalized_events_bytes': normalized_events_path.stat().st_size,
            'replay_units_path': str(replay_units_path),
            'replay_units_bytes': replay_units_path.stat().st_size,
        },
        'row_counts': {
            'raw_trade_rows': stats['raw_trade_rows'],
            'normalized_event_rows': stats['normalized_event_rows'],
            'replay_unit_rows': stats['replay_unit_rows'],
        },
        'coverage': {
            'swap_metadata': coverage_block(
                covered_rows=stats['swap_metadata_covered_rows'],
                missing_rows=stats['swap_metadata_missing_rows'],
            ),
            'fee_inputs': coverage_block(
                covered_rows=stats['fee_covered_rows'],
                missing_rows=stats['fee_missing_rows'],
            ),
            'reference_prices': {
                'at_or_before_rows': stats['reference_price_at_or_before_rows'],
                'later_fallback_rows': stats['reference_price_later_fallback_rows'],
                'missing_rows': stats['reference_price_missing_rows'],
                'coverage_ratio': ratio(
                    stats['reference_price_at_or_before_rows']
                    + stats['reference_price_later_fallback_rows'],
                    stats['raw_trade_rows'],
                ),
            },
            'side_resolution': {
                'explicit_rows': stats['explicit_side_rows'],
                'inferred_rows': stats['inferred_side_rows'],
            },
        },
        'sides': {
            'buy_rows': stats['buy_rows'],
            'sell_rows': stats['sell_rows'],
        },
        'totals': {
            'requested_size_hbar': format_scaled_int(stats['requested_size_raw_total'], 8),
            'requested_notional_usdc': format_scaled_int(stats['requested_notional_raw_total'], 6),
        },
        'timestamp_ranges': {
            'trades': {
                'min_timestamp_seconds': stats['trade_min_timestamp'],
                'max_timestamp_seconds': stats['trade_max_timestamp'],
            },
            'reference_prices': {
                'min_timestamp_seconds': reference_index.min_timestamp_seconds,
                'max_timestamp_seconds': reference_index.max_timestamp_seconds,
            },
        },
        'ordering': {
            'first_key': stats['first_ordering_key'],
            'last_key': stats['last_ordering_key'],
            'fingerprint': fingerprint_payload(
                {
                    'first_key': stats['first_ordering_key'],
                    'last_key': stats['last_ordering_key'],
                    'rows': stats['raw_trade_rows'],
                }
            ),
        },
        'reconciliation': reconciliation,
    }
    return manifest


def coverage_block(*, covered_rows: int, missing_rows: int) -> dict[str, Any]:
    total_rows = covered_rows + missing_rows
    return {
        'covered_rows': covered_rows,
        'missing_rows': missing_rows,
        'coverage_ratio': ratio(covered_rows, total_rows),
    }


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def load_metadata_index(path: str | Path) -> MetadataIndex:
    swap_ids: set[str] = set()
    row_count = 0
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            swap_ids.add(str(parse_int(row['swap_id'])))
    return MetadataIndex(swap_ids=swap_ids, row_count=row_count, unique_swap_count=len(swap_ids))


def load_fee_coverage_index(path: str | Path) -> FeeCoverageIndex:
    covered_days: set[int] = set()
    row_count = 0
    covered_row_count = 0
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            if parse_int(row['poolVersion']) != 2:
                continue
            covered_row_count += 1
            covered_days.add(fee_day_start(parse_int(row['timestampSeconds'])))
    return FeeCoverageIndex(
        covered_days=covered_days,
        row_count=row_count,
        covered_row_count=covered_row_count,
        unique_day_count=len(covered_days),
    )


def fee_day_start(timestamp_seconds: int) -> int:
    return timestamp_seconds - (timestamp_seconds % 86_400)


def _resolve_raw_paths(root: Path) -> RawPaths:
    raw_dir = root / 'data' / 'raw' / 'gigabrain'
    return RawPaths(
        trades_path=raw_dir / TRADES_FILENAME,
        metadata_path=raw_dir / SWAP_METADATA_FILENAME,
        reference_prices_path=raw_dir / REFERENCE_PRICES_FILENAME,
        fee_inputs_path=raw_dir / FEE_INPUTS_FILENAME,
    )


def _require_inputs(raw_paths: RawPaths) -> None:
    missing = [
        path
        for path in [
            raw_paths.trades_path,
            raw_paths.metadata_path,
            raw_paths.reference_prices_path,
            raw_paths.fee_inputs_path,
        ]
        if not path.exists()
    ]
    if missing:
        joined = ', '.join(str(path) for path in missing)
        raise FileNotFoundError(f'Missing normalization input files: {joined}')


def _update_stats(
    stats: dict[str, Any],
    *,
    row: dict[str, str],
    event: Any,
    price_source: str,
    price_fallback: bool,
) -> None:
    trade_timestamp_seconds = event.trade_timestamp_seconds
    if stats['trade_min_timestamp'] is None or trade_timestamp_seconds < stats['trade_min_timestamp']:
        stats['trade_min_timestamp'] = trade_timestamp_seconds
    if stats['trade_max_timestamp'] is None or trade_timestamp_seconds > stats['trade_max_timestamp']:
        stats['trade_max_timestamp'] = trade_timestamp_seconds
    if stats['first_ordering_key'] is None:
        stats['first_ordering_key'] = event.source_ordering_key
    stats['last_ordering_key'] = event.source_ordering_key

    if event.side == 'buy':
        stats['buy_rows'] += 1
    elif event.side == 'sell':
        stats['sell_rows'] += 1

    if has_explicit_side(row.get('type')):
        stats['explicit_side_rows'] += 1
    else:
        stats['inferred_side_rows'] += 1

    if event.swap_metadata_covered:
        stats['swap_metadata_covered_rows'] += 1
    else:
        stats['swap_metadata_missing_rows'] += 1

    if event.fee_covered:
        stats['fee_covered_rows'] += 1
    else:
        stats['fee_missing_rows'] += 1

    if price_source == 'at_or_before' and not price_fallback:
        stats['reference_price_at_or_before_rows'] += 1
    elif price_source == 'nearest_later' and price_fallback:
        stats['reference_price_later_fallback_rows'] += 1
    else:
        stats['reference_price_missing_rows'] += 1

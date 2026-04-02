from __future__ import annotations

import csv
from dataclasses import dataclass, field
import hashlib
import json
import math
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterator

from ..backstop.v2_residual import ResidualQuote, residual_quote_from_v2_row
from ..baseline.v2_realized import average, format_optional_decimal, parse_bool_text, utc_now
from ..fees import (
    FeeRollupStats,
    add_record_fee_rollups,
    build_fee_summary_payload,
    build_hybrid_fee_fields,
    default_v3_scenario_id,
    load_fee_policy,
    v3_supported_scenarios,
)
from ..metrics.core import completion_ratio, slippage_bps, symmetric_reference_denominator_bps
from ..normalize.events import format_bool, format_decimal, format_scaled_int, parse_float, parse_int, parse_optional_float
from ..rules.admissibility import HybridRule, load_hybrid_rule, passes_hybrid_admissibility, passes_slippage_cap
from ..schema import ExecutionRecord, ReplayUnit
from ..validation.reconcile import reconcile_totals
from .book_profile import BookLevel
from .pure_book import (
    PURE_BOOK_OUTPUT_FIELDNAMES,
    format_optional_bool,
    nearly_equal,
    walk_replenishing_book,
)

LANE_NAME = '3b_hybrid'
PURE_BOOK_INPUT_FILENAME = 'lane_3a_pure_book.csv'
V2_BASELINE_INPUT_FILENAME = 'lane_v2_baseline.csv'
HYBRID_RULE_FILENAME = 'hybrid_rule.yaml'
FEE_CONFIG_FILENAME = 'fees.yaml'
LANE_OUTPUT_FILENAME = 'lane_3b_hybrid.csv'
SUMMARY_FILENAME = 'hybrid_summary.json'
MANIFEST_FILENAME = 'hybrid_manifest.json'
OVERFILL_TOLERANCE = 1e-9

FEE_METHODOLOGY = (
    'RH-21 models 3B fee transfers route-by-route under the locked RH-20 contract: pure-book '
    'filled notional uses the V3 WHBAR/USDC scenarios and residual routed to the V2 backstop uses '
    'the locked V2 WHBAR/USDC split.'
)
FEE_PRECISION = 'route_aware_modeled_from_locked_v2_v3_schedules'
FEE_CAVEAT = (
    '3B liquidity-side fee output blends explicit V3 maker rebate capture with V2 active-LP fee '
    'accrual when both routes execute. It is not full maker PnL or LP profitability.'
)


class HybridInputAlignmentError(ValueError):
    pass


@dataclass(frozen=True)
class HybridSourceRow:
    replay_unit_id: str
    timestamp: str
    side: str
    requested_size: float
    requested_notional: float
    filled_size: float
    filled_notional: float
    completion_ratio: float
    reference_price: float
    amm_pre_trade_spot_reference_price: float | None
    avg_execution_price: float
    remainder_size: float
    route_breakdown: dict[str, float]
    admissibility_passed: bool | None
    trade_row_id: int
    swap_event_id: str
    trade_timestamp_seconds: int
    source_ordering_key: str
    base_id: str
    target_id: str
    base_volume_raw: int
    target_volume_raw: int
    reference_price_source: str
    reference_price_fallback: bool
    swap_metadata_covered: bool
    fee_covered: bool


@dataclass(frozen=True)
class HybridRow:
    record: ExecutionRecord
    timestamp: str
    execution_slippage_bps: float
    amm_pre_trade_spot_reference_price: float | None
    amm_pre_trade_spot_gross_slippage_bps: float | None
    trade_row_id: int
    swap_event_id: str
    trade_timestamp_seconds: int
    source_ordering_key: str
    base_id: str
    target_id: str
    base_volume_raw: int
    target_volume_raw: int
    reference_price_source: str
    reference_price_fallback: bool
    swap_metadata_covered: bool
    fee_covered: bool
    pure_book_remainder_size: float
    backstop_quote_recovered: bool
    backstop_quote_source: str | None
    backstop_available_size: float | None
    v2_backstop_routed_size: float


@dataclass
class HybridStats:
    row_count: int = 0
    buy_rows: int = 0
    sell_rows: int = 0
    requested_size_raw_total: int = 0
    requested_notional_raw_total: int = 0
    requested_size_total: float = 0.0
    filled_size_total: float = 0.0
    filled_notional_total: float = 0.0
    remainder_size_total: float = 0.0
    pure_book_size_total: float = 0.0
    v2_backstop_size_total: float = 0.0
    full_fill_rows: int = 0
    partial_fill_rows: int = 0
    zero_fill_rows: int = 0
    completion_ratio_sum: float = 0.0
    fee_covered_rows: int = 0
    fee_missing_rows: int = 0
    precise_fee_rows: int = 0
    fee_rollups: FeeRollupStats = field(default_factory=FeeRollupStats)
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
    amm_pre_trade_spot_supported_rows: int = 0
    amm_pre_trade_spot_missing_rows: int = 0
    amm_pre_trade_spot_slippage_sum_bps: float = 0.0
    amm_pre_trade_spot_slippage_abs_sum_bps: float = 0.0
    amm_pre_trade_spot_finite_slippage_rows: int = 0
    amm_pre_trade_spot_infinite_slippage_rows: int = 0
    amm_pre_trade_spot_slippage_min_bps: float | None = None
    amm_pre_trade_spot_slippage_max_bps: float | None = None
    overfill_rows: int = 0
    residual_rows: int = 0
    no_residual_rows: int = 0
    backstop_quote_recovered_rows: int = 0
    backstop_quote_missing_rows: int = 0
    admissibility_pass_rows: int = 0
    admissibility_fail_rows: int = 0
    routed_rows: int = 0
    pure_book_only_rows: int = 0
    unrouted_residual_rows: int = 0
    available_size_limited_rows: int = 0
    hybrid_full_fill_from_backstop_rows: int = 0
    first_replay_unit_id: str | None = None
    last_replay_unit_id: str | None = None
    first_source_ordering_key: str | None = None
    last_source_ordering_key: str | None = None


@dataclass(frozen=True)
class HybridBuildResult:
    lane_output_path: Path
    summary_path: Path
    manifest_path: Path
    summary: dict[str, Any]
    manifest: dict[str, Any]


@dataclass(frozen=True)
class HybridAlignmentState:
    pure_book_row: HybridSourceRow
    baseline_row: HybridSourceRow
    row_number: int


def projected_hybrid_execution_price(
    *,
    pure_fill_size: float,
    pure_fill_notional: float,
    routed_size: float,
    routed_execution_price: float,
    reference_price: float,
) -> float:
    total_size = pure_fill_size + routed_size
    if total_size <= 0:
        return reference_price
    return (pure_fill_notional + routed_size * routed_execution_price) / total_size



def simulate_hybrid(
    unit: ReplayUnit,
    levels: list[BookLevel],
    residual_quote: ResidualQuote | None,
    max_slippage_bps: float,
    fee_policy: dict[str, Any],
    *,
    default_fee_scenario_id: str | None = None,
) -> ExecutionRecord:
    book_fill = walk_replenishing_book(unit, levels)
    filled_size = book_fill.filled_size
    weighted_notional = book_fill.filled_notional
    route_breakdown = {'pure_book': book_fill.filled_size}
    admissibility_passed = None
    routed_size = 0.0
    routed_execution_price: float | None = None

    if book_fill.remainder_size > 0:
        admissibility_passed = False
        if residual_quote is not None:
            routed_size = min(book_fill.remainder_size, residual_quote.available_size)
            if routed_size > 0:
                projected_execution_price = projected_hybrid_execution_price(
                    pure_fill_size=book_fill.filled_size,
                    pure_fill_notional=book_fill.filled_notional,
                    routed_size=routed_size,
                    routed_execution_price=residual_quote.execution_price,
                    reference_price=unit.reference_price,
                )
                admissibility_passed = passes_slippage_cap(
                    side=unit.side,
                    reference_price=unit.reference_price,
                    execution_price=projected_execution_price,
                    max_slippage_bps=max_slippage_bps,
                )
                if admissibility_passed:
                    routed_execution_price = residual_quote.execution_price
                    filled_size += routed_size
                    weighted_notional += routed_size * residual_quote.execution_price
                    route_breakdown['v2_backstop'] = routed_size

    avg_execution_price = weighted_notional / filled_size if filled_size else unit.reference_price
    remainder_size = max(unit.requested_size - filled_size, 0.0)
    fee_fields = build_hybrid_fee_fields(
        fee_policy,
        requested_notional=unit.requested_notional,
        pure_book_filled_size=book_fill.filled_size,
        pure_book_filled_notional=book_fill.filled_notional,
        v2_backstop_filled_size=routed_size if admissibility_passed else 0.0,
        v2_backstop_execution_price=routed_execution_price,
        default_scenario_id=default_fee_scenario_id or default_v3_scenario_id(fee_policy),
    )
    return ExecutionRecord(
        lane=LANE_NAME,
        replay_unit_id=unit.replay_unit_id,
        side=unit.side,
        requested_size=unit.requested_size,
        requested_notional=unit.requested_notional,
        filled_size=filled_size,
        filled_notional=weighted_notional,
        completion_ratio=completion_ratio(filled_size, unit.requested_size),
        reference_price=unit.reference_price,
        avg_execution_price=avg_execution_price,
        fees_paid=fee_fields['fees_paid'],
        fee_contract_version=fee_fields['fee_contract_version'],
        fee_scenario_id=fee_fields['fee_scenario_id'],
        v3_min_order_ineligible=fee_fields['v3_min_order_ineligible'],
        fee_basis_filled_notional_usd=fee_fields['fee_basis_filled_notional_usd'],
        trader_fee_paid_usd=fee_fields['trader_fee_paid_usd'],
        protocol_fee_earned_usd=fee_fields['protocol_fee_earned_usd'],
        active_lp_fee_earned_usd=fee_fields['active_lp_fee_earned_usd'],
        maker_rebate_earned_usd=fee_fields['maker_rebate_earned_usd'],
        remainder_size=remainder_size,
        route_breakdown=route_breakdown,
        fee_route_breakdown=fee_fields['fee_route_breakdown'],
        admissibility_passed=admissibility_passed,
    )


def run_hybrid_lane(root: str | Path) -> HybridBuildResult:
    repo_root = Path(root).resolve()
    processed_dir = repo_root / 'data' / 'processed'
    pure_book_path = processed_dir / PURE_BOOK_INPUT_FILENAME
    baseline_path = processed_dir / V2_BASELINE_INPUT_FILENAME
    hybrid_rule_path = repo_root / 'config' / HYBRID_RULE_FILENAME
    fee_config_path = repo_root / 'config' / FEE_CONFIG_FILENAME

    _require_inputs([pure_book_path, baseline_path, hybrid_rule_path, fee_config_path])

    hybrid_rule = load_hybrid_rule(hybrid_rule_path)
    fee_policy = load_fee_policy(fee_config_path)
    default_fee_scenario_id = default_v3_scenario_id(fee_policy)

    lane_output_path = processed_dir / LANE_OUTPUT_FILENAME
    summary_path = processed_dir / SUMMARY_FILENAME
    manifest_path = processed_dir / MANIFEST_FILENAME

    stats = HybridStats()
    mapping_fingerprint = hashlib.sha256()

    with lane_output_path.open('w', encoding='utf-8', newline='') as lane_handle:
        writer = csv.DictWriter(lane_handle, fieldnames=PURE_BOOK_OUTPUT_FIELDNAMES)
        writer.writeheader()
        for aligned in iter_aligned_lane_rows(pure_book_path, baseline_path):
            hybrid_row = build_hybrid_row(
                aligned.pure_book_row,
                aligned.baseline_row,
                hybrid_rule,
                fee_policy,
                default_fee_scenario_id=default_fee_scenario_id,
            )
            writer.writerow(render_hybrid_row(hybrid_row))
            update_stats(stats, hybrid_row)
            mapping_fingerprint.update(
                (
                    f'{hybrid_row.source_ordering_key}|{hybrid_row.record.replay_unit_id}|'
                    f'{hybrid_row.trade_row_id}|{hybrid_row.swap_event_id}\n'
                ).encode('utf-8')
            )

    summary = build_summary(
        pure_book_path=pure_book_path,
        baseline_path=baseline_path,
        hybrid_rule_path=hybrid_rule_path,
        fee_config_path=fee_config_path,
        lane_output_path=lane_output_path,
        stats=stats,
        hybrid_rule=hybrid_rule,
        fee_policy=fee_policy,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )
    manifest = build_manifest(
        pure_book_path=pure_book_path,
        baseline_path=baseline_path,
        hybrid_rule_path=hybrid_rule_path,
        fee_config_path=fee_config_path,
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        stats=stats,
        hybrid_rule=hybrid_rule,
        fee_policy=fee_policy,
        summary=summary,
        mapping_fingerprint=mapping_fingerprint.hexdigest(),
    )

    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return HybridBuildResult(
        lane_output_path=lane_output_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
        summary=summary,
        manifest=manifest,
    )


def iter_aligned_lane_rows(
    pure_book_path: str | Path,
    baseline_path: str | Path,
) -> Iterator[HybridAlignmentState]:
    pure_path = Path(pure_book_path)
    base_path = Path(baseline_path)
    with pure_path.open('r', encoding='utf-8', newline='') as pure_handle, base_path.open(
        'r', encoding='utf-8', newline=''
    ) as base_handle:
        pure_reader = csv.DictReader(pure_handle)
        base_reader = csv.DictReader(base_handle)
        for row_number, pair in enumerate(zip_longest(pure_reader, base_reader), start=1):
            pure_row_raw, base_row_raw = pair
            if pure_row_raw is None or base_row_raw is None:
                raise HybridInputAlignmentError(
                    'Mounted RH-05 pure-book rows and RH-04 baseline rows must have identical row counts '
                    f'(mismatch at row {row_number})'
                )
            pure_row = source_row_from_csv_row(pure_row_raw)
            base_row = source_row_from_csv_row(base_row_raw)
            assert_aligned_rows(pure_row, base_row, row_number=row_number)
            yield HybridAlignmentState(pure_book_row=pure_row, baseline_row=base_row, row_number=row_number)



def source_row_from_csv_row(row: dict[str, str]) -> HybridSourceRow:
    admissibility_text = row.get('admissibility_passed')
    admissibility_passed = None if not admissibility_text else parse_bool_text(admissibility_text)
    route_breakdown_text = row.get('route_breakdown') or '{}'
    route_breakdown = json.loads(route_breakdown_text)
    return HybridSourceRow(
        replay_unit_id=row['replay_unit_id'],
        timestamp=row['timestamp'],
        side=row['side'],
        requested_size=parse_float(row['requested_size']),
        requested_notional=parse_float(row['requested_notional']),
        filled_size=parse_float(row['filled_size']),
        filled_notional=parse_float(row['filled_notional']),
        completion_ratio=parse_float(row['completion_ratio']),
        reference_price=parse_float(row['reference_price']),
        amm_pre_trade_spot_reference_price=parse_optional_float(row.get('amm_pre_trade_spot_reference_price')),
        avg_execution_price=parse_float(row['avg_execution_price']),
        remainder_size=parse_float(row['remainder_size']),
        route_breakdown={str(key): float(value) for key, value in route_breakdown.items()},
        admissibility_passed=admissibility_passed,
        trade_row_id=parse_int(row['tradeRowId']),
        swap_event_id=row['swapEventId'],
        trade_timestamp_seconds=parse_int(row['tradeTimestampSeconds']),
        source_ordering_key=row['source_ordering_key'],
        base_id=row['baseId'],
        target_id=row['targetId'],
        base_volume_raw=parse_int(row['baseVolumeRaw']),
        target_volume_raw=parse_int(row['targetVolumeRaw']),
        reference_price_source=row['reference_price_source'],
        reference_price_fallback=parse_bool_text(row['reference_price_fallback']),
        swap_metadata_covered=parse_bool_text(row['swap_metadata_covered']),
        fee_covered=parse_bool_text(row['fee_covered']),
    )



def assert_aligned_rows(pure_row: HybridSourceRow, base_row: HybridSourceRow, *, row_number: int) -> None:
    pairs = [
        ('replay_unit_id', pure_row.replay_unit_id, base_row.replay_unit_id),
        ('tradeRowId', pure_row.trade_row_id, base_row.trade_row_id),
        ('swapEventId', pure_row.swap_event_id, base_row.swap_event_id),
        ('tradeTimestampSeconds', pure_row.trade_timestamp_seconds, base_row.trade_timestamp_seconds),
        ('source_ordering_key', pure_row.source_ordering_key, base_row.source_ordering_key),
        ('timestamp', pure_row.timestamp, base_row.timestamp),
        ('side', pure_row.side, base_row.side),
        ('requested_size', pure_row.requested_size, base_row.requested_size),
        ('requested_notional', pure_row.requested_notional, base_row.requested_notional),
        ('reference_price', pure_row.reference_price, base_row.reference_price),
        (
            'amm_pre_trade_spot_reference_price',
            pure_row.amm_pre_trade_spot_reference_price,
            base_row.amm_pre_trade_spot_reference_price,
        ),
        ('baseId', pure_row.base_id, base_row.base_id),
        ('targetId', pure_row.target_id, base_row.target_id),
        ('baseVolumeRaw', pure_row.base_volume_raw, base_row.base_volume_raw),
        ('targetVolumeRaw', pure_row.target_volume_raw, base_row.target_volume_raw),
    ]
    for field_name, left, right in pairs:
        if left != right:
            raise HybridInputAlignmentError(
                f'{field_name} mismatch at row {row_number}: {left!r} != {right!r}'
            )



def build_hybrid_row(
    pure_book_row: HybridSourceRow,
    baseline_row: HybridSourceRow,
    rule: HybridRule,
    fee_policy: dict[str, Any],
    *,
    default_fee_scenario_id: str | None = None,
) -> HybridRow:
    residual_quote = residual_quote_from_v2_row(
        {
            'lane': 'historical_v2_proxy',
            'replay_unit_id': baseline_row.replay_unit_id,
            'avg_execution_price': format_decimal(baseline_row.avg_execution_price),
            'filled_size': format_decimal(baseline_row.filled_size),
            'tradeRowId': str(baseline_row.trade_row_id),
            'swapEventId': baseline_row.swap_event_id,
            'tradeTimestampSeconds': str(baseline_row.trade_timestamp_seconds),
        }
    )
    record = hybrid_record_from_mounted_rows(
        pure_book_row,
        residual_quote,
        rule,
        fee_policy,
        default_fee_scenario_id=default_fee_scenario_id,
    )
    execution_slippage = 0.0
    if record.filled_size > 0:
        execution_slippage = slippage_bps(
            pure_book_row.reference_price,
            record.avg_execution_price,
            pure_book_row.side,
        )
    amm_pre_trade_spot_gross_slippage = None
    if record.filled_size > 0 and pure_book_row.amm_pre_trade_spot_reference_price is not None:
        amm_pre_trade_spot_gross_slippage = symmetric_reference_denominator_bps(
            pure_book_row.amm_pre_trade_spot_reference_price,
            record.avg_execution_price,
            pure_book_row.side,
        )
    v2_backstop_routed_size = float(record.route_breakdown.get('v2_backstop', 0.0))
    return HybridRow(
        record=record,
        timestamp=pure_book_row.timestamp,
        execution_slippage_bps=execution_slippage,
        amm_pre_trade_spot_reference_price=pure_book_row.amm_pre_trade_spot_reference_price,
        amm_pre_trade_spot_gross_slippage_bps=amm_pre_trade_spot_gross_slippage,
        trade_row_id=pure_book_row.trade_row_id,
        swap_event_id=pure_book_row.swap_event_id,
        trade_timestamp_seconds=pure_book_row.trade_timestamp_seconds,
        source_ordering_key=pure_book_row.source_ordering_key,
        base_id=pure_book_row.base_id,
        target_id=pure_book_row.target_id,
        base_volume_raw=pure_book_row.base_volume_raw,
        target_volume_raw=pure_book_row.target_volume_raw,
        reference_price_source=pure_book_row.reference_price_source,
        reference_price_fallback=pure_book_row.reference_price_fallback,
        swap_metadata_covered=pure_book_row.swap_metadata_covered,
        fee_covered=pure_book_row.fee_covered,
        pure_book_remainder_size=pure_book_row.remainder_size,
        backstop_quote_recovered=residual_quote is not None,
        backstop_quote_source=None if residual_quote is None else residual_quote.source,
        backstop_available_size=None if residual_quote is None else residual_quote.available_size,
        v2_backstop_routed_size=v2_backstop_routed_size,
    )



def hybrid_record_from_mounted_rows(
    pure_book_row: HybridSourceRow,
    residual_quote: ResidualQuote | None,
    rule: HybridRule,
    fee_policy: dict[str, Any],
    *,
    default_fee_scenario_id: str | None = None,
) -> ExecutionRecord:
    filled_size = pure_book_row.filled_size
    filled_notional = pure_book_row.filled_notional
    route_breakdown = {'pure_book': pure_book_row.filled_size}
    admissibility_passed = None
    routed_size = 0.0
    routed_execution_price: float | None = None

    if pure_book_row.remainder_size > 0:
        projected_execution_price = None
        if residual_quote is not None:
            routed_size = min(pure_book_row.remainder_size, residual_quote.available_size)
            if routed_size > 0:
                projected_execution_price = projected_hybrid_execution_price(
                    pure_fill_size=pure_book_row.filled_size,
                    pure_fill_notional=pure_book_row.filled_notional,
                    routed_size=routed_size,
                    routed_execution_price=residual_quote.execution_price,
                    reference_price=pure_book_row.reference_price,
                )
        admissibility_passed = passes_hybrid_admissibility(
            rule,
            side=pure_book_row.side,
            reference_price=pure_book_row.reference_price,
            execution_price=projected_execution_price,
            quote_available=residual_quote is not None,
        )
        if admissibility_passed and residual_quote is not None and routed_size > 0:
            routed_execution_price = residual_quote.execution_price
            filled_size += routed_size
            filled_notional += routed_size * residual_quote.execution_price
            route_breakdown['v2_backstop'] = routed_size

    avg_execution_price = filled_notional / filled_size if filled_size else pure_book_row.reference_price
    overfill = filled_size - pure_book_row.requested_size
    if overfill > OVERFILL_TOLERANCE:
        raise ValueError(
            f'Hybrid lane overfilled replay unit {pure_book_row.replay_unit_id} by {overfill:.12g} size units'
        )
    if overfill > 0:
        filled_size = pure_book_row.requested_size
        filled_notional = avg_execution_price * filled_size

    remainder_size = max(pure_book_row.requested_size - filled_size, 0.0)
    fee_fields = build_hybrid_fee_fields(
        fee_policy,
        requested_notional=pure_book_row.requested_notional,
        pure_book_filled_size=pure_book_row.filled_size,
        pure_book_filled_notional=pure_book_row.filled_notional,
        v2_backstop_filled_size=routed_size if admissibility_passed else 0.0,
        v2_backstop_execution_price=routed_execution_price,
        default_scenario_id=default_fee_scenario_id or default_v3_scenario_id(fee_policy),
    )
    return ExecutionRecord(
        lane=LANE_NAME,
        replay_unit_id=pure_book_row.replay_unit_id,
        side=pure_book_row.side,
        requested_size=pure_book_row.requested_size,
        requested_notional=pure_book_row.requested_notional,
        filled_size=filled_size,
        filled_notional=filled_notional,
        completion_ratio=completion_ratio(filled_size, pure_book_row.requested_size),
        reference_price=pure_book_row.reference_price,
        avg_execution_price=avg_execution_price,
        fees_paid=fee_fields['fees_paid'],
        fee_contract_version=fee_fields['fee_contract_version'],
        fee_scenario_id=fee_fields['fee_scenario_id'],
        v3_min_order_ineligible=fee_fields['v3_min_order_ineligible'],
        fee_basis_filled_notional_usd=fee_fields['fee_basis_filled_notional_usd'],
        trader_fee_paid_usd=fee_fields['trader_fee_paid_usd'],
        protocol_fee_earned_usd=fee_fields['protocol_fee_earned_usd'],
        active_lp_fee_earned_usd=fee_fields['active_lp_fee_earned_usd'],
        maker_rebate_earned_usd=fee_fields['maker_rebate_earned_usd'],
        remainder_size=remainder_size,
        route_breakdown=route_breakdown,
        fee_route_breakdown=fee_fields['fee_route_breakdown'],
        admissibility_passed=admissibility_passed,
    )



def render_hybrid_row(row: HybridRow) -> dict[str, str]:
    record = row.record
    return {
        'lane': record.lane,
        'replay_unit_id': record.replay_unit_id,
        'timestamp': row.timestamp,
        'side': record.side,
        'requested_size': format_decimal(record.requested_size),
        'requested_notional': format_decimal(record.requested_notional),
        'filled_size': format_decimal(record.filled_size),
        'filled_notional': format_decimal(record.filled_notional),
        'completion_ratio': format_decimal(record.completion_ratio),
        'reference_price': format_decimal(record.reference_price),
        'amm_pre_trade_spot_reference_price': format_optional_decimal(row.amm_pre_trade_spot_reference_price),
        'avg_execution_price': format_decimal(record.avg_execution_price),
        'execution_slippage_bps': format_decimal(row.execution_slippage_bps),
        'amm_pre_trade_spot_gross_slippage_bps': format_optional_decimal(
            row.amm_pre_trade_spot_gross_slippage_bps
        ),
        'fees_paid': format_decimal(record.fees_paid),
        'fee_contract_version': record.fee_contract_version,
        'fee_scenario_id': record.fee_scenario_id,
        'v3_min_order_ineligible': format_bool(record.v3_min_order_ineligible),
        'fee_basis_filled_notional_usd': format_decimal(record.fee_basis_filled_notional_usd),
        'trader_fee_paid_usd': format_decimal(record.trader_fee_paid_usd),
        'protocol_fee_earned_usd': format_decimal(record.protocol_fee_earned_usd),
        'active_lp_fee_earned_usd': format_decimal(record.active_lp_fee_earned_usd),
        'maker_rebate_earned_usd': format_decimal(record.maker_rebate_earned_usd),
        'fee_methodology': FEE_METHODOLOGY,
        'fee_precision': FEE_PRECISION,
        'fee_covered': format_bool(row.fee_covered),
        'fee_route_breakdown': json.dumps(record.fee_route_breakdown, sort_keys=True),
        'remainder_size': format_decimal(record.remainder_size),
        'route_breakdown': json.dumps(record.route_breakdown, sort_keys=True),
        'admissibility_passed': format_optional_bool(record.admissibility_passed),
        'tradeRowId': str(row.trade_row_id),
        'swapEventId': row.swap_event_id,
        'tradeTimestampSeconds': str(row.trade_timestamp_seconds),
        'source_ordering_key': row.source_ordering_key,
        'baseId': row.base_id,
        'targetId': row.target_id,
        'baseVolumeRaw': str(row.base_volume_raw),
        'targetVolumeRaw': str(row.target_volume_raw),
        'reference_price_source': row.reference_price_source,
        'reference_price_fallback': format_bool(row.reference_price_fallback),
        'swap_metadata_covered': format_bool(row.swap_metadata_covered),
    }



def update_stats(stats: HybridStats, row: HybridRow) -> None:
    record = row.record
    stats.row_count += 1
    if stats.first_replay_unit_id is None:
        stats.first_replay_unit_id = record.replay_unit_id
    stats.last_replay_unit_id = record.replay_unit_id
    if stats.first_source_ordering_key is None:
        stats.first_source_ordering_key = row.source_ordering_key
    stats.last_source_ordering_key = row.source_ordering_key

    if record.side == 'buy':
        stats.buy_rows += 1
    elif record.side == 'sell':
        stats.sell_rows += 1

    stats.requested_size_raw_total += row.target_volume_raw
    stats.requested_notional_raw_total += row.base_volume_raw
    stats.requested_size_total += record.requested_size
    stats.filled_size_total += record.filled_size
    stats.filled_notional_total += record.filled_notional
    stats.remainder_size_total += record.remainder_size
    stats.pure_book_size_total += float(record.route_breakdown.get('pure_book', 0.0))
    stats.v2_backstop_size_total += row.v2_backstop_routed_size

    if record.filled_size > record.requested_size + OVERFILL_TOLERANCE:
        stats.overfill_rows += 1

    if record.filled_size <= 0:
        stats.zero_fill_rows += 1
    elif record.completion_ratio >= 1.0:
        stats.full_fill_rows += 1
    else:
        stats.partial_fill_rows += 1
    stats.completion_ratio_sum += record.completion_ratio

    if row.fee_covered:
        stats.fee_covered_rows += 1
    else:
        stats.fee_missing_rows += 1

    if record.fee_contract_version:
        stats.precise_fee_rows += 1
        add_record_fee_rollups(stats.fee_rollups, record)

    if row.reference_price_fallback:
        stats.reference_price_fallback_rows += 1

    if row.swap_metadata_covered:
        stats.swap_metadata_covered_rows += 1
    else:
        stats.swap_metadata_missing_rows += 1

    if row.amm_pre_trade_spot_reference_price is None:
        stats.amm_pre_trade_spot_missing_rows += 1
    else:
        stats.amm_pre_trade_spot_supported_rows += 1

    if row.v2_backstop_routed_size > 0:
        stats.routed_rows += 1
    else:
        stats.pure_book_only_rows += 1

    if record.route_breakdown.get('pure_book', 0.0) < record.filled_size and record.completion_ratio >= 1.0:
        stats.hybrid_full_fill_from_backstop_rows += 1

    if record.admissibility_passed is None:
        stats.no_residual_rows += 1
    else:
        stats.residual_rows += 1
        if row.backstop_quote_recovered:
            stats.backstop_quote_recovered_rows += 1
        else:
            stats.backstop_quote_missing_rows += 1
        if record.admissibility_passed:
            stats.admissibility_pass_rows += 1
        else:
            stats.admissibility_fail_rows += 1
        if row.v2_backstop_routed_size <= 0:
            stats.unrouted_residual_rows += 1
        if (
            record.admissibility_passed
            and row.backstop_available_size is not None
            and row.backstop_available_size + OVERFILL_TOLERANCE < row.pure_book_remainder_size
        ):
            stats.available_size_limited_rows += 1

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

    if row.amm_pre_trade_spot_gross_slippage_bps is None:
        return

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
    pure_book_path: Path,
    baseline_path: Path,
    hybrid_rule_path: Path,
    fee_config_path: Path,
    lane_output_path: Path,
    stats: HybridStats,
    hybrid_rule: HybridRule,
    fee_policy: dict[str, Any],
    mapping_fingerprint: str,
) -> dict[str, Any]:
    counts_reconciliation = reconcile_totals(stats.row_count, stats.row_count)
    return {
        'generated_at_utc': utc_now(),
        'lane': LANE_NAME,
        'contract': {
            'lane_mode': 'event_level_hybrid_3b',
            'replay_unit_mapping': 'one_replay_unit_to_one_hybrid_record',
            'canonical_ordering': ['tradeTimestampSeconds', 'swapEventId', 'tradeRowId'],
            'book_fill_basis': 'mounted_3a_pure_book_fill',
            'residual_basis': 'event_level_pure_book_remainder',
            'backstop_quote_basis': 'mounted_v2_realized_execution_price',
            'backstop_route_policy': 'route_residual_only_when_projected_hybrid_slippage_passes',
            'completion_basis': 'filled_size_over_requested_size',
            'slippage_basis': 'reference_price',
            'lambdaplex_parity_proxy_basis': (
                'amm_pre_trade_spot_gross_slippage_bps uses the RH-13 best-supported '
                'AMM pre-trade pool-spot gross convention with a symmetric reference denominator'
            ),
            'fee_treatment': 'route_aware_modeled_from_locked_v2_and_v3_schedules',
        },
        'inputs': {
            'pure_book_path': str(pure_book_path),
            'v2_baseline_path': str(baseline_path),
            'hybrid_rule_path': str(hybrid_rule_path),
            'fee_config_path': str(fee_config_path),
        },
        'rule': hybrid_rule.as_dict(),
        'outputs': {
            'lane_output_path': str(lane_output_path),
        },
        'row_counts': {
            'pure_book_input_rows': stats.row_count,
            'v2_baseline_input_rows': stats.row_count,
            'hybrid_rows': stats.row_count,
            'buy_rows': stats.buy_rows,
            'sell_rows': stats.sell_rows,
        },
        'completion': {
            'full_fill_rows': stats.full_fill_rows,
            'partial_fill_rows': stats.partial_fill_rows,
            'zero_fill_rows': stats.zero_fill_rows,
            'avg_completion_ratio': average(stats.completion_ratio_sum, stats.row_count),
            'hybrid_full_fill_from_backstop_rows': stats.hybrid_full_fill_from_backstop_rows,
        },
        'admissibility': {
            'rows_with_residual': stats.residual_rows,
            'rows_without_residual': stats.no_residual_rows,
            'backstop_quote_recovered_rows': stats.backstop_quote_recovered_rows,
            'backstop_quote_missing_rows': stats.backstop_quote_missing_rows,
            'pass_rows': stats.admissibility_pass_rows,
            'fail_rows': stats.admissibility_fail_rows,
            'pass_rate_on_residual_rows': average(stats.admissibility_pass_rows, stats.residual_rows),
        },
        'route_breakdown': {
            'pure_book_only_rows': stats.pure_book_only_rows,
            'routed_rows': stats.routed_rows,
            'unrouted_residual_rows': stats.unrouted_residual_rows,
            'available_size_limited_rows': stats.available_size_limited_rows,
            'pure_book_size_hbar': format_decimal(stats.pure_book_size_total),
            'v2_backstop_size_hbar': format_decimal(stats.v2_backstop_size_total),
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
            'excluded_zero_fill_rows': stats.slippage_excluded_zero_fill_rows,
            'reference_basis': 'reconstructed_amm_pre_trade_pool_spot',
            'execution_basis': 'gross_lane_avg_execution_price',
            'denominator': 'symmetric_reference_price',
            'status': 'parity_proxy_only',
        },
        'totals': {
            'requested_size_hbar': format_scaled_int(stats.requested_size_raw_total, 8),
            'requested_notional_usdc': format_scaled_int(stats.requested_notional_raw_total, 6),
            'filled_size_hbar': format_decimal(stats.filled_size_total),
            'filled_notional_usdc': format_decimal(stats.filled_notional_total),
            'remainder_size_hbar': format_decimal(stats.remainder_size_total),
            'pure_book_size_hbar': format_decimal(stats.pure_book_size_total),
            'v2_backstop_size_hbar': format_decimal(stats.v2_backstop_size_total),
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
            **build_fee_summary_payload(
                fee_rollups=stats.fee_rollups,
                requested_notional_total=stats.requested_notional_raw_total / 1_000_000,
                default_scenario_id=default_v3_scenario_id(fee_policy),
                supported_scenarios=v3_supported_scenarios(fee_policy),
            ),
            'policy': fee_policy,
            'caveat': FEE_CAVEAT,
        },
        'mapping': {
            'first_replay_unit_id': stats.first_replay_unit_id,
            'last_replay_unit_id': stats.last_replay_unit_id,
            'first_source_ordering_key': stats.first_source_ordering_key,
            'last_source_ordering_key': stats.last_source_ordering_key,
            'fingerprint': mapping_fingerprint,
            'one_to_one_mapping_verified': True,
            'row_count': stats.row_count,
        },
        'reconciliation': {
            **counts_reconciliation,
            'hybrid_count': stats.row_count,
            'hybrid_count_matches_pure_book': True,
            'hybrid_count_matches_v2_baseline': True,
            'input_alignment_verified': True,
            'filled_plus_remainder_matches_requested_size': nearly_equal(
                stats.filled_size_total + stats.remainder_size_total,
                stats.requested_size_total,
            ),
            'no_overfill_rows': stats.overfill_rows == 0,
            'overfill_rows': stats.overfill_rows,
        },
        'caveats': build_caveats(stats, hybrid_rule),
    }



def build_manifest(
    *,
    pure_book_path: Path,
    baseline_path: Path,
    hybrid_rule_path: Path,
    fee_config_path: Path,
    lane_output_path: Path,
    summary_path: Path,
    stats: HybridStats,
    hybrid_rule: HybridRule,
    fee_policy: dict[str, Any],
    summary: dict[str, Any],
    mapping_fingerprint: str,
) -> dict[str, Any]:
    return {
        'generated_at_utc': utc_now(),
        'lane': LANE_NAME,
        'contract': summary['contract'],
        'inputs': {
            'pure_book_path': str(pure_book_path),
            'pure_book_bytes': pure_book_path.stat().st_size,
            'v2_baseline_path': str(baseline_path),
            'v2_baseline_bytes': baseline_path.stat().st_size,
            'hybrid_rule_path': str(hybrid_rule_path),
            'hybrid_rule_bytes': hybrid_rule_path.stat().st_size,
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
        'rule': hybrid_rule.as_dict(),
        'row_counts': summary['row_counts'],
        'admissibility': summary['admissibility'],
        'route_breakdown': summary['route_breakdown'],
        'mapping': {
            'fingerprint': mapping_fingerprint,
            'one_to_one_mapping_verified': True,
            'row_count': stats.row_count,
            'input_alignment_verified': True,
        },
        'reconciliation': summary['reconciliation'],
        'fees': {
            **summary['fees'],
            'policy': fee_policy,
        },
        'caveats': build_caveats(stats, hybrid_rule),
    }



def build_caveats(stats: HybridStats, hybrid_rule: HybridRule) -> list[str]:
    caveats = [
        FEE_CAVEAT,
        '3B reuses the mounted RH-05 pure-book lane and mounted RH-04 realized V2 baseline as '
        'read-only inputs in the normal rerun path; it does not rebuild normalization, baseline, or '
        'pure-book artifacts during hybrid materialization.',
        'Under the event-level contract, residual means the remainder of the event-level replay unit '
        'after the mounted 3A pure-book fill; it is not a recovered multi-event user-order residual.',
        'The mounted V2 baseline supplies a recoverable historical V2 proxy quote per replay unit. '
        '3B only routes residual size to that backstop when the frozen admissibility rule passes on the '
        'projected hybrid average execution price after the mounted 3A fill plus candidate routed residual.',
        f'The frozen first-pass admissibility rule uses buy={format_decimal(hybrid_rule.max_buy_slippage_bps)} '
        f'bps and sell={format_decimal(hybrid_rule.max_sell_slippage_bps)} bps maximum realized slippage '
        'versus the replay-unit reference price, evaluated on the projected hybrid average execution price '
        'rather than the raw backstop quote in isolation.',
        'The added `amm_pre_trade_spot_gross_slippage_bps` field is a Lambdaplex-parity proxy only. '
        'It uses the RH-13 best-supported reconstructed AMM pre-trade pool spot plus a symmetric '
        'reference denominator and does not replace the canonical reference-price study metric.',
    ]
    if stats.unrouted_residual_rows > 0:
        caveats.append(
            f'{stats.unrouted_residual_rows} residual replay unit(s) remain partially filled or unfilled '
            'after 3B because the backstop quote was missing, the admissibility rule failed, or the '
            'recoverable quote size was smaller than the residual. completion_ratio and remainder_size '
            'preserve that outcome explicitly; the lane does not force completion to 1.0.'
        )
    if stats.backstop_quote_missing_rows > 0:
        caveats.append(
            f'{stats.backstop_quote_missing_rows} residual replay unit(s) had no recoverable V2 proxy quote '
            'in the mounted baseline input and therefore remained unfilled under the locked failure policy.'
        )
    if stats.available_size_limited_rows > 0:
        caveats.append(
            f'{stats.available_size_limited_rows} residual replay unit(s) only partially routed to the V2 '
            'backstop because the recoverable quote size was smaller than the pure-book residual.'
        )
    if stats.slippage_excluded_zero_fill_rows > 0:
        caveats.append(
            f'{stats.slippage_excluded_zero_fill_rows} zero-fill replay unit(s) are excluded from slippage '
            'averages because no hybrid execution occurred.'
        )
    if stats.infinite_slippage_rows > 0:
        caveats.append(
            f'{stats.infinite_slippage_rows} replay unit(s) have non-finite hybrid slippage and are excluded '
            'from finite slippage averages.'
        )
    if stats.amm_pre_trade_spot_missing_rows > 0:
        caveats.append(
            f'{stats.amm_pre_trade_spot_missing_rows} replay unit(s) do not have enough raw swap-state '
            'fields to support the AMM pre-trade spot parity proxy and remain blank for that metric family.'
        )
    return caveats



def _require_inputs(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing hybrid lane inputs: {", ".join(missing)}')

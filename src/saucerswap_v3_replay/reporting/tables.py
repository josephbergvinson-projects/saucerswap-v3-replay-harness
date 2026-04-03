from __future__ import annotations

import json
from typing import Any

from ..benchmarks.lambdaplex import PublishedBenchmarkStatus
from ..metrics.summaries import RollupSummary
from ..normalize.events import format_decimal, format_scaled_int
from .fee_views import FeeRollupSummary
from .spread_capture_views import SpreadCaptureRollupSummary

AGGREGATE_FIELDNAMES = [
    'lane',
    'lane_label',
    'data_status',
    'row_count',
    'requested_size_hbar',
    'requested_notional_usdc',
    'filled_size_hbar',
    'filled_notional_usdc',
    'remainder_size_hbar',
    'fill_rate',
    'avg_completion_ratio',
    'avg_slippage_bps',
    'avg_abs_slippage_bps',
    'avg_amm_pre_trade_spot_gross_slippage_bps',
    'avg_abs_amm_pre_trade_spot_gross_slippage_bps',
    'finite_slippage_rows',
    'non_finite_slippage_rows',
    'finite_amm_pre_trade_spot_gross_slippage_rows',
    'non_finite_amm_pre_trade_spot_gross_slippage_rows',
    'full_fill_rows',
    'partial_fill_rows',
    'zero_fill_rows',
    'fee_covered_rows',
    'fee_missing_rows',
    'admissibility_pass_rows',
    'admissibility_fail_rows',
    'admissibility_unknown_rows',
    'fee_precision',
    'benchmark_comparable',
    'source_notes_path',
    'published_headline_metrics',
    'benchmark_provenance',
    'notes',
]

SEGMENT_FIELDNAMES = [
    'segment',
    'lane',
    'lane_label',
    'row_count',
    'requested_size_hbar',
    'requested_notional_usdc',
    'filled_size_hbar',
    'filled_notional_usdc',
    'remainder_size_hbar',
    'fill_rate',
    'avg_completion_ratio',
    'avg_slippage_bps',
    'avg_abs_slippage_bps',
    'avg_amm_pre_trade_spot_gross_slippage_bps',
    'avg_abs_amm_pre_trade_spot_gross_slippage_bps',
    'finite_slippage_rows',
    'non_finite_slippage_rows',
    'finite_amm_pre_trade_spot_gross_slippage_rows',
    'non_finite_amm_pre_trade_spot_gross_slippage_rows',
    'full_fill_rows',
    'partial_fill_rows',
    'zero_fill_rows',
    'fee_covered_rows',
    'fee_missing_rows',
    'admissibility_pass_rows',
    'admissibility_fail_rows',
    'admissibility_unknown_rows',
]

FEE_AGGREGATE_FIELDNAMES = [
    'lane',
    'lane_label',
    'row_count',
    'requested_notional_usdc',
    'fee_basis_filled_notional_usd',
    'trader_fee_paid_usd',
    'active_lp_fee_earned_usd',
    'maker_rebate_earned_usd',
    'liquidity_side_fee_earned_usd',
    'protocol_fee_earned_usd',
    'execution_shortfall_usd',
    'all_in_trader_cost_usd',
    'trader_fee_paid_bps_on_requested_notional',
    'trader_fee_paid_bps_on_filled_notional',
    'liquidity_side_fee_earned_bps_on_requested_notional',
    'protocol_fee_earned_bps_on_requested_notional',
    'execution_shortfall_bps_on_requested_notional',
    'all_in_trader_cost_bps_on_requested_notional',
    'v3_min_order_ineligible_rows',
    'fee_precision',
    'notes',
]

FEE_SEGMENT_FIELDNAMES = [
    'segment',
    'lane',
    'lane_label',
    'row_count',
    'requested_notional_usdc',
    'fee_basis_filled_notional_usd',
    'trader_fee_paid_usd',
    'active_lp_fee_earned_usd',
    'maker_rebate_earned_usd',
    'liquidity_side_fee_earned_usd',
    'protocol_fee_earned_usd',
    'execution_shortfall_usd',
    'all_in_trader_cost_usd',
    'trader_fee_paid_bps_on_requested_notional',
    'trader_fee_paid_bps_on_filled_notional',
    'liquidity_side_fee_earned_bps_on_requested_notional',
    'protocol_fee_earned_bps_on_requested_notional',
    'execution_shortfall_bps_on_requested_notional',
    'all_in_trader_cost_bps_on_requested_notional',
    'v3_min_order_ineligible_rows',
]

FEE_SCENARIO_FIELDNAMES = [
    'lane',
    'lane_label',
    'scenario_id',
    'row_count',
    'requested_notional_usdc',
    'fee_basis_filled_notional_usd',
    'trader_fee_paid_usd',
    'active_lp_fee_earned_usd',
    'maker_rebate_earned_usd',
    'liquidity_side_fee_earned_usd',
    'protocol_fee_earned_usd',
    'execution_shortfall_usd',
    'all_in_trader_cost_usd',
    'trader_fee_paid_bps_on_requested_notional',
    'trader_fee_paid_bps_on_filled_notional',
    'liquidity_side_fee_earned_bps_on_requested_notional',
    'protocol_fee_earned_bps_on_requested_notional',
    'execution_shortfall_bps_on_requested_notional',
    'all_in_trader_cost_bps_on_requested_notional',
    'v3_min_order_ineligible_rows',
    'notes',
]

SPREAD_CAPTURE_AGGREGATE_FIELDNAMES = [
    'lane',
    'lane_label',
    'row_count',
    'resting_book_fill_rows',
    'zero_resting_book_fill_rows',
    'requested_notional_usdc',
    'resting_book_filled_size_hbar',
    'resting_book_filled_notional_usd',
    'gross_spread_capture_usd',
    'gross_spread_capture_bps_on_requested_notional',
    'gross_spread_capture_bps_on_resting_book_filled_notional',
    'notes',
]

SPREAD_CAPTURE_SEGMENT_FIELDNAMES = [
    'segment',
    'lane',
    'lane_label',
    'row_count',
    'resting_book_fill_rows',
    'zero_resting_book_fill_rows',
    'requested_notional_usdc',
    'resting_book_filled_size_hbar',
    'resting_book_filled_notional_usd',
    'gross_spread_capture_usd',
    'gross_spread_capture_bps_on_requested_notional',
    'gross_spread_capture_bps_on_resting_book_filled_notional',
]


def build_aggregate_rows(
    *,
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_rollups: dict[str, RollupSummary],
    lane_fee_precision: dict[str, str],
    lane_notes: dict[str, str],
    benchmark_status: PublishedBenchmarkStatus,
) -> list[dict[str, str]]:
    rows = [
        build_rollup_row(
            lane=lane,
            lane_label=lane_labels[lane],
            rollup=lane_rollups[lane],
            fee_precision=lane_fee_precision.get(lane, ''),
            notes=lane_notes.get(lane, ''),
        )
        for lane in lane_order
        if lane in lane_rollups
    ]
    rows.append(build_benchmark_row(benchmark_status))
    return rows


def build_segment_rows(
    *,
    segment_order: list[str],
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_segment_rollups: dict[str, dict[str, RollupSummary]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for segment in segment_order:
        for lane in lane_order:
            rollup = lane_segment_rollups.get(lane, {}).get(segment)
            if rollup is None:
                continue
            rows.append(
                {
                    'segment': segment,
                    'lane': lane,
                    'lane_label': lane_labels[lane],
                    **rollup_metrics(rollup),
                }
            )
    return rows


def build_fee_aggregate_rows(
    *,
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_fee_rollups: dict[str, FeeRollupSummary],
    lane_fee_precision: dict[str, str],
    lane_notes: dict[str, str],
) -> list[dict[str, str]]:
    return [
        build_fee_rollup_row(
            lane=lane,
            lane_label=lane_labels[lane],
            rollup=lane_fee_rollups[lane],
            fee_precision=lane_fee_precision.get(lane, ''),
            notes=lane_notes.get(lane, ''),
        )
        for lane in lane_order
        if lane in lane_fee_rollups
    ]


def build_fee_segment_rows(
    *,
    segment_order: list[str],
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_segment_rollups: dict[str, dict[str, FeeRollupSummary]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for segment in segment_order:
        for lane in lane_order:
            rollup = lane_segment_rollups.get(lane, {}).get(segment)
            if rollup is None:
                continue
            rows.append(
                {
                    'segment': segment,
                    'lane': lane,
                    'lane_label': lane_labels[lane],
                    **fee_rollup_metrics(rollup),
                }
            )
    return rows


def build_fee_scenario_rows(
    *,
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_scenario_rollups: dict[str, dict[str, FeeRollupSummary]],
    scenario_order: list[str],
    lane_notes: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for lane in lane_order:
        scenario_rollups = lane_scenario_rollups.get(lane, {})
        for scenario_id in scenario_order:
            rollup = scenario_rollups.get(scenario_id)
            if rollup is None:
                continue
            rows.append(
                {
                    'lane': lane,
                    'lane_label': lane_labels[lane],
                    'scenario_id': scenario_id,
                    **fee_rollup_metrics(rollup),
                    'notes': lane_notes.get(lane, ''),
                }
            )
    return rows


def build_spread_capture_aggregate_rows(
    *,
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_spread_capture_rollups: dict[str, SpreadCaptureRollupSummary],
    lane_notes: dict[str, str],
) -> list[dict[str, str]]:
    return [
        build_spread_capture_rollup_row(
            lane=lane,
            lane_label=lane_labels[lane],
            rollup=lane_spread_capture_rollups[lane],
            notes=lane_notes.get(lane, ''),
        )
        for lane in lane_order
        if lane in lane_spread_capture_rollups
    ]


def build_spread_capture_segment_rows(
    *,
    segment_order: list[str],
    lane_order: list[str],
    lane_labels: dict[str, str],
    lane_segment_rollups: dict[str, dict[str, SpreadCaptureRollupSummary]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for segment in segment_order:
        for lane in lane_order:
            rollup = lane_segment_rollups.get(lane, {}).get(segment)
            if rollup is None:
                continue
            rows.append(
                {
                    'segment': segment,
                    'lane': lane,
                    'lane_label': lane_labels[lane],
                    **spread_capture_rollup_metrics(rollup),
                }
            )
    return rows


def build_rollup_row(
    *,
    lane: str,
    lane_label: str,
    rollup: RollupSummary,
    fee_precision: str,
    notes: str,
) -> dict[str, str]:
    return {
        'lane': lane,
        'lane_label': lane_label,
        'data_status': 'materialized',
        **rollup_metrics(rollup),
        'fee_precision': fee_precision,
        'benchmark_comparable': '',
        'source_notes_path': '',
        'published_headline_metrics': '',
        'benchmark_provenance': '',
        'notes': notes,
    }


def build_fee_rollup_row(
    *,
    lane: str,
    lane_label: str,
    rollup: FeeRollupSummary,
    fee_precision: str,
    notes: str,
) -> dict[str, str]:
    return {
        'lane': lane,
        'lane_label': lane_label,
        **fee_rollup_metrics(rollup),
        'fee_precision': fee_precision,
        'notes': notes,
    }


def build_spread_capture_rollup_row(
    *,
    lane: str,
    lane_label: str,
    rollup: SpreadCaptureRollupSummary,
    notes: str,
) -> dict[str, str]:
    return {
        'lane': lane,
        'lane_label': lane_label,
        **spread_capture_rollup_metrics(rollup),
        'notes': notes,
    }


def build_benchmark_row(benchmark_status: PublishedBenchmarkStatus) -> dict[str, str]:
    headline_metrics = ''
    if benchmark_status.headline_metrics:
        headline_metrics = json.dumps(benchmark_status.headline_metrics, sort_keys=True)

    note_parts = []
    if benchmark_status.comparable:
        note_parts.append('External published benchmark panel; comparable headline metrics merged from the local benchmark payload.')
    else:
        note_parts.append('Published panel is placeholder or incomplete; no comparable benchmark metrics were merged.')
    if benchmark_status.notes_summary:
        note_parts.append(benchmark_status.notes_summary)

    row = {
        'lane': 'lambdaplex_published',
        'lane_label': 'Lambdaplex published panel',
        'data_status': benchmark_status.status,
        **build_benchmark_metric_text(
            benchmark_status.comparable_headline_metrics if benchmark_status.comparable else {}
        ),
        'fee_precision': '',
        'benchmark_comparable': 'true' if benchmark_status.comparable else 'false',
        'source_notes_path': benchmark_status.source_notes_path,
        'published_headline_metrics': headline_metrics,
        'benchmark_provenance': benchmark_status.provenance.summary,
        'notes': ' '.join(note_parts).strip(),
    }
    return row


def build_benchmark_metric_text(metrics: dict[str, int | float]) -> dict[str, str]:
    row = {field: '' for field in rollup_metrics_fieldnames()}
    for field, value in metrics.items():
        if field in {
            'row_count',
            'finite_slippage_rows',
            'non_finite_slippage_rows',
            'full_fill_rows',
            'partial_fill_rows',
            'zero_fill_rows',
            'fee_covered_rows',
            'fee_missing_rows',
            'admissibility_pass_rows',
            'admissibility_fail_rows',
            'admissibility_unknown_rows',
        }:
            row[field] = str(int(value))
        else:
            row[field] = format_decimal(float(value))
    return row


def rollup_metrics_fieldnames() -> tuple[str, ...]:
    return (
        'row_count',
        'requested_size_hbar',
        'requested_notional_usdc',
        'filled_size_hbar',
        'filled_notional_usdc',
        'remainder_size_hbar',
        'fill_rate',
        'avg_completion_ratio',
        'avg_slippage_bps',
        'avg_abs_slippage_bps',
        'avg_amm_pre_trade_spot_gross_slippage_bps',
        'avg_abs_amm_pre_trade_spot_gross_slippage_bps',
        'finite_slippage_rows',
        'non_finite_slippage_rows',
        'finite_amm_pre_trade_spot_gross_slippage_rows',
        'non_finite_amm_pre_trade_spot_gross_slippage_rows',
        'full_fill_rows',
        'partial_fill_rows',
        'zero_fill_rows',
        'fee_covered_rows',
        'fee_missing_rows',
        'admissibility_pass_rows',
        'admissibility_fail_rows',
        'admissibility_unknown_rows',
    )


def rollup_metrics(rollup: RollupSummary) -> dict[str, str]:
    parity_metric_available = (
        rollup.finite_amm_pre_trade_spot_gross_slippage_rows
        + rollup.non_finite_amm_pre_trade_spot_gross_slippage_rows
    ) > 0
    return {
        'row_count': str(rollup.row_count),
        'requested_size_hbar': format_scaled_int(rollup.requested_size_raw_total, 8),
        'requested_notional_usdc': format_scaled_int(rollup.requested_notional_raw_total, 6),
        'filled_size_hbar': format_decimal(rollup.filled_size_total),
        'filled_notional_usdc': format_decimal(rollup.filled_notional_total),
        'remainder_size_hbar': format_decimal(rollup.remainder_size_total),
        'fill_rate': format_decimal(rollup.fill_rate),
        'avg_completion_ratio': format_decimal(rollup.avg_completion_ratio),
        'avg_slippage_bps': format_decimal(rollup.avg_slippage_bps),
        'avg_abs_slippage_bps': format_decimal(rollup.avg_abs_slippage_bps),
        'avg_amm_pre_trade_spot_gross_slippage_bps': (
            format_decimal(rollup.avg_amm_pre_trade_spot_gross_slippage_bps) if parity_metric_available else ''
        ),
        'avg_abs_amm_pre_trade_spot_gross_slippage_bps': (
            format_decimal(rollup.avg_abs_amm_pre_trade_spot_gross_slippage_bps) if parity_metric_available else ''
        ),
        'finite_slippage_rows': str(rollup.finite_slippage_rows),
        'non_finite_slippage_rows': str(rollup.non_finite_slippage_rows),
        'finite_amm_pre_trade_spot_gross_slippage_rows': str(rollup.finite_amm_pre_trade_spot_gross_slippage_rows),
        'non_finite_amm_pre_trade_spot_gross_slippage_rows': str(
            rollup.non_finite_amm_pre_trade_spot_gross_slippage_rows
        ),
        'full_fill_rows': str(rollup.full_fill_rows),
        'partial_fill_rows': str(rollup.partial_fill_rows),
        'zero_fill_rows': str(rollup.zero_fill_rows),
        'fee_covered_rows': str(rollup.fee_covered_rows),
        'fee_missing_rows': str(rollup.fee_missing_rows),
        'admissibility_pass_rows': str(rollup.admissibility_pass_rows),
        'admissibility_fail_rows': str(rollup.admissibility_fail_rows),
        'admissibility_unknown_rows': str(rollup.admissibility_unknown_rows),
    }


def fee_rollup_metrics(rollup: FeeRollupSummary) -> dict[str, str]:
    return {
        'row_count': str(rollup.row_count),
        'requested_notional_usdc': format_scaled_int(rollup.requested_notional_raw_total, 6),
        'fee_basis_filled_notional_usd': format_decimal(rollup.fee_basis_filled_notional_total),
        'trader_fee_paid_usd': format_decimal(rollup.trader_fee_paid_total),
        'active_lp_fee_earned_usd': format_decimal(rollup.active_lp_fee_earned_total),
        'maker_rebate_earned_usd': format_decimal(rollup.maker_rebate_earned_total),
        'liquidity_side_fee_earned_usd': format_decimal(rollup.liquidity_side_fee_earned_total),
        'protocol_fee_earned_usd': format_decimal(rollup.protocol_fee_earned_total),
        'execution_shortfall_usd': format_decimal(rollup.execution_shortfall_total),
        'all_in_trader_cost_usd': format_decimal(rollup.all_in_trader_cost_total),
        'trader_fee_paid_bps_on_requested_notional': format_decimal(
            rollup.trader_fee_paid_bps_on_requested_notional
        ),
        'trader_fee_paid_bps_on_filled_notional': format_decimal(rollup.trader_fee_paid_bps_on_filled_notional),
        'liquidity_side_fee_earned_bps_on_requested_notional': format_decimal(
            rollup.liquidity_side_fee_earned_bps_on_requested_notional
        ),
        'protocol_fee_earned_bps_on_requested_notional': format_decimal(
            rollup.protocol_fee_earned_bps_on_requested_notional
        ),
        'execution_shortfall_bps_on_requested_notional': format_decimal(
            rollup.execution_shortfall_bps_on_requested_notional
        ),
        'all_in_trader_cost_bps_on_requested_notional': format_decimal(
            rollup.all_in_trader_cost_bps_on_requested_notional
        ),
        'v3_min_order_ineligible_rows': str(rollup.v3_min_order_ineligible_rows),
    }


def spread_capture_rollup_metrics(rollup: SpreadCaptureRollupSummary) -> dict[str, str]:
    return {
        'row_count': str(rollup.row_count),
        'resting_book_fill_rows': str(rollup.resting_book_fill_rows),
        'zero_resting_book_fill_rows': str(rollup.zero_resting_book_fill_rows),
        'requested_notional_usdc': format_scaled_int(rollup.requested_notional_raw_total, 6),
        'resting_book_filled_size_hbar': format_decimal(rollup.resting_book_filled_size_total),
        'resting_book_filled_notional_usd': format_decimal(rollup.resting_book_filled_notional_total),
        'gross_spread_capture_usd': format_decimal(rollup.gross_spread_capture_total),
        'gross_spread_capture_bps_on_requested_notional': format_decimal(
            rollup.gross_spread_capture_bps_on_requested_notional
        ),
        'gross_spread_capture_bps_on_resting_book_filled_notional': format_decimal(
            rollup.gross_spread_capture_bps_on_resting_book_filled_notional
        ),
    }


def render_final_comparison_report(
    *,
    aggregate_rows: list[dict[str, str]],
    fee_aggregate_rows: list[dict[str, str]],
    spread_capture_aggregate_rows: list[dict[str, str]],
    side_rows: list[dict[str, str]],
    fee_side_rows: list[dict[str, str]],
    bucket_rows: list[dict[str, str]],
    fee_bucket_rows: list[dict[str, str]],
    fee_scenario_rows: list[dict[str, str]],
    benchmark_status: PublishedBenchmarkStatus,
    caveats: list[str],
) -> str:
    headline_rows = [
        row
        for row in aggregate_rows
        if row['lane'] != 'lambdaplex_published' or benchmark_status.comparable
    ]
    benchmark_rows = [row for row in aggregate_rows if row['lane'] == 'lambdaplex_published']

    lines = ['# Final Comparison Report', '', '## Study caveats', '']
    for caveat in caveats:
        lines.append(f'- {caveat}')

    lines.extend(
        [
            '',
            '## Headline lane comparison',
            '',
            render_markdown_table(
                headline_rows,
                [
                    ('Lane', 'lane_label'),
                    ('Rows', 'row_count'),
                    ('Fill rate', 'fill_rate'),
                    ('Avg completion', 'avg_completion_ratio'),
                    ('Avg study slippage (bps)', 'avg_slippage_bps'),
                    ('Avg parity proxy slippage (bps)', 'avg_amm_pre_trade_spot_gross_slippage_bps'),
                    ('Remainder (HBAR)', 'remainder_size_hbar'),
                    ('Notes', 'notes'),
                ],
            ),
            '',
            '## Fee-inclusive economics',
            '',
            render_markdown_table(
                fee_aggregate_rows,
                [
                    ('Lane', 'lane_label'),
                    ('Trader fee (USD)', 'trader_fee_paid_usd'),
                    ('Liquidity-side earnings (USD)', 'liquidity_side_fee_earned_usd'),
                    ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
                    ('Execution shortfall (USD)', 'execution_shortfall_usd'),
                    ('All-in trader cost (USD)', 'all_in_trader_cost_usd'),
                    ('Trader fee (bps, requested)', 'trader_fee_paid_bps_on_requested_notional'),
                    ('All-in cost (bps, requested)', 'all_in_trader_cost_bps_on_requested_notional'),
                    ('Notes', 'notes'),
                ],
            ),
            '',
            '## Gross spread capture proxy',
            '',
            'Filled resting-book leg only for 3A and the pure-book leg of 3B. This is a study-reference spread-capture proxy, not full maker PnL, not explicit LP fee accrual, and not V3 maker rebate.',
            '',
            render_markdown_table(
                spread_capture_aggregate_rows,
                [
                    ('Lane', 'lane_label'),
                    ('Rows', 'row_count'),
                    ('Book-leg fill rows', 'resting_book_fill_rows'),
                    ('Book-leg filled notional (USD)', 'resting_book_filled_notional_usd'),
                    ('Gross spread capture (USD)', 'gross_spread_capture_usd'),
                    ('Gross spread capture (bps, book leg)', 'gross_spread_capture_bps_on_resting_book_filled_notional'),
                    ('Notes', 'notes'),
                ],
            ),
            '',
            'Exact figures require materialized `data/processed/lane_3a_pure_book.csv` and `data/processed/lane_3b_hybrid.csv`. If those row-level outputs are absent in the mounted checkout, rerun `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli pure-book --root .`, `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid --root .`, and `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root .`.',
            '',
            '## Side split',
            '',
            render_markdown_table(
                side_rows,
                [
                    ('Side', 'segment'),
                    ('Lane', 'lane_label'),
                    ('Rows', 'row_count'),
                    ('Fill rate', 'fill_rate'),
                    ('Avg completion', 'avg_completion_ratio'),
                    ('Avg study slippage (bps)', 'avg_slippage_bps'),
                    ('Avg parity proxy slippage (bps)', 'avg_amm_pre_trade_spot_gross_slippage_bps'),
                ],
            ),
            '',
            '## Fee side split',
            '',
            render_markdown_table(
                fee_side_rows,
                [
                    ('Side', 'segment'),
                    ('Lane', 'lane_label'),
                    ('Trader fee (USD)', 'trader_fee_paid_usd'),
                    ('Liquidity-side earnings (USD)', 'liquidity_side_fee_earned_usd'),
                    ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
                    ('All-in cost (bps, requested)', 'all_in_trader_cost_bps_on_requested_notional'),
                ],
            ),
            '',
            '## Bucket split',
            '',
            render_markdown_table(
                bucket_rows,
                [
                    ('Bucket', 'segment'),
                    ('Lane', 'lane_label'),
                    ('Rows', 'row_count'),
                    ('Requested notional (USDC)', 'requested_notional_usdc'),
                    ('Fill rate', 'fill_rate'),
                    ('Avg completion', 'avg_completion_ratio'),
                    ('Avg study slippage (bps)', 'avg_slippage_bps'),
                    ('Avg parity proxy slippage (bps)', 'avg_amm_pre_trade_spot_gross_slippage_bps'),
                ],
            ),
            '',
            '## Fee bucket split',
            '',
            render_markdown_table(
                fee_bucket_rows,
                [
                    ('Bucket', 'segment'),
                    ('Lane', 'lane_label'),
                    ('Trader fee (USD)', 'trader_fee_paid_usd'),
                    ('Liquidity-side earnings (USD)', 'liquidity_side_fee_earned_usd'),
                    ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
                    ('All-in cost (bps, requested)', 'all_in_trader_cost_bps_on_requested_notional'),
                ],
            ),
            '',
            '## xSAUCE fee scenario sensitivity',
            '',
            render_markdown_table(
                fee_scenario_rows,
                [
                    ('Lane', 'lane_label'),
                    ('Scenario', 'scenario_id'),
                    ('Trader fee (USD)', 'trader_fee_paid_usd'),
                    ('Liquidity-side earnings (USD)', 'liquidity_side_fee_earned_usd'),
                    ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
                    ('All-in cost (bps, requested)', 'all_in_trader_cost_bps_on_requested_notional'),
                    ('Notes', 'notes'),
                ],
            ),
            '',
            '## Benchmark panel status',
            '',
            render_markdown_table(
                benchmark_rows,
                [
                    ('Benchmark', 'lane_label'),
                    ('Status', 'data_status'),
                    ('Comparable', 'benchmark_comparable'),
                    ('Source notes', 'source_notes_path'),
                    ('Published headline metrics', 'published_headline_metrics'),
                    ('Provenance', 'benchmark_provenance'),
                    ('Notes', 'notes'),
                ],
            ),
            '',
            f'Lambdaplex market: `{benchmark_status.market}`',
            f'Lambdaplex benchmark schema: `{benchmark_status.schema_version}`',
        ]
    )
    return '\n'.join(lines) + '\n'


def render_reconciliation_report(
    *,
    reconciliation_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
) -> str:
    lines = [
        '# Reconciliation Report',
        '',
        '## Mounted artifact checks',
        '',
        render_markdown_table(
            reconciliation_rows,
            [
                ('Lane', 'lane_label'),
                ('Rows', 'row_count'),
                ('Counts match', 'counts_match'),
                ('Size check', 'size_check'),
                ('Alignment check', 'alignment_check'),
                ('Mapping fingerprint', 'mapping_fingerprint'),
            ],
        ),
        '',
        '## Input surfaces',
        '',
        render_markdown_table(
            source_rows,
            [
                ('Lane', 'lane_label'),
                ('Lane CSV', 'lane_csv'),
                ('Summary JSON', 'summary_json'),
                ('Manifest JSON', 'manifest_json'),
            ],
        ),
    ]
    return '\n'.join(lines) + '\n'


def render_validation_report(
    *,
    validation_rows: list[dict[str, str]],
    global_checks: list[str],
) -> str:
    lines = [
        '# Validation Report',
        '',
        '## Rollup validation',
        '',
        render_markdown_table(
            validation_rows,
            [
                ('Lane', 'lane_label'),
                ('Rows', 'row_count_matches'),
                ('Requested totals', 'requested_totals_match'),
                ('Filled totals', 'filled_totals_match'),
                ('Completion counts', 'completion_counts_match'),
                ('Fee coverage', 'fee_coverage_match'),
                ('Fee rollup', 'default_fee_rollup_match'),
                ('Status', 'status'),
            ],
        ),
        '',
        '## Global checks',
        '',
    ]
    for check in global_checks:
        lines.append(f'- {check}')
    return '\n'.join(lines) + '\n'


def render_validation_polish_report(
    *,
    caveats: list[str],
    rollup_validation_rows: list[dict[str, str]],
    global_checks: list[str],
    sample_rows: list[dict[str, str]],
    golden_rows: list[dict[str, str]],
    artifact_rows: list[dict[str, str]],
) -> str:
    lines = ['# Validation Report', '', '## Study caveats', '']
    for caveat in caveats:
        lines.append(f'- {caveat}')

    lines.extend(
        [
            '',
            '## Rollup validation',
            '',
            render_markdown_table(
                rollup_validation_rows,
                [
                    ('Lane', 'lane_label'),
                    ('Rows', 'row_count_matches'),
                    ('Requested totals', 'requested_totals_match'),
                    ('Filled totals', 'filled_totals_match'),
                    ('Completion counts', 'completion_counts_match'),
                    ('Fee coverage', 'fee_coverage_match'),
                    ('Fee rollup', 'default_fee_rollup_match'),
                    ('Status', 'status'),
                ],
            ),
            '',
            '## Global checks',
            '',
        ]
    )
    for check in global_checks:
        lines.append(f'- {check}')

    lines.extend(
        [
            '',
            '## Sampled realized-V2 sanity pack',
            '',
            'First observed row per populated `side x requested_notional bucket` segment from mounted `data/processed/lane_v2_baseline.csv`.',
            '',
            render_markdown_table(
                sample_rows,
                [
                    ('Segment', 'segment'),
                    ('Rows in segment', 'rows_in_segment'),
                    ('Replay unit', 'replay_unit_id'),
                    ('Requested notional (USDC)', 'requested_notional'),
                    ('Source ordering key', 'source_ordering_key'),
                    ('Checks', 'check_summary'),
                    ('Status', 'status'),
                ],
            ),
            '',
            '## Toy golden cases',
            '',
            'Fixture inputs: `tests/fixtures/toy_book.yaml`, `tests/fixtures/toy_flow.csv`, `tests/fixtures/toy_expected_outputs.json`.',
            '',
            render_markdown_table(
                golden_rows,
                [
                    ('Case', 'name'),
                    ('Lane', 'lane'),
                    ('Replay unit', 'replay_unit_id'),
                    ('Completion ratio', 'completion_ratio'),
                    ('Remainder size', 'remainder_size'),
                    ('Admissibility', 'admissibility_passed'),
                    ('Checks', 'check_summary'),
                    ('Status', 'status'),
                ],
            ),
            '',
            '## Generated artifacts',
            '',
            render_markdown_table(
                artifact_rows,
                [
                    ('Artifact', 'artifact'),
                    ('Path', 'path'),
                    ('Status', 'status'),
                    ('Fingerprint', 'fingerprint'),
                ],
            ),
        ]
    )
    return '\n'.join(lines) + '\n'


def render_markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    headers = [label for label, _ in columns]
    divider = ['---'] * len(columns)
    lines = [
        '| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join(divider) + ' |',
    ]
    for row in rows:
        values = [escape_markdown_cell(row.get(key, '')) for _, key in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def escape_markdown_cell(value: Any) -> str:
    text = str(value)
    if not text:
        return ''
    return text.replace('|', '\\|')

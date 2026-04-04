#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = ROOT / 'artifacts' / 'rh09-benchmark-20260325' / 'reporting-root'
CURRENT_REPORT_PATH = ROOT / 'reports' / 'final-comparison.md'
OUTPUT_DIR = ROOT / 'artifacts' / 'rh23-report-v2'
REPORT_PATH = ROOT / 'reports' / 'final-comparison-v2.md'


@dataclass(frozen=True)
class SegmentRow:
    segment: str
    lane: str
    lane_label: str
    row_count: int
    requested_notional_usdc: float
    filled_notional_usdc: float
    fill_rate: float
    avg_completion_ratio: float
    avg_slippage_bps: float


@dataclass(frozen=True)
class FeeRow:
    segment: str
    lane: str
    lane_label: str
    row_count: int
    requested_notional_usdc: float
    fee_basis_filled_notional_usd: float
    pure_book_filled_notional_usdc: float
    v2_backstop_filled_notional_usdc: float
    trader_fee_paid_usd: float
    maker_rebate_earned_usd: float
    active_lp_fee_earned_usd: float
    liquidity_side_fee_earned_usd: float
    protocol_fee_earned_usd: float
    trader_fee_bps_on_requested_notional: float
    trader_fee_bps_on_filled_notional: float
    protocol_fee_bps_on_requested_notional: float
    liquidity_side_fee_bps_on_requested_notional: float


LANE_LABELS = {
    'v2_realized': 'V2 baseline',
    '3a_pure_book': '3A pure-book',
    '3b_hybrid': '3B hybrid',
}

V2 = {
    'trader_bps': 15.0,
    'lp_bps': 12.5,
    'protocol_bps': 2.5,
}
V3_DEFAULT = {
    'scenario_id': 'no_xsauce',
    'trader_bps': 12.0,
    'maker_bps': 0.2,
    'protocol_bps': 11.8,
}
V3_TIER2 = {
    'scenario_id': 'tier2_10pct',
    'trader_bps': 10.8,
    'maker_bps': 0.22,
    'protocol_bps': 10.58,
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def parse_segment_rows(path: Path, segment_field: str) -> list[SegmentRow]:
    rows: list[SegmentRow] = []
    for raw in read_csv_rows(path):
        lane = raw['lane']
        if lane not in LANE_LABELS:
            continue
        rows.append(
            SegmentRow(
                segment=raw[segment_field],
                lane=lane,
                lane_label=raw['lane_label'],
                row_count=int(raw['row_count']),
                requested_notional_usdc=float(raw['requested_notional_usdc']),
                filled_notional_usdc=float(raw['filled_notional_usdc']),
                fill_rate=float(raw['fill_rate']),
                avg_completion_ratio=float(raw['avg_completion_ratio']),
                avg_slippage_bps=float(raw['avg_slippage_bps']),
            )
        )
    return rows


def bps(amount: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return (amount / denominator) * 10_000.0


def amount(notional: float, bps_value: float) -> float:
    return notional * bps_value / 10_000.0


def build_fee_rows(rows: Iterable[SegmentRow], *, pure_book_lookup: dict[tuple[str, str], SegmentRow], scenario: dict[str, float | str]) -> list[FeeRow]:
    fee_rows: list[FeeRow] = []
    for row in rows:
        if row.lane == 'v2_realized':
            pure_book_notional = 0.0
            v2_backstop_notional = row.filled_notional_usdc
            trader_fee_paid_usd = amount(v2_backstop_notional, V2['trader_bps'])
            maker_rebate_earned_usd = 0.0
            active_lp_fee_earned_usd = amount(v2_backstop_notional, V2['lp_bps'])
            protocol_fee_earned_usd = amount(v2_backstop_notional, V2['protocol_bps'])
        elif row.lane == '3a_pure_book':
            pure_book_notional = row.filled_notional_usdc
            v2_backstop_notional = 0.0
            trader_fee_paid_usd = amount(pure_book_notional, float(scenario['trader_bps']))
            maker_rebate_earned_usd = amount(pure_book_notional, float(scenario['maker_bps']))
            active_lp_fee_earned_usd = 0.0
            protocol_fee_earned_usd = amount(pure_book_notional, float(scenario['protocol_bps']))
        elif row.lane == '3b_hybrid':
            pure_book_row = pure_book_lookup[(row.segment, '3a_pure_book')]
            pure_book_notional = pure_book_row.filled_notional_usdc
            v2_backstop_notional = max(row.filled_notional_usdc - pure_book_notional, 0.0)
            trader_fee_paid_usd = amount(pure_book_notional, float(scenario['trader_bps'])) + amount(v2_backstop_notional, V2['trader_bps'])
            maker_rebate_earned_usd = amount(pure_book_notional, float(scenario['maker_bps']))
            active_lp_fee_earned_usd = amount(v2_backstop_notional, V2['lp_bps'])
            protocol_fee_earned_usd = amount(pure_book_notional, float(scenario['protocol_bps'])) + amount(v2_backstop_notional, V2['protocol_bps'])
        else:
            raise ValueError(f'Unsupported lane {row.lane}')
        liquidity_side_fee_earned_usd = maker_rebate_earned_usd + active_lp_fee_earned_usd
        fee_rows.append(
            FeeRow(
                segment=row.segment,
                lane=row.lane,
                lane_label=row.lane_label,
                row_count=row.row_count,
                requested_notional_usdc=row.requested_notional_usdc,
                fee_basis_filled_notional_usd=row.filled_notional_usdc,
                pure_book_filled_notional_usdc=pure_book_notional,
                v2_backstop_filled_notional_usdc=v2_backstop_notional,
                trader_fee_paid_usd=trader_fee_paid_usd,
                maker_rebate_earned_usd=maker_rebate_earned_usd,
                active_lp_fee_earned_usd=active_lp_fee_earned_usd,
                liquidity_side_fee_earned_usd=liquidity_side_fee_earned_usd,
                protocol_fee_earned_usd=protocol_fee_earned_usd,
                trader_fee_bps_on_requested_notional=bps(trader_fee_paid_usd, row.requested_notional_usdc),
                trader_fee_bps_on_filled_notional=bps(trader_fee_paid_usd, row.filled_notional_usdc),
                protocol_fee_bps_on_requested_notional=bps(protocol_fee_earned_usd, row.requested_notional_usdc),
                liquidity_side_fee_bps_on_requested_notional=bps(liquidity_side_fee_earned_usd, row.requested_notional_usdc),
            )
        )
    return fee_rows


def money(value: float) -> str:
    return f"{value:,.2f}"


def num(value: float) -> str:
    text = f"{value:,.6f}"
    return text.rstrip('0').rstrip('.')


def markdown_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    header = '| ' + ' | '.join(label for label, _ in columns) + ' |'
    sep = '| ' + ' | '.join('---' for _ in columns) + ' |'
    body = ['| ' + ' | '.join(row.get(key, '') for _, key in columns) + ' |' for row in rows]
    return '\n'.join([header, sep, *body])


def fee_rows_to_csv(path: Path, rows: list[FeeRow], scenario_id: str) -> None:
    fieldnames = [
        'segment', 'lane', 'lane_label', 'scenario_id', 'row_count', 'requested_notional_usdc',
        'fee_basis_filled_notional_usd', 'pure_book_filled_notional_usdc', 'v2_backstop_filled_notional_usdc',
        'trader_fee_paid_usd', 'maker_rebate_earned_usd', 'active_lp_fee_earned_usd',
        'liquidity_side_fee_earned_usd', 'protocol_fee_earned_usd',
        'trader_fee_bps_on_requested_notional', 'trader_fee_bps_on_filled_notional',
        'protocol_fee_bps_on_requested_notional', 'liquidity_side_fee_bps_on_requested_notional'
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'segment': row.segment,
                'lane': row.lane,
                'lane_label': row.lane_label,
                'scenario_id': scenario_id,
                'row_count': row.row_count,
                'requested_notional_usdc': f'{row.requested_notional_usdc:.12f}',
                'fee_basis_filled_notional_usd': f'{row.fee_basis_filled_notional_usd:.12f}',
                'pure_book_filled_notional_usdc': f'{row.pure_book_filled_notional_usdc:.12f}',
                'v2_backstop_filled_notional_usdc': f'{row.v2_backstop_filled_notional_usdc:.12f}',
                'trader_fee_paid_usd': f'{row.trader_fee_paid_usd:.12f}',
                'maker_rebate_earned_usd': f'{row.maker_rebate_earned_usd:.12f}',
                'active_lp_fee_earned_usd': f'{row.active_lp_fee_earned_usd:.12f}',
                'liquidity_side_fee_earned_usd': f'{row.liquidity_side_fee_earned_usd:.12f}',
                'protocol_fee_earned_usd': f'{row.protocol_fee_earned_usd:.12f}',
                'trader_fee_bps_on_requested_notional': f'{row.trader_fee_bps_on_requested_notional:.12f}',
                'trader_fee_bps_on_filled_notional': f'{row.trader_fee_bps_on_filled_notional:.12f}',
                'protocol_fee_bps_on_requested_notional': f'{row.protocol_fee_bps_on_requested_notional:.12f}',
                'liquidity_side_fee_bps_on_requested_notional': f'{row.liquidity_side_fee_bps_on_requested_notional:.12f}',
            })


def build_report(aggregate_rows: list[SegmentRow], side_rows: list[SegmentRow], bucket_rows: list[SegmentRow], default_fees: list[FeeRow], tier2_fees: list[FeeRow], current_report_excerpt: str, delta_summary: str) -> str:
    default_lookup = {(row.segment, row.lane): row for row in default_fees}
    tier2_lookup = {(row.segment, row.lane): row for row in tier2_fees}

    headline_execution = [
        {
            'lane_label': row.lane_label,
            'row_count': str(row.row_count),
            'fill_rate': num(row.fill_rate),
            'avg_completion_ratio': num(row.avg_completion_ratio),
            'avg_slippage_bps': num(row.avg_slippage_bps),
        }
        for row in aggregate_rows
    ]
    headline_fees = [
        {
            'lane_label': row.lane_label,
            'trader_fee_paid_usd': money(row.trader_fee_paid_usd),
            'maker_rebate_earned_usd': money(row.maker_rebate_earned_usd),
            'active_lp_fee_earned_usd': money(row.active_lp_fee_earned_usd),
            'liquidity_side_fee_earned_usd': money(row.liquidity_side_fee_earned_usd),
            'protocol_fee_earned_usd': money(row.protocol_fee_earned_usd),
            'trader_fee_bps_on_requested_notional': num(row.trader_fee_bps_on_requested_notional),
            'trader_fee_bps_on_filled_notional': num(row.trader_fee_bps_on_filled_notional),
        }
        for row in default_fees
        if row.segment == 'aggregate'
    ]
    scenario_rows = []
    for lane in ('v2_realized', '3a_pure_book', '3b_hybrid'):
        row = default_lookup[('aggregate', lane)]
        scenario_rows.append({
            'lane_label': row.lane_label,
            'scenario_id': 'no_xsauce' if lane != 'v2_realized' else 'v2_fixed',
            'trader_fee_paid_usd': money(row.trader_fee_paid_usd),
            'liquidity_side_fee_earned_usd': money(row.liquidity_side_fee_earned_usd),
            'protocol_fee_earned_usd': money(row.protocol_fee_earned_usd),
            'trader_fee_bps_on_requested_notional': num(row.trader_fee_bps_on_requested_notional),
        })
        if lane != 'v2_realized':
            tier2 = tier2_lookup[('aggregate', lane)]
            scenario_rows.append({
                'lane_label': tier2.lane_label,
                'scenario_id': 'tier2_10pct',
                'trader_fee_paid_usd': money(tier2.trader_fee_paid_usd),
                'liquidity_side_fee_earned_usd': money(tier2.liquidity_side_fee_earned_usd),
                'protocol_fee_earned_usd': money(tier2.protocol_fee_earned_usd),
                'trader_fee_bps_on_requested_notional': num(tier2.trader_fee_bps_on_requested_notional),
            })
    fee_side = [
        {
            'segment': row.segment,
            'lane_label': row.lane_label,
            'trader_fee_paid_usd': money(row.trader_fee_paid_usd),
            'liquidity_side_fee_earned_usd': money(row.liquidity_side_fee_earned_usd),
            'protocol_fee_earned_usd': money(row.protocol_fee_earned_usd),
            'trader_fee_bps_on_requested_notional': num(row.trader_fee_bps_on_requested_notional),
        }
        for row in default_fees
        if row.segment in {'buy', 'sell'}
    ]
    fee_bucket = [
        {
            'segment': row.segment,
            'lane_label': row.lane_label,
            'trader_fee_paid_usd': money(row.trader_fee_paid_usd),
            'liquidity_side_fee_earned_usd': money(row.liquidity_side_fee_earned_usd),
            'protocol_fee_earned_usd': money(row.protocol_fee_earned_usd),
            'trader_fee_bps_on_requested_notional': num(row.trader_fee_bps_on_requested_notional),
        }
        for row in default_fees
        if row.segment not in {'aggregate', 'buy', 'sell'}
    ]

    return '\n'.join([
        '# Final Comparison Report V2',
        '',
        '## Source basis and scope',
        '',
        '- This v2 report adds the fee-inclusive layer requested after the originally published replay study.',
        '- The fee reconstruction in this document is anchored to the last retained structured reporting snapshot: `artifacts/rh09-benchmark-20260325/reporting-root/`.',
        '- The current `reports/final-comparison.md` on `main` reflects a later RH-12 hybrid-only execution rerun, but the matching structured lane CSVs/summaries were not retained, so exact fee reconstruction on that later basis is not possible from the mounted workspace.',
        '- To avoid mixing incompatible bases, the execution-quality tables and fee tables in this v2 document are all tied to the retained RH-09 structured snapshot.',
        '- The later RH-12 hybrid delta is still captured separately below so the report preserves the full study history.',
        '',
        '## Changelog vs prior final report',
        '',
        '- Added explicit trader-fee, liquidity-side-earnings, and protocol-earnings surfaces for V2 / 3A / 3B.',
        '- Added xSAUCE fee sensitivity (`no_xsauce` vs `tier2_10pct`).',
        '- Added an explicit reconstruction note for the fee layer and a later-RH-12 delta note for 3B.',
        '- Preserved the execution-quality comparison as a separate surface rather than silently replacing it with fee-inclusive metrics.',
        '',
        '## Locked fee model used in this report',
        '',
        '- **V2 WHBAR/USDC**: trader pays `15.0 bps`, active LPs earn `12.5 bps`, protocol earns `2.5 bps`.',
        '- **V3 WHBAR/USDC / no xSAUCE**: trader pays `12.0 bps`, maker earns `0.20 bps`, protocol earns `11.8 bps`.',
        '- **V3 WHBAR/USDC / tier 2 (10%)**: trader pays `10.8 bps`, maker earns `0.22 bps`, protocol earns `10.58 bps`.',
        '- **3B hybrid attribution rule**: pure-book notional uses the V3 schedule; the residual notional above 3A for the same segment is treated as V2 backstop notional and uses the V2 schedule.',
        '',
        '## Validation / reconstruction note',
        '',
        '- The retained RH-09 structured snapshot still validates cleanly at the aggregate, side, and bucket level.',
        '- Fee rows in this v2 report are deterministic transformations of retained `filled_notional_usdc` plus the locked RH-20/21 fee contract.',
        '- Because replay-unit lane files are no longer mounted, this report **cannot** surface exact replay-unit-level `v3_min_order_ineligible` counts or the exact RH-22 all-in trader-cost USD rollups that depend on row-level execution-shortfall reconstruction.',
        '- V2 liquidity-side figures are aggregate active-LP fee accrual, not LP ROI. V3 liquidity-side figures are maker rebate capture, not full market-maker PnL.',
        '',
        '## Execution-quality headline snapshot (retained structured basis)',
        '',
        markdown_table(headline_execution, [
            ('Lane', 'lane_label'),
            ('Rows', 'row_count'),
            ('Fill rate', 'fill_rate'),
            ('Avg completion', 'avg_completion_ratio'),
            ('Avg study slippage (bps)', 'avg_slippage_bps'),
        ]),
        '',
        '## Explicit fee economics — headline aggregate (`no_xsauce` default)',
        '',
        markdown_table(headline_fees, [
            ('Lane', 'lane_label'),
            ('Trader fee (USD)', 'trader_fee_paid_usd'),
            ('Maker rebate (USD)', 'maker_rebate_earned_usd'),
            ('V2 LP accrual (USD)', 'active_lp_fee_earned_usd'),
            ('Liquidity-side total (USD)', 'liquidity_side_fee_earned_usd'),
            ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
            ('Trader fee (bps, requested)', 'trader_fee_bps_on_requested_notional'),
            ('Trader fee (bps, filled)', 'trader_fee_bps_on_filled_notional'),
        ]),
        '',
        '## Fee side split (`no_xsauce` default)',
        '',
        markdown_table(fee_side, [
            ('Side', 'segment'),
            ('Lane', 'lane_label'),
            ('Trader fee (USD)', 'trader_fee_paid_usd'),
            ('Liquidity-side total (USD)', 'liquidity_side_fee_earned_usd'),
            ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
            ('Trader fee (bps, requested)', 'trader_fee_bps_on_requested_notional'),
        ]),
        '',
        '## Fee bucket split (`no_xsauce` default)',
        '',
        markdown_table(fee_bucket, [
            ('Bucket', 'segment'),
            ('Lane', 'lane_label'),
            ('Trader fee (USD)', 'trader_fee_paid_usd'),
            ('Liquidity-side total (USD)', 'liquidity_side_fee_earned_usd'),
            ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
            ('Trader fee (bps, requested)', 'trader_fee_bps_on_requested_notional'),
        ]),
        '',
        '## xSAUCE fee sensitivity — headline aggregate',
        '',
        markdown_table(scenario_rows, [
            ('Lane', 'lane_label'),
            ('Scenario', 'scenario_id'),
            ('Trader fee (USD)', 'trader_fee_paid_usd'),
            ('Liquidity-side total (USD)', 'liquidity_side_fee_earned_usd'),
            ('Protocol earnings (USD)', 'protocol_fee_earned_usd'),
            ('Trader fee (bps, requested)', 'trader_fee_bps_on_requested_notional'),
        ]),
        '',
        '## Interpretation',
        '',
        '- V2 charges the highest explicit trader fee at a fixed `15 bps`, but routes all of that fee to active LPs plus the protocol.',
        '- 3A lowers explicit trader fees versus V2 while redirecting the liquidity-side transfer from LP accrual to maker rebate capture.',
        '- 3B sits between 3A and V2: its explicit fee layer is lower than V2 because much of the flow remains on the pure book, but higher than 3A because the residual backstop inherits V2 fees.',
        '- The xSAUCE tier-2 case lowers explicit trader fees for 3A/3B while increasing maker rebates modestly, with the remaining fee reduction flowing out of protocol take.',
        '',
        '## Later RH-12 hybrid-only rerun note',
        '',
        '- The later RH-12 rerun improved 3B execution-quality metrics versus the retained RH-09 structured snapshot, especially in larger buckets.',
        '- Those hybrid-only execution deltas are preserved here for completeness, but fee totals in this v2 report remain tied to the retained RH-09 structured pack because the later filled-notional tables were not retained.',
        '',
        delta_summary.strip(),
        '',
        '## Current main report reference',
        '',
        '- `reports/final-comparison.md` remains preserved as the later execution-quality / parity-proxy report on `main`.',
        '- This v2 document does not overwrite that report basis; it adds the fee layer on the last retained structured snapshot and carries the later RH-12 hybrid delta separately.',
        '- The current main report still contains the latest RH-12 hybrid execution figures (for example 3B aggregate `fill_rate = 0.989470558433` and `avg_slippage_bps = 2.261091936527`), but exact fee totals on that later basis cannot be reconstructed without the missing structured lane outputs.',
    ])


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    aggregate_rows = parse_segment_rows(SNAPSHOT_ROOT / 'data/processed/comparison_aggregate.csv', 'lane')
    for row in aggregate_rows:
        object.__setattr__(row, 'segment', 'aggregate')
    side_rows = parse_segment_rows(SNAPSHOT_ROOT / 'data/processed/comparison_by_side.csv', 'segment')
    bucket_rows = parse_segment_rows(SNAPSHOT_ROOT / 'data/processed/comparison_by_bucket.csv', 'segment')
    pure_book_lookup = {(row.segment, row.lane): row for row in [*aggregate_rows, *side_rows, *bucket_rows]}

    default_fee_rows = build_fee_rows([*aggregate_rows, *side_rows, *bucket_rows], pure_book_lookup=pure_book_lookup, scenario=V3_DEFAULT)
    tier2_fee_rows = build_fee_rows([*aggregate_rows, *side_rows, *bucket_rows], pure_book_lookup=pure_book_lookup, scenario=V3_TIER2)

    fee_rows_to_csv(OUTPUT_DIR / 'fees_no_xsauce.csv', default_fee_rows, 'no_xsauce')
    fee_rows_to_csv(OUTPUT_DIR / 'fees_tier2_10pct.csv', tier2_fee_rows, 'tier2_10pct')

    current_report_excerpt = CURRENT_REPORT_PATH.read_text(encoding='utf-8')
    delta_summary = (ROOT / 'artifacts' / 'rh12-large-clip-20260325' / 'before_after_delta_summary.md').read_text(encoding='utf-8')
    report = build_report(aggregate_rows, side_rows, bucket_rows, default_fee_rows, tier2_fee_rows, current_report_excerpt, delta_summary)
    REPORT_PATH.write_text(report + '\n', encoding='utf-8')

    summary = {
        'source_basis': str(SNAPSHOT_ROOT.relative_to(ROOT)),
        'current_report_reference': str(CURRENT_REPORT_PATH.relative_to(ROOT)),
        'generated_report_path': str(REPORT_PATH.relative_to(ROOT)),
        'generated_fee_csvs': [
            str((OUTPUT_DIR / 'fees_no_xsauce.csv').relative_to(ROOT)),
            str((OUTPUT_DIR / 'fees_tier2_10pct.csv').relative_to(ROOT)),
        ],
    }
    (OUTPUT_DIR / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

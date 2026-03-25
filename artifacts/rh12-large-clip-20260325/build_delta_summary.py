from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BEFORE_ROOT = REPO_ROOT / 'artifacts' / 'rh09-benchmark-20260325' / 'reporting-root' / 'data' / 'processed'
AFTER_ROOT = Path(__file__).resolve().parent / 'rerun-root' / 'data' / 'processed'
OUT_JSON = Path(__file__).with_name('before_after_delta_summary.json')
OUT_MD = Path(__file__).with_name('before_after_delta_summary.md')
TARGET_LANE = '3b_hybrid'
SEGMENTS = ['10k-25k', '25k+']
METRICS = [
    'fill_rate',
    'avg_completion_ratio',
    'avg_slippage_bps',
    'avg_abs_slippage_bps',
    'remainder_size_hbar',
    'full_fill_rows',
    'partial_fill_rows',
    'admissibility_pass_rows',
    'admissibility_fail_rows',
]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))



def pick_row(rows: list[dict[str, str]], *, lane: str, segment: str | None = None) -> dict[str, str]:
    for row in rows:
        if row['lane'] != lane:
            continue
        if segment is None or row.get('segment') == segment:
            return row
    raise KeyError((lane, segment))



def to_number(value: str) -> float:
    return float(value)



def format_delta(metric: str, before: float, after: float) -> str:
    delta = after - before
    sign = '+' if delta >= 0 else ''
    if metric.endswith('_rows'):
        return f'{sign}{int(round(delta))}'
    return f'{sign}{delta:.12g}'



def build_payload() -> dict[str, object]:
    before_aggregate = load_csv(BEFORE_ROOT / 'comparison_aggregate.csv')
    after_aggregate = load_csv(AFTER_ROOT / 'comparison_aggregate.csv')
    before_bucket = load_csv(BEFORE_ROOT / 'comparison_by_bucket.csv')
    after_bucket = load_csv(AFTER_ROOT / 'comparison_by_bucket.csv')

    payload: dict[str, object] = {'aggregate': {}, 'segments': {}}

    for label, before_row, after_row in [
        ('aggregate', pick_row(before_aggregate, lane=TARGET_LANE), pick_row(after_aggregate, lane=TARGET_LANE)),
        *[
            (
                segment,
                pick_row(before_bucket, lane=TARGET_LANE, segment=segment),
                pick_row(after_bucket, lane=TARGET_LANE, segment=segment),
            )
            for segment in SEGMENTS
        ],
    ]:
        target = {}
        for metric in METRICS:
            before = to_number(before_row[metric])
            after = to_number(after_row[metric])
            target[metric] = {
                'before': before,
                'after': after,
                'delta': after - before,
            }
        if label == 'aggregate':
            payload['aggregate'] = target
        else:
            payload['segments'][label] = target
    return payload



def build_markdown(payload: dict[str, object]) -> str:
    lines = [
        '# RH-12 before/after delta summary',
        '',
        'Comparison basis:',
        '- Before: `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/`',
        '- After: `artifacts/rh12-large-clip-20260325/rerun-root/data/processed/`',
        '- Lane: `3b_hybrid`',
        '',
    ]

    def add_section(title: str, section: dict[str, dict[str, float]]) -> None:
        lines.append(f'## {title}')
        lines.append('')
        lines.append('| metric | before | after | delta |')
        lines.append('| --- | ---: | ---: | ---: |')
        for metric in METRICS:
            values = section[metric]
            before = values['before']
            after = values['after']
            if metric.endswith('_rows'):
                before_text = str(int(round(before)))
                after_text = str(int(round(after)))
            else:
                before_text = f'{before:.12g}'
                after_text = f'{after:.12g}'
            lines.append(
                f"| {metric} | {before_text} | {after_text} | {format_delta(metric, before, after)} |"
            )
        lines.append('')

    add_section('Aggregate', payload['aggregate'])
    for segment in SEGMENTS:
        add_section(segment, payload['segments'][segment])
    return '\n'.join(lines) + '\n'



def main() -> None:
    payload = build_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    OUT_MD.write_text(build_markdown(payload), encoding='utf-8')
    print(OUT_MD)


if __name__ == '__main__':
    main()

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from ..baseline.v2_realized import _require_inputs
from ..benchmarks.lambdaplex import load_published_benchmark_status
from ..normalize.events import format_decimal, parse_float
from ..reporting.pack import (
    SIDE_ORDER,
    UNBUCKETED_LABEL,
    assign_bucket,
    build_report_caveats,
    load_bucket_config,
)
from ..reporting.tables import render_markdown_table, render_validation_polish_report
from .determinism import fingerprint_payload
from .golden_cases import evaluate_golden_cases

SAMPLED_V2_JSON_FILENAME = 'rh08-validation-sampled-v2-sanity.json'
SAMPLED_V2_MARKDOWN_FILENAME = 'rh08-validation-sampled-v2-sanity.md'
GOLDEN_CASES_JSON_FILENAME = 'rh08-validation-golden-cases.json'
GOLDEN_CASES_MARKDOWN_FILENAME = 'rh08-validation-golden-cases.md'
SUMMARY_FILENAME = 'rh08_validation_summary.json'
MANIFEST_FILENAME = 'rh08_validation_manifest.json'
VALIDATION_REPORT_FILENAME = 'validation.md'

SOURCE_ANCHOR_FIELDS = [
    'replay_unit_id',
    'tradeRowId',
    'swapEventId',
    'tradeTimestampSeconds',
    'source_ordering_key',
]


@dataclass(frozen=True)
class ValidationPolishBuildResult:
    sampled_realized_v2_json_path: Path
    sampled_realized_v2_markdown_path: Path
    golden_cases_json_path: Path
    golden_cases_markdown_path: Path
    validation_path: Path
    summary_path: Path
    manifest_path: Path
    summary: dict[str, Any]
    manifest: dict[str, Any]


def run_validation_polish(root: str | Path) -> ValidationPolishBuildResult:
    repo_root = Path(root).resolve()
    processed_dir = repo_root / 'data' / 'processed'
    reports_dir = repo_root / 'reports'
    generated_dir = reports_dir / 'generated'
    config_dir = repo_root / 'config'
    fixture_dir = repo_root / 'tests' / 'fixtures'

    baseline_lane_path = processed_dir / 'lane_v2_baseline.csv'
    v2_summary_path = processed_dir / 'v2_baseline_summary.json'
    v2_manifest_path = processed_dir / 'v2_baseline_manifest.json'
    pure_summary_path = processed_dir / 'pure_book_summary.json'
    pure_manifest_path = processed_dir / 'pure_book_manifest.json'
    hybrid_summary_path = processed_dir / 'hybrid_summary.json'
    hybrid_manifest_path = processed_dir / 'hybrid_manifest.json'
    reporting_summary_path = processed_dir / 'reporting_pack_summary.json'
    reporting_manifest_path = processed_dir / 'reporting_pack_manifest.json'
    bucket_config_path = config_dir / 'buckets.yaml'
    fee_config_path = config_dir / 'fees.yaml'
    benchmark_path = repo_root / 'benchmarks' / 'lambdaplex' / 'published-results.json'
    toy_book_path = fixture_dir / 'toy_book.yaml'
    toy_flow_path = fixture_dir / 'toy_flow.csv'
    toy_expected_outputs_path = fixture_dir / 'toy_expected_outputs.json'

    _require_inputs(
        [
            baseline_lane_path,
            v2_summary_path,
            v2_manifest_path,
            pure_summary_path,
            pure_manifest_path,
            hybrid_summary_path,
            hybrid_manifest_path,
            reporting_summary_path,
            reporting_manifest_path,
            bucket_config_path,
            fee_config_path,
            benchmark_path,
            toy_book_path,
            toy_flow_path,
            toy_expected_outputs_path,
        ]
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    bucket_config = load_bucket_config(bucket_config_path)
    benchmark_status = load_published_benchmark_status(benchmark_path)
    v2_summary = read_json(v2_summary_path)
    pure_summary = read_json(pure_summary_path)
    hybrid_summary = read_json(hybrid_summary_path)
    reporting_summary = read_json(reporting_summary_path)

    sampled_realized_v2 = build_sampled_realized_v2_sanity_pack(
        baseline_lane_path,
        bucket_config_path=bucket_config_path,
    )
    golden_cases = evaluate_golden_cases(
        toy_book_path,
        toy_flow_path,
        toy_expected_outputs_path,
        fee_config_path=fee_config_path,
    )

    sampled_realized_v2_json_path = generated_dir / SAMPLED_V2_JSON_FILENAME
    sampled_realized_v2_markdown_path = generated_dir / SAMPLED_V2_MARKDOWN_FILENAME
    golden_cases_json_path = generated_dir / GOLDEN_CASES_JSON_FILENAME
    golden_cases_markdown_path = generated_dir / GOLDEN_CASES_MARKDOWN_FILENAME
    validation_path = reports_dir / VALIDATION_REPORT_FILENAME
    summary_path = processed_dir / SUMMARY_FILENAME
    manifest_path = processed_dir / MANIFEST_FILENAME

    write_json(sampled_realized_v2_json_path, sampled_realized_v2)
    sampled_realized_v2_markdown_path.write_text(
        render_sampled_realized_v2_markdown(sampled_realized_v2),
        encoding='utf-8',
    )
    write_json(golden_cases_json_path, golden_cases)
    golden_cases_markdown_path.write_text(
        render_golden_cases_markdown(golden_cases),
        encoding='utf-8',
    )

    reporting_validation = reporting_summary['validation']
    overall_status = build_overall_status(
        reporting_validation,
        sampled_realized_v2=sampled_realized_v2,
        golden_cases=golden_cases,
    )
    study_caveats = build_report_caveats(benchmark_status)

    summary = {
        'lane': 'validation_polish',
        'contract': {
            'mounted_input_policy': 'read_only_reuse_of_rh04_rh05_rh06_rh07_artifacts',
            'realized_v2_sampling': 'first_observed_row_per_populated_side_x_requested_notional_bucket_segment',
            'golden_fixture_source': 'tests/fixtures/toy_book.yaml + toy_flow.csv + toy_expected_outputs.json',
            'reporting_context_source': 'mounted_rh07_reporting_pack_summary',
        },
        'inputs': {
            'mounted_baseline_lane_path': str(baseline_lane_path.resolve()),
            'mounted_v2_summary_path': str(v2_summary_path.resolve()),
            'mounted_pure_book_summary_path': str(pure_summary_path.resolve()),
            'mounted_hybrid_summary_path': str(hybrid_summary_path.resolve()),
            'mounted_reporting_summary_path': str(reporting_summary_path.resolve()),
            'bucket_config_path': str(bucket_config_path.resolve()),
            'fee_config_path': str(fee_config_path.resolve()),
            'benchmark_path': str(benchmark_path.resolve()),
            'toy_book_path': str(toy_book_path.resolve()),
            'toy_flow_path': str(toy_flow_path.resolve()),
            'toy_expected_outputs_path': str(toy_expected_outputs_path.resolve()),
        },
        'mounted_snapshot': {
            'v2_baseline': mounted_snapshot(v2_summary),
            'pure_book': mounted_snapshot(pure_summary),
            'hybrid': mounted_snapshot(hybrid_summary),
            'reporting_pack': mounted_snapshot(reporting_summary),
        },
        'outputs': {
            'sampled_realized_v2_json_path': relative_path(sampled_realized_v2_json_path, repo_root),
            'sampled_realized_v2_markdown_path': relative_path(sampled_realized_v2_markdown_path, repo_root),
            'golden_cases_json_path': relative_path(golden_cases_json_path, repo_root),
            'golden_cases_markdown_path': relative_path(golden_cases_markdown_path, repo_root),
            'validation_report_path': relative_path(validation_path, repo_root),
            'summary_path': relative_path(summary_path, repo_root),
            'manifest_path': relative_path(manifest_path, repo_root),
        },
        'study_caveats': study_caveats,
        'sampled_realized_v2': {
            'status': sampled_realized_v2['status'],
            'fingerprint': sampled_realized_v2['fingerprint'],
            'counts': sampled_realized_v2['counts'],
        },
        'golden_cases': {
            'status': golden_cases['status'],
            'fingerprint': golden_cases['fingerprint'],
            'counts': golden_cases['counts'],
        },
        'reporting_validation': reporting_validation,
        'overall_status': overall_status,
    }
    write_json(summary_path, summary)

    artifact_rows = build_artifact_rows(
        repo_root=repo_root,
        sampled_realized_v2_json_path=sampled_realized_v2_json_path,
        sampled_realized_v2_markdown_path=sampled_realized_v2_markdown_path,
        golden_cases_json_path=golden_cases_json_path,
        golden_cases_markdown_path=golden_cases_markdown_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
    )
    validation_path.write_text(
        render_validation_polish_report(
            caveats=study_caveats,
            rollup_validation_rows=reporting_validation['lanes'],
            global_checks=reporting_validation['global_checks'],
            sample_rows=build_sample_report_rows(sampled_realized_v2),
            golden_rows=build_golden_report_rows(golden_cases),
            artifact_rows=artifact_rows,
        ),
        encoding='utf-8',
    )

    manifest = {
        'lane': summary['lane'],
        'status': summary['overall_status'],
        'inputs': {
            'mounted_artifacts': [
                manifest_input_entry('baseline_lane', baseline_lane_path),
                manifest_input_entry('v2_summary', v2_summary_path),
                manifest_input_entry('v2_manifest', v2_manifest_path),
                manifest_input_entry('pure_book_summary', pure_summary_path),
                manifest_input_entry('pure_book_manifest', pure_manifest_path),
                manifest_input_entry('hybrid_summary', hybrid_summary_path),
                manifest_input_entry('hybrid_manifest', hybrid_manifest_path),
                manifest_input_entry('reporting_pack_summary', reporting_summary_path),
                manifest_input_entry('reporting_pack_manifest', reporting_manifest_path),
            ],
            'config': [
                manifest_input_entry('bucket_config', bucket_config_path),
                manifest_input_entry('fee_config', fee_config_path),
                manifest_input_entry('benchmark', benchmark_path),
            ],
            'fixtures': [
                manifest_input_entry('toy_book', toy_book_path),
                manifest_input_entry('toy_flow', toy_flow_path),
                manifest_input_entry('toy_expected_outputs', toy_expected_outputs_path),
            ],
        },
        'mounted_snapshot': summary['mounted_snapshot'],
        'fingerprints': {
            'sampled_realized_v2': sampled_realized_v2['fingerprint'],
            'golden_cases': golden_cases['fingerprint'],
            'reporting_validation': fingerprint_payload(reporting_validation),
            'summary_payload': fingerprint_payload(summary),
        },
        'outputs': build_output_manifest(
            repo_root=repo_root,
            paths=[
                sampled_realized_v2_json_path,
                sampled_realized_v2_markdown_path,
                golden_cases_json_path,
                golden_cases_markdown_path,
                validation_path,
                summary_path,
            ],
            manifest_path=manifest_path,
        ),
    }
    write_json(manifest_path, manifest)

    return ValidationPolishBuildResult(
        sampled_realized_v2_json_path=sampled_realized_v2_json_path,
        sampled_realized_v2_markdown_path=sampled_realized_v2_markdown_path,
        golden_cases_json_path=golden_cases_json_path,
        golden_cases_markdown_path=golden_cases_markdown_path,
        validation_path=validation_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
        summary=summary,
        manifest=manifest,
    )


def build_sampled_realized_v2_sanity_pack(
    baseline_lane_path: str | Path,
    *,
    bucket_config_path: str | Path,
) -> dict[str, Any]:
    bucket_config = load_bucket_config(bucket_config_path)
    segment_counts: dict[tuple[str, str], int] = {}
    selected_rows: dict[tuple[str, str], dict[str, str]] = {}
    rows_scanned = 0

    with Path(baseline_lane_path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_scanned += 1
            segment = (
                row['side'],
                assign_bucket(bucket_config, parse_float(row['requested_notional'])),
            )
            segment_counts[segment] = segment_counts.get(segment, 0) + 1
            if segment not in selected_rows:
                selected_rows[segment] = dict(row)

    bucket_order = [bucket.label for bucket in bucket_config.buckets] + [UNBUCKETED_LABEL]
    samples: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for side in SIDE_ORDER:
        for bucket_label in bucket_order:
            segment_key = (side, bucket_label)
            row_count = segment_counts.get(segment_key, 0)
            selected_row = selected_rows.get(segment_key)
            segments.append(
                {
                    'side': side,
                    'bucket': bucket_label,
                    'row_count': row_count,
                    'selected': selected_row is not None,
                }
            )
            if selected_row is None:
                continue
            samples.append(
                build_sampled_baseline_case(
                    selected_row,
                    side=side,
                    bucket_label=bucket_label,
                    row_count=row_count,
                )
            )

    empty_segments = [segment for segment in segments if segment['row_count'] == 0]
    populated_segments = [segment for segment in segments if segment['row_count'] > 0]
    status = 'pass' if all(sample['status'] == 'pass' for sample in samples) else 'fail'
    fingerprint = fingerprint_payload(
        {
            'selection_strategy': {
                'type': 'first_observed_row_per_populated_segment',
                'side_order': SIDE_ORDER,
                'bucket_order': bucket_order,
            },
            'segments': segments,
            'samples': samples,
        }
    )
    return {
        'selection_strategy': {
            'type': 'first_observed_row_per_populated_segment',
            'axis': ['side', 'requested_notional_bucket'],
            'side_order': SIDE_ORDER,
            'bucket_order': bucket_order,
            'source_lane_path': str(Path(baseline_lane_path)),
            'bucket_config_path': str(Path(bucket_config_path)),
        },
        'counts': {
            'rows_scanned': rows_scanned,
            'populated_segments': len(populated_segments),
            'empty_segments': len(empty_segments),
            'selected_segments': len(samples),
        },
        'status': status,
        'fingerprint': fingerprint,
        'segments': segments,
        'samples': samples,
    }


def build_sampled_baseline_case(
    row: dict[str, str],
    *,
    side: str,
    bucket_label: str,
    row_count: int,
) -> dict[str, Any]:
    route_breakdown_raw = json.loads(row.get('route_breakdown') or '{}')
    route_breakdown = {
        str(key): format_decimal(float(value)) for key, value in sorted(route_breakdown_raw.items())
    }
    contract_checks = {
        'filled_size_matches_requested_size': numeric_text_match(row['filled_size'], row['requested_size']),
        'filled_notional_matches_requested_notional': numeric_text_match(
            row['filled_notional'],
            row['requested_notional'],
        ),
        'completion_ratio_is_one': numeric_text_match(row['completion_ratio'], '1'),
        'remainder_size_is_zero': numeric_text_match(row['remainder_size'], '0'),
        'route_breakdown_contains_v2': 'v2' in route_breakdown,
        'route_breakdown_v2_matches_filled_size': numeric_text_match(
            route_breakdown.get('v2', '0'),
            row['filled_size'],
        ),
        'admissibility_passed_true': str(row.get('admissibility_passed') or '').strip() == 'true',
        'source_anchors_present': all(str(row.get(field) or '').strip() for field in SOURCE_ANCHOR_FIELDS),
    }
    pass_count = sum(1 for value in contract_checks.values() if value)
    return {
        'segment': f'{side} / {bucket_label}',
        'side': side,
        'bucket': bucket_label,
        'rows_in_segment': row_count,
        'check_summary': f'{pass_count}/{len(contract_checks)}',
        'status': 'pass' if pass_count == len(contract_checks) else 'fail',
        'source_anchor': {
            'replay_unit_id': row['replay_unit_id'],
            'trade_row_id': row['tradeRowId'],
            'swap_event_id': row['swapEventId'],
            'trade_timestamp_seconds': row['tradeTimestampSeconds'],
            'source_ordering_key': row['source_ordering_key'],
        },
        'values': {
            'requested_size': normalized_numeric_text(row['requested_size']),
            'requested_notional': normalized_numeric_text(row['requested_notional']),
            'filled_size': normalized_numeric_text(row['filled_size']),
            'filled_notional': normalized_numeric_text(row['filled_notional']),
            'completion_ratio': normalized_numeric_text(row['completion_ratio']),
            'remainder_size': normalized_numeric_text(row['remainder_size']),
            'reference_price': normalized_numeric_text(row['reference_price']),
            'avg_execution_price': normalized_numeric_text(row['avg_execution_price']),
            'realized_slippage_bps': normalized_numeric_text(row['realized_slippage_bps']),
            'route_breakdown': route_breakdown,
            'admissibility_passed': row['admissibility_passed'],
            'reference_price_source': row['reference_price_source'],
            'reference_price_fallback': row['reference_price_fallback'],
        },
        'contract_checks': contract_checks,
    }


def render_sampled_realized_v2_markdown(payload: dict[str, Any]) -> str:
    rows = build_sample_report_rows(payload)
    lines = [
        '# RH-08 Sampled Realized-V2 Sanity Pack',
        '',
        'Strategy: first observed row per populated `side x requested_notional bucket` segment from mounted `data/processed/lane_v2_baseline.csv`.',
        '',
        '## Selected samples',
        '',
        render_markdown_table(
            rows,
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
    ]
    return '\n'.join(lines) + '\n'


def render_golden_cases_markdown(payload: dict[str, Any]) -> str:
    rows = build_golden_report_rows(payload)
    lines = [
        '# RH-08 Golden Cases',
        '',
        'Fixture inputs: `tests/fixtures/toy_book.yaml`, `tests/fixtures/toy_flow.csv`, `tests/fixtures/toy_expected_outputs.json`.',
        '',
        '## Golden-case results',
        '',
        render_markdown_table(
            rows,
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
    ]
    return '\n'.join(lines) + '\n'


def build_sample_report_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            'segment': sample['segment'],
            'rows_in_segment': str(sample['rows_in_segment']),
            'replay_unit_id': sample['source_anchor']['replay_unit_id'],
            'requested_notional': sample['values']['requested_notional'],
            'source_ordering_key': sample['source_anchor']['source_ordering_key'],
            'check_summary': sample['check_summary'],
            'status': sample['status'],
        }
        for sample in payload['samples']
    ]


def build_golden_report_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            'name': case['name'],
            'lane': case['lane'],
            'replay_unit_id': case['replay_unit_id'],
            'completion_ratio': case['actual']['completion_ratio'],
            'remainder_size': case['actual']['remainder_size'],
            'admissibility_passed': render_optional_bool(case['actual']['admissibility_passed']),
            'check_summary': case['check_summary'],
            'status': case['status'],
        }
        for case in payload['cases']
    ]


def build_artifact_rows(
    *,
    repo_root: Path,
    sampled_realized_v2_json_path: Path,
    sampled_realized_v2_markdown_path: Path,
    golden_cases_json_path: Path,
    golden_cases_markdown_path: Path,
    summary_path: Path,
    manifest_path: Path,
) -> list[dict[str, str]]:
    return [
        artifact_row(repo_root, 'Sampled realized-V2 JSON', sampled_realized_v2_json_path, status='materialized'),
        artifact_row(repo_root, 'Sampled realized-V2 Markdown', sampled_realized_v2_markdown_path, status='materialized'),
        artifact_row(repo_root, 'Golden cases JSON', golden_cases_json_path, status='materialized'),
        artifact_row(repo_root, 'Golden cases Markdown', golden_cases_markdown_path, status='materialized'),
        artifact_row(repo_root, 'Validation summary JSON', summary_path, status='materialized'),
        artifact_row(
            repo_root,
            'Validation manifest JSON',
            manifest_path,
            status='materialized',
            fingerprint='omitted:self-reference',
        ),
    ]


def artifact_row(
    repo_root: Path,
    label: str,
    path: Path,
    *,
    status: str,
    fingerprint: str | None = None,
) -> dict[str, str]:
    resolved_fingerprint = fingerprint
    if resolved_fingerprint is None and path.exists():
        resolved_fingerprint = file_sha256(path)
    return {
        'artifact': label,
        'path': relative_path(path, repo_root),
        'status': status,
        'fingerprint': resolved_fingerprint or '',
    }


def build_overall_status(
    reporting_validation: dict[str, Any],
    *,
    sampled_realized_v2: dict[str, Any],
    golden_cases: dict[str, Any],
) -> str:
    rollup_pass = all(row['status'] == 'pass' for row in reporting_validation['lanes'])
    if rollup_pass and sampled_realized_v2['status'] == 'pass' and golden_cases['status'] == 'pass':
        return 'pass'
    return 'fail'


def mounted_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    mapping = summary.get('mapping', {})
    return {
        'generated_at_utc': summary.get('generated_at_utc'),
        'lane': summary.get('lane'),
        'mapping_fingerprint': mapping.get('fingerprint'),
        'row_counts': summary.get('row_counts', {}),
    }


def manifest_input_entry(label: str, path: Path) -> dict[str, Any]:
    return {
        'label': label,
        'path': str(path.resolve()),
        'bytes': path.stat().st_size,
    }


def build_output_manifest(
    *,
    repo_root: Path,
    paths: list[Path],
    manifest_path: Path,
) -> list[dict[str, Any]]:
    entries = [
        {
            'path': relative_path(path, repo_root),
            'bytes': path.stat().st_size,
            'sha256': file_sha256(path),
        }
        for path in paths
    ]
    entries.append(
        {
            'path': relative_path(manifest_path, repo_root),
            'bytes': 'omitted:self-reference',
            'sha256': 'omitted:self-reference',
        }
    )
    return entries


def numeric_text_match(left: str, right: str, *, tolerance: float = 1e-12) -> bool:
    return abs(parse_float(left) - parse_float(right)) <= tolerance


def normalized_numeric_text(value: str) -> str:
    return format_decimal(parse_float(value))


def render_optional_bool(value: bool | None) -> str:
    if value is None:
        return ''
    return 'true' if value else 'false'


def relative_path(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterator

from ..baseline.v2_realized import _require_inputs, parse_bool_text, utc_now
from ..benchmarks.lambdaplex import PublishedBenchmarkStatus, load_published_benchmark_status
from ..metrics.summaries import LaneObservation, RollupSummary, roll_up_observations
from ..normalize.events import parse_float, parse_int
from ..settings import _load_yaml_payload
from .tables import (
    AGGREGATE_FIELDNAMES,
    SEGMENT_FIELDNAMES,
    build_aggregate_rows,
    build_segment_rows,
    render_final_comparison_report,
    render_reconciliation_report,
    render_validation_report,
)

REPORTING_CONFIG_FILENAME = 'reporting.yaml'
BUCKET_CONFIG_FILENAME = 'buckets.yaml'
BENCHMARK_FILENAME = 'published-results.json'
COMPARISON_AGGREGATE_FILENAME = 'comparison_aggregate.csv'
COMPARISON_BY_BUCKET_FILENAME = 'comparison_by_bucket.csv'
COMPARISON_BY_SIDE_FILENAME = 'comparison_by_side.csv'
SUMMARY_FILENAME = 'reporting_pack_summary.json'
MANIFEST_FILENAME = 'reporting_pack_manifest.json'
FINAL_COMPARISON_REPORT = 'final-comparison.md'
RECONCILIATION_REPORT = 'reconciliation.md'
VALIDATION_REPORT = 'validation.md'
UNBUCKETED_LABEL = 'unbucketed'

LANE_ORDER = ['v2_realized', '3a_pure_book', '3b_hybrid']
SIDE_ORDER = ['buy', 'sell']
LANE_LABELS = {
    'v2_realized': 'V2 baseline',
    '3a_pure_book': '3A pure-book',
    '3b_hybrid': '3B hybrid',
}
LANE_NOTES = {
    'v2_realized': 'Observed realized V2 execution under the event-level replay contract.',
    '3a_pure_book': 'Study-owned replenishing synthetic book; partial fills remain explicit.',
    '3b_hybrid': 'Mounted 3A fill plus residual V2 backstop only when the frozen admissibility rule passes.',
}


@dataclass(frozen=True)
class LaneInputSpec:
    lane: str
    csv_filename: str
    summary_filename: str
    manifest_filename: str
    slippage_field: str
    row_count_key: str
    alignment_path: tuple[str, ...]
    size_checks: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ReportingConfig:
    include_side_split: bool
    include_bucket_split: bool
    include_validation_summary: bool
    figure_dir: str


@dataclass(frozen=True)
class BucketDefinition:
    label: str
    minimum: float
    maximum: float | None


@dataclass(frozen=True)
class BucketConfig:
    edge_semantics: str
    basis: str
    buckets: list[BucketDefinition]


@dataclass(frozen=True)
class LaneArtifacts:
    aggregate: RollupSummary
    by_side: dict[str, RollupSummary]
    by_bucket: dict[str, RollupSummary]
    summary: dict[str, Any]
    manifest: dict[str, Any]


@dataclass(frozen=True)
class ReportingPackBuildResult:
    comparison_aggregate_path: Path
    comparison_by_bucket_path: Path
    comparison_by_side_path: Path
    final_comparison_path: Path
    reconciliation_path: Path
    validation_path: Path
    summary_path: Path
    manifest_path: Path
    summary: dict[str, Any]
    manifest: dict[str, Any]


LANE_SPECS = [
    LaneInputSpec(
        lane='v2_realized',
        csv_filename='lane_v2_baseline.csv',
        summary_filename='v2_baseline_summary.json',
        manifest_filename='v2_baseline_manifest.json',
        slippage_field='realized_slippage_bps',
        row_count_key='baseline_rows',
        alignment_path=('mapping', 'replay_projection_complete'),
        size_checks=(
            ('reconciliation', 'requested_size_matches_filled_size'),
            ('reconciliation', 'requested_notional_matches_filled_notional'),
        ),
    ),
    LaneInputSpec(
        lane='3a_pure_book',
        csv_filename='lane_3a_pure_book.csv',
        summary_filename='pure_book_summary.json',
        manifest_filename='pure_book_manifest.json',
        slippage_field='execution_slippage_bps',
        row_count_key='pure_book_rows',
        alignment_path=('mapping', 'replay_projection_complete'),
        size_checks=(('reconciliation', 'filled_plus_remainder_matches_requested_size'),),
    ),
    LaneInputSpec(
        lane='3b_hybrid',
        csv_filename='lane_3b_hybrid.csv',
        summary_filename='hybrid_summary.json',
        manifest_filename='hybrid_manifest.json',
        slippage_field='execution_slippage_bps',
        row_count_key='hybrid_rows',
        alignment_path=('reconciliation', 'input_alignment_verified'),
        size_checks=(('reconciliation', 'filled_plus_remainder_matches_requested_size'),),
    ),
]


def run_reporting_pack(root: str | Path) -> ReportingPackBuildResult:
    repo_root = Path(root).resolve()
    processed_dir = repo_root / 'data' / 'processed'
    reports_dir = repo_root / 'reports'
    config_dir = repo_root / 'config'
    benchmark_path = repo_root / 'benchmarks' / 'lambdaplex' / BENCHMARK_FILENAME
    reporting_config_path = config_dir / REPORTING_CONFIG_FILENAME
    bucket_config_path = config_dir / BUCKET_CONFIG_FILENAME

    input_paths = [benchmark_path, reporting_config_path, bucket_config_path]
    for spec in LANE_SPECS:
        input_paths.extend(
            [
                processed_dir / spec.csv_filename,
                processed_dir / spec.summary_filename,
                processed_dir / spec.manifest_filename,
            ]
        )
    _require_inputs(input_paths)

    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    reporting_config = load_reporting_config(reporting_config_path)
    bucket_config = load_bucket_config(bucket_config_path)
    benchmark_status = load_published_benchmark_status(benchmark_path)

    lane_artifacts: dict[str, LaneArtifacts] = {}
    for spec in LANE_SPECS:
        lane_summary = json.loads((processed_dir / spec.summary_filename).read_text(encoding='utf-8'))
        lane_manifest = json.loads((processed_dir / spec.manifest_filename).read_text(encoding='utf-8'))
        aggregate, by_side, by_bucket = roll_up_lane(
            processed_dir / spec.csv_filename,
            spec=spec,
            bucket_config=bucket_config,
            reporting_config=reporting_config,
        )
        lane_artifacts[spec.lane] = LaneArtifacts(
            aggregate=aggregate,
            by_side=by_side,
            by_bucket=by_bucket,
            summary=lane_summary,
            manifest=lane_manifest,
        )
    authoritative_aggregates = {
        spec.lane: aggregate_from_summary(spec, lane_artifacts[spec.lane])
        for spec in LANE_SPECS
    }

    aggregate_rows = build_aggregate_rows(
        lane_order=LANE_ORDER,
        lane_labels=LANE_LABELS,
        lane_rollups=authoritative_aggregates,
        lane_fee_precision={
            lane: str(artifact.summary.get('fees', {}).get('fee_precision', ''))
            for lane, artifact in lane_artifacts.items()
        },
        lane_notes=LANE_NOTES,
        benchmark_status=benchmark_status,
    )
    side_rows = build_segment_rows(
        segment_order=SIDE_ORDER,
        lane_order=LANE_ORDER,
        lane_labels=LANE_LABELS,
        lane_segment_rollups={lane: artifact.by_side for lane, artifact in lane_artifacts.items()},
    )
    bucket_rows = build_segment_rows(
        segment_order=[bucket.label for bucket in bucket_config.buckets] + [UNBUCKETED_LABEL],
        lane_order=LANE_ORDER,
        lane_labels=LANE_LABELS,
        lane_segment_rollups={lane: artifact.by_bucket for lane, artifact in lane_artifacts.items()},
    )

    comparison_aggregate_path = processed_dir / COMPARISON_AGGREGATE_FILENAME
    comparison_by_bucket_path = processed_dir / COMPARISON_BY_BUCKET_FILENAME
    comparison_by_side_path = processed_dir / COMPARISON_BY_SIDE_FILENAME
    summary_path = processed_dir / SUMMARY_FILENAME
    manifest_path = processed_dir / MANIFEST_FILENAME
    final_comparison_path = reports_dir / FINAL_COMPARISON_REPORT
    reconciliation_path = reports_dir / RECONCILIATION_REPORT
    validation_path = reports_dir / VALIDATION_REPORT

    write_csv(comparison_aggregate_path, AGGREGATE_FIELDNAMES, aggregate_rows)
    write_csv(comparison_by_bucket_path, SEGMENT_FIELDNAMES, bucket_rows)
    write_csv(comparison_by_side_path, SEGMENT_FIELDNAMES, side_rows)

    validation_rows = [build_validation_row(spec, lane_artifacts[spec.lane]) for spec in LANE_SPECS]
    reconciliation_rows = [build_reconciliation_row(spec, lane_artifacts[spec.lane]) for spec in LANE_SPECS]
    source_rows = [
        {
            'lane_label': LANE_LABELS[spec.lane],
            'lane_csv': f'data/processed/{spec.csv_filename}',
            'summary_json': f'data/processed/{spec.summary_filename}',
            'manifest_json': f'data/processed/{spec.manifest_filename}',
        }
        for spec in LANE_SPECS
    ]
    global_checks = build_global_checks(reporting_config, bucket_config, benchmark_status, validation_rows)

    final_comparison_path.write_text(
        render_final_comparison_report(
            aggregate_rows=aggregate_rows,
            side_rows=side_rows,
            bucket_rows=bucket_rows,
            benchmark_status=benchmark_status,
            caveats=build_report_caveats(benchmark_status),
        ),
        encoding='utf-8',
    )
    reconciliation_path.write_text(
        render_reconciliation_report(
            reconciliation_rows=reconciliation_rows,
            source_rows=source_rows,
        ),
        encoding='utf-8',
    )
    validation_path.write_text(
        render_validation_report(
            validation_rows=validation_rows,
            global_checks=global_checks,
        ),
        encoding='utf-8',
    )

    summary = {
        'generated_at_utc': utc_now(),
        'reporting_config': {
            'include_side_split': reporting_config.include_side_split,
            'include_bucket_split': reporting_config.include_bucket_split,
            'include_validation_summary': reporting_config.include_validation_summary,
            'figure_dir': reporting_config.figure_dir,
        },
        'bucket_config': {
            'edge_semantics': bucket_config.edge_semantics,
            'basis': bucket_config.basis,
            'labels': [bucket.label for bucket in bucket_config.buckets],
        },
        'benchmark': {
            'source': benchmark_status.source,
            'market': benchmark_status.market,
            'status': benchmark_status.status,
            'comparable': benchmark_status.comparable,
            'headline_metrics': benchmark_status.headline_metrics,
            'notes': benchmark_status.notes,
        },
        'outputs': {
            'comparison_aggregate_path': str(comparison_aggregate_path),
            'comparison_by_bucket_path': str(comparison_by_bucket_path),
            'comparison_by_side_path': str(comparison_by_side_path),
            'final_comparison_path': str(final_comparison_path),
            'reconciliation_path': str(reconciliation_path),
            'validation_path': str(validation_path),
            'summary_path': str(summary_path),
            'manifest_path': str(manifest_path),
        },
        'lane_rollups': {
            lane: {
                'aggregate': serialize_rollup_summary(artifact.aggregate),
                'authoritative_aggregate': serialize_rollup_summary(authoritative_aggregates[lane]),
                'by_side': {key: serialize_rollup_summary(value) for key, value in artifact.by_side.items()},
                'by_bucket': {key: serialize_rollup_summary(value) for key, value in artifact.by_bucket.items()},
            }
            for lane, artifact in lane_artifacts.items()
        },
        'validation': {
            'lanes': validation_rows,
            'global_checks': global_checks,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

    manifest = {
        'generated_at_utc': summary['generated_at_utc'],
        'inputs': build_manifest_inputs(repo_root, benchmark_path, reporting_config_path, bucket_config_path),
        'outputs': build_manifest_outputs(
            comparison_aggregate_path,
            comparison_by_bucket_path,
            comparison_by_side_path,
            final_comparison_path,
            reconciliation_path,
            validation_path,
            summary_path,
            manifest_path,
        ),
        'benchmark': summary['benchmark'],
        'validation': summary['validation'],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    return ReportingPackBuildResult(
        comparison_aggregate_path=comparison_aggregate_path,
        comparison_by_bucket_path=comparison_by_bucket_path,
        comparison_by_side_path=comparison_by_side_path,
        final_comparison_path=final_comparison_path,
        reconciliation_path=reconciliation_path,
        validation_path=validation_path,
        summary_path=summary_path,
        manifest_path=manifest_path,
        summary=summary,
        manifest=manifest,
    )


def load_reporting_config(path: str | Path) -> ReportingConfig:
    payload = _load_yaml_payload(Path(path))
    reporting = payload.get('reporting')
    if not isinstance(reporting, dict):
        raise ValueError(f'{path} must define a top-level reporting mapping')
    return ReportingConfig(
        include_side_split=bool(reporting.get('include_side_split', True)),
        include_bucket_split=bool(reporting.get('include_bucket_split', True)),
        include_validation_summary=bool(reporting.get('include_validation_summary', True)),
        figure_dir=str(reporting.get('figure_dir', 'reports/figures')),
    )


def load_bucket_config(path: str | Path) -> BucketConfig:
    config_path = Path(path)
    raw_text = config_path.read_text(encoding='utf-8')
    payload = _load_yaml_payload(config_path)
    buckets_raw = payload.get('requested_notional_buckets')
    if not isinstance(buckets_raw, list) or not buckets_raw:
        buckets_raw = parse_bucket_entries(raw_text)
    if not buckets_raw:
        raise ValueError(f'{path} must define requested_notional_buckets')
    bucket_basis = payload.get('bucket_basis')
    if bucket_basis is None:
        bucket_basis = parse_bucket_header(raw_text, 'bucket_basis')
    if bucket_basis != 'requested_notional':
        raise ValueError(f'{path} must set bucket_basis=requested_notional for RH-07')
    edge_semantics = payload.get('bucket_edge_semantics')
    if edge_semantics is None:
        edge_semantics = parse_bucket_header(raw_text, 'bucket_edge_semantics') or ''

    buckets: list[BucketDefinition] = []
    for item in buckets_raw:
        if not isinstance(item, dict):
            raise ValueError(f'{path} bucket entries must be mappings')
        buckets.append(
            BucketDefinition(
                label=str(item['label']),
                minimum=float(item['min']),
                maximum=None if item.get('max') is None else float(item['max']),
            )
        )

    return BucketConfig(
        edge_semantics=str(edge_semantics),
        basis='requested_notional',
        buckets=buckets,
    )


def parse_bucket_entries(text: str) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith('- {') or not line.endswith('}'):
            continue
        inner = line[3:-1]
        bucket: dict[str, Any] = {}
        for entry in inner.split(','):
            key, raw_value = entry.split(':', 1)
            bucket[key.strip()] = parse_bucket_scalar(raw_value.strip())
        buckets.append(bucket)
    return buckets


def parse_bucket_header(text: str, key: str) -> Any:
    prefix = f'{key}:'
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or not line.startswith(prefix):
            continue
        return parse_bucket_scalar(line[len(prefix) :].strip())
    return None


def parse_bucket_scalar(value: str) -> Any:
    text = value.strip()
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if text.lower() == 'null':
        return None
    if '.' in text:
        return float(text)
    return int(text)


def roll_up_lane(
    csv_path: Path,
    *,
    spec: LaneInputSpec,
    bucket_config: BucketConfig,
    reporting_config: ReportingConfig,
) -> tuple[RollupSummary, dict[str, RollupSummary], dict[str, RollupSummary]]:
    bucket_label = None
    if reporting_config.include_bucket_split:
        bucket_label = lambda observation: assign_bucket(bucket_config, observation.requested_notional)

    aggregate, by_side, by_bucket = roll_up_observations(
        iter_lane_observations(csv_path, slippage_field=spec.slippage_field),
        bucket_label=bucket_label,
    )
    if not reporting_config.include_side_split:
        by_side = {}
    if not reporting_config.include_bucket_split:
        by_bucket = {}
    return aggregate, by_side, by_bucket


def iter_lane_observations(csv_path: Path, *, slippage_field: str) -> Iterator[LaneObservation]:
    with csv_path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            admissibility_text = str(row.get('admissibility_passed', '')).strip()
            admissibility = None if not admissibility_text else parse_bool_text(admissibility_text)
            yield LaneObservation(
                lane=row['lane'],
                side=row['side'],
                requested_size=parse_float(row['requested_size']),
                requested_notional=parse_float(row['requested_notional']),
                requested_size_raw=parse_int(row['targetVolumeRaw']),
                requested_notional_raw=parse_int(row['baseVolumeRaw']),
                filled_size=parse_float(row['filled_size']),
                filled_notional=parse_float(row['filled_notional']),
                completion_ratio=parse_float(row['completion_ratio']),
                remainder_size=parse_float(row['remainder_size']),
                slippage_bps=parse_float(row[slippage_field]),
                fee_covered=parse_bool_text(row.get('fee_covered')),
                admissibility_passed=admissibility,
            )


def assign_bucket(bucket_config: BucketConfig, requested_notional: float) -> str:
    for index, bucket in enumerate(bucket_config.buckets):
        is_last = index == len(bucket_config.buckets) - 1
        if requested_notional < bucket.minimum:
            continue
        if bucket.maximum is None:
            return bucket.label
        if requested_notional < bucket.maximum:
            return bucket.label
        if is_last and requested_notional == bucket.maximum:
            return bucket.label
    return UNBUCKETED_LABEL


def build_validation_row(spec: LaneInputSpec, artifacts: LaneArtifacts) -> dict[str, str]:
    summary = artifacts.summary
    aggregate = artifacts.aggregate

    row_count_matches = aggregate.row_count == int(summary['row_counts'][spec.row_count_key])
    requested_totals_match = (
        build_requested_size_text(aggregate) == summary['totals']['requested_size_hbar']
        and build_requested_notional_text(aggregate) == summary['totals']['requested_notional_usdc']
    )
    filled_totals_match = (
        approximately_matches_summary(aggregate.filled_size_total, summary['totals']['filled_size_hbar'])
        and approximately_matches_summary(aggregate.filled_notional_total, summary['totals']['filled_notional_usdc'])
        and remainder_matches_summary(aggregate, summary)
    )
    completion_counts_match = (
        aggregate.full_fill_rows == int(summary['completion']['full_fill_rows'])
        and aggregate.partial_fill_rows == int(summary['completion']['partial_fill_rows'])
        and aggregate.zero_fill_rows == int(summary['completion']['zero_fill_rows'])
    )
    fee_coverage_match = (
        aggregate.fee_covered_rows == int(summary['fees']['fee_covered_rows'])
        and aggregate.fee_missing_rows == int(summary['fees']['fee_missing_rows'])
    )

    checks = [
        row_count_matches,
        requested_totals_match,
        filled_totals_match,
        completion_counts_match,
        fee_coverage_match,
    ]
    status = 'pass' if all(checks) else 'fail'
    return {
        'lane': spec.lane,
        'lane_label': LANE_LABELS[spec.lane],
        'row_count_matches': bool_text(row_count_matches),
        'requested_totals_match': bool_text(requested_totals_match),
        'filled_totals_match': bool_text(filled_totals_match),
        'completion_counts_match': bool_text(completion_counts_match),
        'fee_coverage_match': bool_text(fee_coverage_match),
        'status': status,
    }


def build_reconciliation_row(spec: LaneInputSpec, artifacts: LaneArtifacts) -> dict[str, str]:
    summary = artifacts.summary
    counts_match = bool(summary['reconciliation']['counts_match'])
    size_checks = all(bool(dig(summary, path)) for path in spec.size_checks)
    alignment_check = bool(dig(summary, spec.alignment_path))
    return {
        'lane': spec.lane,
        'lane_label': LANE_LABELS[spec.lane],
        'row_count': str(summary['row_counts'][spec.row_count_key]),
        'counts_match': bool_text(counts_match),
        'size_check': bool_text(size_checks),
        'alignment_check': bool_text(alignment_check),
        'mapping_fingerprint': str(summary.get('mapping', {}).get('fingerprint', '')),
    }


def build_global_checks(
    reporting_config: ReportingConfig,
    bucket_config: BucketConfig,
    benchmark_status: PublishedBenchmarkStatus,
    validation_rows: list[dict[str, str]],
) -> list[str]:
    all_pass = all(row['status'] == 'pass' for row in validation_rows)
    checks = [
        f'Lane order fixed to: {", ".join(LANE_LABELS[lane] for lane in LANE_ORDER)}.',
        f'Side split enabled in config/reporting.yaml: {bool_text(reporting_config.include_side_split)}.',
        f'Bucket split enabled in config/reporting.yaml: {bool_text(reporting_config.include_bucket_split)}.',
        f'Bucket basis from config/buckets.yaml: `{bucket_config.basis}` with semantics `{bucket_config.edge_semantics}`.',
        f'All direct lane rollups matched mounted lane summaries: {bool_text(all_pass)}.',
    ]
    if benchmark_status.comparable:
        checks.append('Lambdaplex published panel exposed headline metrics, but RH-07 preserves them as raw published payload only.')
    else:
        checks.append(
            f'Lambdaplex published panel status is `{benchmark_status.status}`; no comparable benchmark metrics were merged.'
        )
    return checks


def aggregate_from_summary(spec: LaneInputSpec, artifacts: LaneArtifacts) -> RollupSummary:
    summary = artifacts.summary
    direct = artifacts.aggregate
    requested_size_raw_total = direct.requested_size_raw_total
    requested_notional_raw_total = direct.requested_notional_raw_total
    requested_size_total = requested_size_raw_total / 10**8
    filled_size_total = float(summary['totals']['filled_size_hbar'])

    fill_rate = 0.0
    if requested_size_total > 0:
        fill_rate = round(filled_size_total / requested_size_total, 12)

    return RollupSummary(
        row_count=int(summary['row_counts'][spec.row_count_key]),
        requested_size_raw_total=requested_size_raw_total,
        requested_notional_raw_total=requested_notional_raw_total,
        filled_size_total=filled_size_total,
        filled_notional_total=float(summary['totals']['filled_notional_usdc']),
        remainder_size_total=float(summary['totals'].get('remainder_size_hbar', 0.0)),
        fill_rate=fill_rate,
        avg_completion_ratio=float(summary['completion']['avg_completion_ratio']),
        avg_slippage_bps=float(summary['slippage_bps']['avg']),
        avg_abs_slippage_bps=float(summary['slippage_bps']['avg_abs']),
        finite_slippage_rows=int(summary['slippage_bps']['finite_rows']),
        non_finite_slippage_rows=int(summary['slippage_bps'].get('infinite_rows', 0)),
        full_fill_rows=int(summary['completion']['full_fill_rows']),
        partial_fill_rows=int(summary['completion']['partial_fill_rows']),
        zero_fill_rows=int(summary['completion']['zero_fill_rows']),
        fee_covered_rows=int(summary['fees']['fee_covered_rows']),
        fee_missing_rows=int(summary['fees']['fee_missing_rows']),
        admissibility_pass_rows=direct.admissibility_pass_rows,
        admissibility_fail_rows=direct.admissibility_fail_rows,
        admissibility_unknown_rows=direct.admissibility_unknown_rows,
    )


def build_report_caveats(benchmark_status: PublishedBenchmarkStatus) -> list[str]:
    caveats = [
        'This pack is an event-level replay benchmark, not an order-level reconstruction or production-fidelity V3 simulator.',
        'The reporting path reuses mounted RH-03, RH-04, RH-05, and RH-06 artifacts as read-only inputs and does not rebuild those layers.',
        '3A and 3B still carry `fees_paid=0.0` because the current phase has no grounded synthetic or blended fee model.',
    ]
    if benchmark_status.comparable:
        caveats.append('Lambdaplex is surfaced only as raw published headline payload because schema alignment is not locked in this phase.')
    else:
        caveats.append(
            'The current Lambdaplex published panel is placeholder or incomplete, so no benchmark metrics were merged into the comparison tables.'
        )
    return caveats


def build_manifest_inputs(
    repo_root: Path,
    benchmark_path: Path,
    reporting_config_path: Path,
    bucket_config_path: Path,
) -> dict[str, Any]:
    inputs = {
        'benchmark_path': str(benchmark_path),
        'benchmark_bytes': benchmark_path.stat().st_size,
        'reporting_config_path': str(reporting_config_path),
        'reporting_config_bytes': reporting_config_path.stat().st_size,
        'bucket_config_path': str(bucket_config_path),
        'bucket_config_bytes': bucket_config_path.stat().st_size,
    }
    for spec in LANE_SPECS:
        csv_path = repo_root / 'data' / 'processed' / spec.csv_filename
        summary_path = repo_root / 'data' / 'processed' / spec.summary_filename
        manifest_path = repo_root / 'data' / 'processed' / spec.manifest_filename
        inputs[f'{spec.lane}_csv_path'] = str(csv_path)
        inputs[f'{spec.lane}_csv_bytes'] = csv_path.stat().st_size
        inputs[f'{spec.lane}_summary_path'] = str(summary_path)
        inputs[f'{spec.lane}_summary_bytes'] = summary_path.stat().st_size
        inputs[f'{spec.lane}_manifest_path'] = str(manifest_path)
        inputs[f'{spec.lane}_manifest_bytes'] = manifest_path.stat().st_size
    return inputs


def build_manifest_outputs(
    comparison_aggregate_path: Path,
    comparison_by_bucket_path: Path,
    comparison_by_side_path: Path,
    final_comparison_path: Path,
    reconciliation_path: Path,
    validation_path: Path,
    summary_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    return {
        'comparison_aggregate_path': str(comparison_aggregate_path),
        'comparison_aggregate_bytes': comparison_aggregate_path.stat().st_size,
        'comparison_by_bucket_path': str(comparison_by_bucket_path),
        'comparison_by_bucket_bytes': comparison_by_bucket_path.stat().st_size,
        'comparison_by_side_path': str(comparison_by_side_path),
        'comparison_by_side_bytes': comparison_by_side_path.stat().st_size,
        'final_comparison_path': str(final_comparison_path),
        'final_comparison_bytes': final_comparison_path.stat().st_size,
        'reconciliation_path': str(reconciliation_path),
        'reconciliation_bytes': reconciliation_path.stat().st_size,
        'validation_path': str(validation_path),
        'validation_bytes': validation_path.stat().st_size,
        'summary_path': str(summary_path),
        'summary_bytes': summary_path.stat().st_size,
        'manifest_path': str(manifest_path),
    }


def serialize_rollup_summary(rollup: RollupSummary) -> dict[str, Any]:
    return {
        'row_count': rollup.row_count,
        'requested_size_raw_total': rollup.requested_size_raw_total,
        'requested_notional_raw_total': rollup.requested_notional_raw_total,
        'filled_size_total': rollup.filled_size_total,
        'filled_notional_total': rollup.filled_notional_total,
        'remainder_size_total': rollup.remainder_size_total,
        'fill_rate': rollup.fill_rate,
        'avg_completion_ratio': rollup.avg_completion_ratio,
        'avg_slippage_bps': rollup.avg_slippage_bps,
        'avg_abs_slippage_bps': rollup.avg_abs_slippage_bps,
        'finite_slippage_rows': rollup.finite_slippage_rows,
        'non_finite_slippage_rows': rollup.non_finite_slippage_rows,
        'full_fill_rows': rollup.full_fill_rows,
        'partial_fill_rows': rollup.partial_fill_rows,
        'zero_fill_rows': rollup.zero_fill_rows,
        'fee_covered_rows': rollup.fee_covered_rows,
        'fee_missing_rows': rollup.fee_missing_rows,
        'admissibility_pass_rows': rollup.admissibility_pass_rows,
        'admissibility_fail_rows': rollup.admissibility_fail_rows,
        'admissibility_unknown_rows': rollup.admissibility_unknown_rows,
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def dig(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_requested_size_text(rollup: RollupSummary) -> str:
    from ..normalize.events import format_scaled_int

    return format_scaled_int(rollup.requested_size_raw_total, 8)


def build_requested_notional_text(rollup: RollupSummary) -> str:
    from ..normalize.events import format_scaled_int

    return format_scaled_int(rollup.requested_notional_raw_total, 6)


def build_decimal_text(value: float) -> str:
    from ..normalize.events import format_decimal

    return format_decimal(value)


def remainder_matches_summary(aggregate: RollupSummary, summary: dict[str, Any]) -> bool:
    remainder = summary['totals'].get('remainder_size_hbar')
    if remainder is None:
        return abs(aggregate.remainder_size_total) <= 1e-12
    return approximately_matches_summary(aggregate.remainder_size_total, remainder)


def bool_text(value: bool) -> str:
    return 'true' if value else 'false'


def approximately_matches_summary(actual: float, expected_text: str | float) -> bool:
    expected = float(expected_text)
    return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-6)

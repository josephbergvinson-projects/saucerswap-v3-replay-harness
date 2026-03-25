from __future__ import annotations

import argparse
import json
from pathlib import Path

from .baseline.v2_realized import run_v2_realized_baseline
from .extract.gigabrain import build_extract_manifest, write_extract_manifest
from .normalize.pipeline import run_normalization
from .reporting.pack import run_reporting_pack
from .settings import load_study_settings
from .sim.hybrid import run_hybrid_lane
from .sim.pure_book import run_pure_book_lane
from .validation.polish import run_validation_polish


def cmd_validate_config(_: argparse.Namespace) -> int:
    settings = load_study_settings(Path('config/study.yaml'))
    print(json.dumps(settings.as_dict(), indent=2))
    return 0


def cmd_layout(_: argparse.Namespace) -> int:
    print("saucerswap-v3-replay-harness")
    print("├── docs")
    print("├── config")
    print("├── sql")
    print("├── benchmarks")
    print("├── data")
    print("├── src")
    print("├── tests")
    print("└── reports")
    return 0


def cmd_probe_gigabrain(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    manifest = build_extract_manifest(root)
    if args.write_manifest:
        out_path = write_extract_manifest(root)
        manifest['manifest_path'] = str(out_path.relative_to(root))
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_normalize_event_level(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_normalization(root)
    payload = {
        'normalized_events_path': str(result.normalized_events_path.relative_to(root)),
        'replay_units_path': str(result.replay_units_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'row_counts': result.manifest['row_counts'],
        'coverage': result.manifest['coverage'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_v2_baseline(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_v2_realized_baseline(root)
    payload = {
        'lane_output_path': str(result.lane_output_path.relative_to(root)),
        'summary_path': str(result.summary_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'row_counts': result.summary['row_counts'],
        'fees': result.summary['fees'],
        'reconciliation': result.summary['reconciliation'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_pure_book(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_pure_book_lane(root)
    payload = {
        'lane_output_path': str(result.lane_output_path.relative_to(root)),
        'summary_path': str(result.summary_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'row_counts': result.summary['row_counts'],
        'completion': result.summary['completion'],
        'slippage_bps': result.summary['slippage_bps'],
        'fees': result.summary['fees'],
        'reconciliation': result.summary['reconciliation'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_hybrid(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_hybrid_lane(root)
    payload = {
        'lane_output_path': str(result.lane_output_path.relative_to(root)),
        'summary_path': str(result.summary_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'row_counts': result.summary['row_counts'],
        'completion': result.summary['completion'],
        'admissibility': result.summary['admissibility'],
        'route_breakdown': result.summary['route_breakdown'],
        'slippage_bps': result.summary['slippage_bps'],
        'fees': result.summary['fees'],
        'reconciliation': result.summary['reconciliation'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_reporting_pack(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_reporting_pack(root)
    payload = {
        'comparison_aggregate_path': str(result.comparison_aggregate_path.relative_to(root)),
        'comparison_by_bucket_path': str(result.comparison_by_bucket_path.relative_to(root)),
        'comparison_by_side_path': str(result.comparison_by_side_path.relative_to(root)),
        'final_comparison_path': str(result.final_comparison_path.relative_to(root)),
        'reconciliation_path': str(result.reconciliation_path.relative_to(root)),
        'validation_path': str(result.validation_path.relative_to(root)),
        'summary_path': str(result.summary_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'benchmark': result.summary['benchmark'],
        'validation': result.summary['validation'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_validation_polish(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run_validation_polish(root)
    payload = {
        'sampled_realized_v2_json_path': str(result.sampled_realized_v2_json_path.relative_to(root)),
        'sampled_realized_v2_markdown_path': str(result.sampled_realized_v2_markdown_path.relative_to(root)),
        'golden_cases_json_path': str(result.golden_cases_json_path.relative_to(root)),
        'golden_cases_markdown_path': str(result.golden_cases_markdown_path.relative_to(root)),
        'validation_report_path': str(result.validation_path.relative_to(root)),
        'summary_path': str(result.summary_path.relative_to(root)),
        'manifest_path': str(result.manifest_path.relative_to(root)),
        'overall_status': result.summary['overall_status'],
        'sampled_realized_v2': result.summary['sampled_realized_v2'],
        'golden_cases': result.summary['golden_cases'],
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='saucerswap-v3-replay')
    sub = parser.add_subparsers(dest='command', required=True)

    validate = sub.add_parser('validate-config', help='Load and print study config')
    validate.set_defaults(func=cmd_validate_config)

    layout = sub.add_parser('layout', help='Print project layout summary')
    layout.set_defaults(func=cmd_layout)

    probe = sub.add_parser('probe-gigabrain', help='Probe Gigabrain access readiness and write extract manifest')
    probe.add_argument('--root', default='.', help='Repo/worktree root to inspect')
    probe.add_argument('--no-write-manifest', dest='write_manifest', action='store_false')
    probe.set_defaults(func=cmd_probe_gigabrain, write_manifest=True)

    normalize = sub.add_parser('normalize-event-level', help='Normalize raw gigabrain CSVs into event-level replay units')
    normalize.add_argument('--root', default='.', help='Repo/worktree root to normalize from')
    normalize.set_defaults(func=cmd_normalize_event_level)

    baseline = sub.add_parser('v2-baseline', help='Build the realized V2 baseline lane from normalized event-level replay units')
    baseline.add_argument('--root', default='.', help='Repo/worktree root to build from')
    baseline.set_defaults(func=cmd_v2_baseline)

    pure_book = sub.add_parser('pure-book', help='Build the 3A pure-book lane from normalized event-level replay units')
    pure_book.add_argument('--root', default='.', help='Repo/worktree root to build from')
    pure_book.set_defaults(func=cmd_pure_book)

    hybrid = sub.add_parser(
        'hybrid',
        help='Build the 3B hybrid lane from mounted 3A pure-book and RH-04 V2 baseline artifacts',
    )
    hybrid.add_argument('--root', default='.', help='Repo/worktree root to build from')
    hybrid.set_defaults(func=cmd_hybrid)

    reporting_pack = sub.add_parser(
        'reporting-pack',
        help='Build the RH-07 comparison pack from mounted RH-04/RH-05/RH-06 artifacts',
    )
    reporting_pack.add_argument('--root', default='.', help='Repo/worktree root to build from')
    reporting_pack.set_defaults(func=cmd_reporting_pack)

    validation_polish = sub.add_parser(
        'validation-polish',
        help='Build the RH-08 validation polish pack from mounted RH-04/RH-05/RH-06/RH-07 artifacts',
    )
    validation_polish.add_argument('--root', default='.', help='Repo/worktree root to build from')
    validation_polish.set_defaults(func=cmd_validation_polish)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extract.gigabrain import build_extract_manifest, write_extract_manifest
from .normalize.pipeline import run_normalization
from .settings import load_study_settings


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

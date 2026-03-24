from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='saucerswap-v3-replay')
    sub = parser.add_subparsers(dest='command', required=True)

    validate = sub.add_parser('validate-config', help='Load and print study config')
    validate.set_defaults(func=cmd_validate_config)

    layout = sub.add_parser('layout', help='Print project layout summary')
    layout.set_defaults(func=cmd_layout)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = Path(__file__).resolve().parent
RERUN_ROOT = ARTIFACT_ROOT / 'rerun-root'

CONFIG_FILES = [
    ('config/hybrid_rule.yaml', 'config/hybrid_rule.yaml'),
    ('config/fees.yaml', 'config/fees.yaml'),
    ('config/buckets.yaml', 'config/buckets.yaml'),
    ('config/reporting.yaml', 'config/reporting.yaml'),
]
BENCHMARK_FILES = [
    ('benchmarks/lambdaplex/published-results.json', 'benchmarks/lambdaplex/published-results.json'),
    ('benchmarks/lambdaplex/source-notes.md', 'benchmarks/lambdaplex/source-notes.md'),
]
PROCESSED_INPUTS = [
    'lane_v2_baseline.csv',
    'v2_baseline_summary.json',
    'v2_baseline_manifest.json',
    'lane_3a_pure_book.csv',
    'pure_book_summary.json',
    'pure_book_manifest.json',
]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)



def copy_file(src_rel: str, dst_rel: str) -> None:
    src = REPO_ROOT / src_rel
    dst = RERUN_ROOT / dst_rel
    ensure_parent(dst)
    shutil.copy2(src, dst)



def symlink_processed_input(filename: str) -> None:
    src = (REPO_ROOT / 'data' / 'processed' / filename).resolve()
    dst = RERUN_ROOT / 'data' / 'processed' / filename
    ensure_parent(dst)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(src)



def main() -> None:
    (RERUN_ROOT / 'data' / 'processed').mkdir(parents=True, exist_ok=True)
    (RERUN_ROOT / 'reports').mkdir(parents=True, exist_ok=True)

    for src_rel, dst_rel in CONFIG_FILES:
        copy_file(src_rel, dst_rel)
    for src_rel, dst_rel in BENCHMARK_FILES:
        copy_file(src_rel, dst_rel)
    for filename in PROCESSED_INPUTS:
        symlink_processed_input(filename)

    print(RERUN_ROOT)


if __name__ == '__main__':
    main()

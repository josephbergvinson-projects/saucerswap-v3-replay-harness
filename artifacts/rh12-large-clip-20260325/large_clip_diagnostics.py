from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / 'data' / 'processed'
OUTPUT = Path(__file__).with_name('diagnostics_summary.json')

BUCKETS = [
    ('<1k', 0.0, 1000.0),
    ('1k-5k', 1000.0, 5000.0),
    ('5k-10k', 5000.0, 10000.0),
    ('10k-25k', 10000.0, 25000.0),
    ('25k+', 25000.0, None),
]
MAX_SLIPPAGE_BPS = 50.0


@dataclass(frozen=True)
class Row:
    replay_unit_id: str
    side: str
    requested_size: float
    requested_notional: float
    filled_size: float
    filled_notional: float
    completion_ratio: float
    reference_price: float
    avg_execution_price: float
    remainder_size: float
    admissibility_passed: bool | None


class Stats:
    def __init__(self) -> None:
        self.rows = 0
        self.remainder_rows = 0
        self.requested_size = 0.0
        self.requested_notional = 0.0
        self.current_completion_sum = 0.0
        self.blended_completion_sum = 0.0
        self.current_full_fills = 0
        self.blended_full_fills = 0
        self.current_filled_size = 0.0
        self.blended_filled_size = 0.0
        self.current_admissible_residual_rows = 0
        self.current_inadmissible_residual_rows = 0
        self.blended_admissible_residual_rows = 0
        self.blended_only_residual_rows = 0
        self.size_limited_rows = 0

    def add(
        self,
        pure: Row,
        hybrid: Row,
        baseline: Row,
        *,
        current_admissible: bool,
        blended_admissible: bool,
    ) -> None:
        self.rows += 1
        self.requested_size += pure.requested_size
        self.requested_notional += pure.requested_notional
        self.current_completion_sum += hybrid.completion_ratio
        self.current_filled_size += hybrid.filled_size
        blended_filled_size = projected_filled_size(pure, baseline, blended_admissible)
        blended_completion = 0.0 if pure.requested_size <= 0 else blended_filled_size / pure.requested_size
        self.blended_completion_sum += blended_completion
        self.blended_filled_size += blended_filled_size
        if hybrid.completion_ratio >= 1.0 - 1e-12:
            self.current_full_fills += 1
        if blended_completion >= 1.0 - 1e-12:
            self.blended_full_fills += 1

        if pure.remainder_size > 1e-12:
            self.remainder_rows += 1
            if current_admissible:
                self.current_admissible_residual_rows += 1
            else:
                self.current_inadmissible_residual_rows += 1
            if blended_admissible:
                self.blended_admissible_residual_rows += 1
            if blended_admissible and not current_admissible:
                self.blended_only_residual_rows += 1
            if baseline.filled_size + 1e-12 < pure.remainder_size:
                self.size_limited_rows += 1

    def as_dict(self) -> dict[str, float | int]:
        return {
            'rows': self.rows,
            'requested_notional_usdc': round(self.requested_notional, 6),
            'requested_size_hbar': round(self.requested_size, 12),
            'current_full_fill_rate': safe_div(self.current_full_fills, self.rows),
            'projected_blended_full_fill_rate': safe_div(self.blended_full_fills, self.rows),
            'current_avg_completion_ratio': safe_div(self.current_completion_sum, self.rows),
            'projected_blended_avg_completion_ratio': safe_div(self.blended_completion_sum, self.rows),
            'current_filled_size_ratio': safe_div(self.current_filled_size, self.requested_size),
            'projected_blended_filled_size_ratio': safe_div(self.blended_filled_size, self.requested_size),
            'pure_book_residual_rows': self.remainder_rows,
            'pure_book_residual_row_share': safe_div(self.remainder_rows, self.rows),
            'current_admissible_residual_rows': self.current_admissible_residual_rows,
            'current_inadmissible_residual_rows': self.current_inadmissible_residual_rows,
            'blended_admissible_residual_rows': self.blended_admissible_residual_rows,
            'blended_only_residual_rows': self.blended_only_residual_rows,
            'available_size_limited_rows': self.size_limited_rows,
        }


def safe_div(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return round(n / d, 10)


def slippage_bps(reference_price: float, execution_price: float, side: str) -> float:
    if side == 'buy':
        return ((execution_price / reference_price) - 1.0) * 10_000
    return ((reference_price / execution_price) - 1.0) * 10_000


def assign_bucket(requested_notional: float) -> str:
    for label, minimum, maximum in BUCKETS:
        if requested_notional < minimum:
            continue
        if maximum is None or requested_notional < maximum:
            return label
    raise ValueError(f'No bucket for {requested_notional}')


def parse_bool(text: str) -> bool | None:
    stripped = (text or '').strip().lower()
    if stripped == 'true':
        return True
    if stripped == 'false':
        return False
    return None


def row_from_csv(row: dict[str, str]) -> Row:
    return Row(
        replay_unit_id=row['replay_unit_id'],
        side=row['side'],
        requested_size=float(row['requested_size']),
        requested_notional=float(row['requested_notional']),
        filled_size=float(row['filled_size']),
        filled_notional=float(row['filled_notional']),
        completion_ratio=float(row['completion_ratio']),
        reference_price=float(row['reference_price']),
        avg_execution_price=float(row['avg_execution_price']),
        remainder_size=float(row['remainder_size']),
        admissibility_passed=parse_bool(row.get('admissibility_passed', '')),
    )


def projected_filled_size(pure: Row, baseline: Row, blended_admissible: bool) -> float:
    if pure.remainder_size <= 1e-12 or not blended_admissible:
        return pure.filled_size
    return pure.filled_size + min(pure.remainder_size, baseline.filled_size)


def projected_blended_execution_price(pure: Row, baseline: Row) -> float:
    routed_size = min(pure.remainder_size, baseline.filled_size)
    total_size = pure.filled_size + routed_size
    if total_size <= 0:
        return pure.reference_price
    return (pure.filled_notional + routed_size * baseline.avg_execution_price) / total_size


def iter_aligned_rows() -> tuple[Row, Row, Row]:
    pure_path = PROCESSED / 'lane_3a_pure_book.csv'
    hybrid_path = PROCESSED / 'lane_3b_hybrid.csv'
    baseline_path = PROCESSED / 'lane_v2_baseline.csv'
    with (
        pure_path.open('r', encoding='utf-8', newline='') as pure_handle,
        hybrid_path.open('r', encoding='utf-8', newline='') as hybrid_handle,
        baseline_path.open('r', encoding='utf-8', newline='') as baseline_handle,
    ):
        pure_reader = csv.DictReader(pure_handle)
        hybrid_reader = csv.DictReader(hybrid_handle)
        baseline_reader = csv.DictReader(baseline_handle)
        for row_number, triple in enumerate(zip_longest(pure_reader, hybrid_reader, baseline_reader), start=1):
            pure_raw, hybrid_raw, baseline_raw = triple
            if pure_raw is None or hybrid_raw is None or baseline_raw is None:
                raise ValueError(f'Input row-count mismatch at row {row_number}')
            if not (
                pure_raw['replay_unit_id'] == hybrid_raw['replay_unit_id'] == baseline_raw['replay_unit_id']
            ):
                raise ValueError(
                    'Replay-unit alignment mismatch at row '
                    f"{row_number}: {pure_raw['replay_unit_id']} / {hybrid_raw['replay_unit_id']} / {baseline_raw['replay_unit_id']}"
                )
            yield row_from_csv(pure_raw), row_from_csv(hybrid_raw), row_from_csv(baseline_raw)


def main() -> None:
    stats_by_bucket = {label: Stats() for label, _, _ in BUCKETS}
    overall = Stats()
    sample_blended_only: list[dict[str, float | str]] = []

    for pure, hybrid, baseline in iter_aligned_rows():
        current_admissible = (
            pure.remainder_size > 1e-12
            and slippage_bps(pure.reference_price, baseline.avg_execution_price, pure.side) <= MAX_SLIPPAGE_BPS
        )
        blended_price = projected_blended_execution_price(pure, baseline)
        blended_admissible = (
            pure.remainder_size > 1e-12
            and slippage_bps(pure.reference_price, blended_price, pure.side) <= MAX_SLIPPAGE_BPS
        )
        bucket = assign_bucket(pure.requested_notional)
        stats_by_bucket[bucket].add(
            pure,
            hybrid,
            baseline,
            current_admissible=current_admissible,
            blended_admissible=blended_admissible,
        )
        overall.add(
            pure,
            hybrid,
            baseline,
            current_admissible=current_admissible,
            blended_admissible=blended_admissible,
        )

        if blended_admissible and not current_admissible and len(sample_blended_only) < 20:
            sample_blended_only.append(
                {
                    'replay_unit_id': pure.replay_unit_id,
                    'bucket': bucket,
                    'side': pure.side,
                    'requested_notional_usdc': round(pure.requested_notional, 6),
                    'requested_size_hbar': round(pure.requested_size, 6),
                    'pure_book_completion_ratio': round(pure.completion_ratio, 6),
                    'baseline_avg_execution_price': round(baseline.avg_execution_price, 12),
                    'projected_blended_execution_price': round(blended_price, 12),
                    'current_backstop_slippage_bps': round(
                        slippage_bps(pure.reference_price, baseline.avg_execution_price, pure.side), 6
                    ),
                    'projected_blended_slippage_bps': round(
                        slippage_bps(pure.reference_price, blended_price, pure.side), 6
                    ),
                }
            )

    payload = {
        'max_slippage_bps': MAX_SLIPPAGE_BPS,
        'overall': overall.as_dict(),
        'by_bucket': {bucket: stats.as_dict() for bucket, stats in stats_by_bucket.items()},
        'sample_blended_only_rows': sample_blended_only,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuerySpec:
    name: str
    sql_path: Path
    output_path: Path


def default_query_specs(root: Path) -> list[QuerySpec]:
    return [
        QuerySpec(
            name='trades',
            sql_path=root / 'sql' / 'extract_hbar_usdc_v2_015_trades.sql',
            output_path=root / 'data' / 'raw' / 'gigabrain' / 'hbar_usdc_v2_015_trades.parquet',
        ),
        QuerySpec(
            name='swap_metadata',
            sql_path=root / 'sql' / 'extract_hbar_usdc_v2_015_swap_metadata.sql',
            output_path=root / 'data' / 'raw' / 'gigabrain' / 'hbar_usdc_v2_015_swap_metadata.parquet',
        ),
    ]

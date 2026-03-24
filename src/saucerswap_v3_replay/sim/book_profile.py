from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class BookLevel:
    spread_bps: float
    size_usd: float


@dataclass(frozen=True)
class BookProfile:
    total_depth_usd: float
    replenish_per_replay_unit: bool
    levels: tuple[BookLevel, ...]

    @property
    def fingerprint(self) -> str:
        payload = {
            'total_depth_usd': self.total_depth_usd,
            'replenish_per_replay_unit': self.replenish_per_replay_unit,
            'levels': [
                {
                    'spread_bps': level.spread_bps,
                    'size_usd': level.size_usd,
                }
                for level in self.levels
            ],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()


def allocate_depth(total_depth_usd: float, levels: list[tuple[float, float]]) -> list[BookLevel]:
    total_weight = sum(weight for _, weight in levels)
    if total_depth_usd < 0:
        raise ValueError('total_depth_usd must be non-negative')
    if total_weight <= 0:
        raise ValueError('Book levels must have positive total weight')
    return [
        BookLevel(spread_bps=spread, size_usd=total_depth_usd * (weight / total_weight))
        for spread, weight in levels
    ]


def load_book_profile(path: str | Path) -> BookProfile:
    config_path = Path(path)
    total_depth_usd, replenish_per_replay_unit, weighted_levels = _parse_book_profile_text(
        config_path.read_text(encoding='utf-8')
    )
    return BookProfile(
        total_depth_usd=total_depth_usd,
        replenish_per_replay_unit=replenish_per_replay_unit,
        levels=tuple(allocate_depth(total_depth_usd, weighted_levels)),
    )


def _parse_book_profile_text(text: str) -> tuple[float, bool, list[tuple[float, float]]]:
    in_pure_book = False
    total_depth_usd: float | None = None
    replenish_per_replay_unit = True
    weighted_levels: list[tuple[float, float]] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == 'pure_book:':
            in_pure_book = True
            continue
        if not in_pure_book:
            continue
        if stripped.startswith('total_depth_usd:'):
            total_depth_usd = float(stripped.split(':', 1)[1].strip())
            continue
        if stripped.startswith('replenish_per_replay_unit:'):
            replenish_per_replay_unit = stripped.split(':', 1)[1].strip().lower() == 'true'
            continue
        if stripped.startswith('- {') and stripped.endswith('}'):
            inline_mapping = _parse_inline_mapping(stripped[1:].strip())
            weighted_levels.append((float(inline_mapping['spread_bps']), float(inline_mapping['weight'])))

    if total_depth_usd is None:
        raise ValueError('pure_book.total_depth_usd is required')
    if not weighted_levels:
        raise ValueError('pure_book.levels must define at least one level')
    return total_depth_usd, replenish_per_replay_unit, weighted_levels


def _parse_inline_mapping(text: str) -> dict[str, str]:
    stripped = text.strip()
    if not (stripped.startswith('{') and stripped.endswith('}')):
        raise ValueError(f'Unsupported inline mapping: {text!r}')
    payload = stripped[1:-1]
    mapping: dict[str, str] = {}
    for entry in payload.split(','):
        key, value = entry.split(':', 1)
        mapping[key.strip()] = value.strip()
    return mapping

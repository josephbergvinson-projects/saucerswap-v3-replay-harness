from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

ALLOWED_BENCHMARK_STATUSES = frozenset({'placeholder', 'incomplete', 'comparable'})
REQUIRED_COMPARABLE_HEADLINE_FIELDS = (
    'fill_rate',
    'avg_completion_ratio',
    'avg_slippage_bps',
    'avg_abs_slippage_bps',
    'remainder_size_hbar',
)
ALLOWED_COMPARABLE_HEADLINE_FIELDS = frozenset(
    {
        'row_count',
        'requested_size_hbar',
        'requested_notional_usdc',
        'filled_size_hbar',
        'filled_notional_usdc',
        'remainder_size_hbar',
        'fill_rate',
        'avg_completion_ratio',
        'avg_slippage_bps',
        'avg_abs_slippage_bps',
        'finite_slippage_rows',
        'non_finite_slippage_rows',
        'full_fill_rows',
        'partial_fill_rows',
        'zero_fill_rows',
        'fee_covered_rows',
        'fee_missing_rows',
        'admissibility_pass_rows',
        'admissibility_fail_rows',
        'admissibility_unknown_rows',
    }
)
INTEGER_COMPARABLE_HEADLINE_FIELDS = frozenset(
    {
        'row_count',
        'finite_slippage_rows',
        'non_finite_slippage_rows',
        'full_fill_rows',
        'partial_fill_rows',
        'zero_fill_rows',
        'fee_covered_rows',
        'fee_missing_rows',
        'admissibility_pass_rows',
        'admissibility_fail_rows',
        'admissibility_unknown_rows',
    }
)


@dataclass(frozen=True)
class BenchmarkProvenance:
    local_payload_state: str
    local_payload_complete: bool
    blocking_reason: str
    captured_artifacts: tuple[str, ...]
    mapping_notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            'local_payload_state': self.local_payload_state,
            'local_payload_complete': self.local_payload_complete,
            'blocking_reason': self.blocking_reason,
            'captured_artifacts': list(self.captured_artifacts),
            'mapping_notes': list(self.mapping_notes),
        }

    @property
    def summary(self) -> str:
        parts = [
            f'local_payload_state={self.local_payload_state}',
            f'local_payload_complete={str(self.local_payload_complete).lower()}',
        ]
        if self.blocking_reason:
            parts.append(self.blocking_reason)
        if self.mapping_notes:
            parts.append('mapping_notes=' + '; '.join(self.mapping_notes))
        if self.captured_artifacts:
            parts.append('captured_artifacts=' + ', '.join(self.captured_artifacts))
        return ' | '.join(parts)


@dataclass(frozen=True)
class PublishedBenchmarkStatus:
    schema_version: str
    source: str
    market: str
    status: str
    source_notes_path: str
    source_notes_markdown: str
    headline_metrics: dict[str, Any]
    comparable_headline_metrics: dict[str, int | float]
    provenance: BenchmarkProvenance
    notes: tuple[str, ...]

    @property
    def comparable(self) -> bool:
        return self.status == 'comparable'

    @property
    def notes_summary(self) -> str:
        return ' '.join(self.notes).strip()

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'source': self.source,
            'market': self.market,
            'status': self.status,
            'comparable': self.comparable,
            'source_notes_path': self.source_notes_path,
            'headline_metrics': self.headline_metrics,
            'comparable_headline_metrics': self.comparable_headline_metrics,
            'provenance': self.provenance.as_dict(),
            'notes': list(self.notes),
        }


def load_published_results(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'{path} must contain a top-level JSON object')
    return payload


def load_published_benchmark_status(path: Path) -> PublishedBenchmarkStatus:
    benchmark_path = Path(path).resolve()
    payload = load_published_results(benchmark_path)
    repo_root = benchmark_path.parents[2]

    required_keys = {
        'schema_version',
        'source',
        'market',
        'status',
        'source_notes_path',
        'headline_metrics',
        'comparable_headline_metrics',
        'provenance',
    }
    missing_keys = sorted(required_keys - payload.keys())
    if missing_keys:
        raise ValueError(f'{benchmark_path} missing required keys: {", ".join(missing_keys)}')

    status = str(payload['status']).strip().lower()
    if status not in ALLOWED_BENCHMARK_STATUSES:
        raise ValueError(
            f'{benchmark_path} status must be one of {sorted(ALLOWED_BENCHMARK_STATUSES)}; got {payload["status"]!r}'
        )

    source_notes_path = str(payload['source_notes_path']).strip()
    if not source_notes_path:
        raise ValueError(f'{benchmark_path} source_notes_path must be non-empty')
    source_notes_relative = Path(source_notes_path)
    if source_notes_relative.is_absolute():
        raise ValueError(f'{benchmark_path} source_notes_path must be repo-relative, not absolute')
    source_notes_file = (repo_root / source_notes_relative).resolve()
    if not source_notes_file.is_file():
        raise ValueError(f'{benchmark_path} source_notes_path does not exist: {source_notes_path}')

    headline_metrics = payload['headline_metrics']
    if not isinstance(headline_metrics, dict):
        raise ValueError(f'{benchmark_path} headline_metrics must be a mapping')

    comparable_headline_metrics = _normalize_comparable_headline_metrics(
        payload['comparable_headline_metrics'],
        benchmark_path,
    )
    if status == 'comparable':
        missing_fields = [
            field for field in REQUIRED_COMPARABLE_HEADLINE_FIELDS if field not in comparable_headline_metrics
        ]
        if missing_fields:
            raise ValueError(
                f'{benchmark_path} comparable benchmark payload missing required comparable_headline_metrics: '
                + ', '.join(missing_fields)
            )

    provenance = _load_provenance(payload['provenance'], benchmark_path)
    notes = tuple(_normalize_notes(payload.get('notes', []), field_name='notes'))

    return PublishedBenchmarkStatus(
        schema_version=str(payload['schema_version']).strip(),
        source=str(payload['source']).strip(),
        market=str(payload['market']).strip(),
        status=status,
        source_notes_path=source_notes_path,
        source_notes_markdown=source_notes_file.read_text(encoding='utf-8'),
        headline_metrics=dict(headline_metrics),
        comparable_headline_metrics=comparable_headline_metrics,
        provenance=provenance,
        notes=notes,
    )


def _load_provenance(value: Any, benchmark_path: Path) -> BenchmarkProvenance:
    if not isinstance(value, dict):
        raise ValueError(f'{benchmark_path} provenance must be a mapping')
    required_keys = {
        'local_payload_state',
        'local_payload_complete',
        'blocking_reason',
        'captured_artifacts',
        'mapping_notes',
    }
    missing_keys = sorted(required_keys - value.keys())
    if missing_keys:
        raise ValueError(f'{benchmark_path} provenance missing required keys: {", ".join(missing_keys)}')
    return BenchmarkProvenance(
        local_payload_state=str(value['local_payload_state']).strip(),
        local_payload_complete=_normalize_bool(value['local_payload_complete'], benchmark_path, 'local_payload_complete'),
        blocking_reason=str(value['blocking_reason']).strip(),
        captured_artifacts=tuple(_normalize_notes(value['captured_artifacts'], field_name='captured_artifacts')),
        mapping_notes=tuple(_normalize_notes(value['mapping_notes'], field_name='mapping_notes')),
    )


def _normalize_bool(value: Any, benchmark_path: Path, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f'{benchmark_path} {field_name} must be a boolean')


def _normalize_notes(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        raise ValueError(f'{field_name} must be a string or list of strings')
    notes: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f'{field_name} entries must be strings')
        text = item.strip()
        if text:
            notes.append(text)
    return notes


def _normalize_comparable_headline_metrics(value: Any, benchmark_path: Path) -> dict[str, int | float]:
    if not isinstance(value, dict):
        raise ValueError(f'{benchmark_path} comparable_headline_metrics must be a mapping')
    normalized: dict[str, int | float] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        if key not in ALLOWED_COMPARABLE_HEADLINE_FIELDS:
            raise ValueError(f'{benchmark_path} comparable_headline_metrics contains unsupported field: {key}')
        if raw_value is None:
            continue
        try:
            number = int(raw_value) if key in INTEGER_COMPARABLE_HEADLINE_FIELDS else float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{benchmark_path} comparable_headline_metrics[{key!r}] must be numeric') from exc
        normalized[key] = number
    return normalized

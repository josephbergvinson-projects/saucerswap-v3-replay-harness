from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..settings import load_study_settings


@dataclass(frozen=True)
class QuerySpec:
    name: str
    sql_path: Path
    output_path: Path


@dataclass(frozen=True)
class AccessRouteProbe:
    kind: str
    ready: bool
    missing_keys: list[str]


@dataclass(frozen=True)
class AccessProbe:
    env_files_loaded: list[str]
    candidate_env_files_present: list[str]
    mysql: AccessRouteProbe
    metabase: AccessRouteProbe

    @property
    def any_ready(self) -> bool:
        return self.mysql.ready or self.metabase.ready


MYSQL_KEYS = [
    'GIGABRAIN_MYSQL_HOST',
    'GIGABRAIN_MYSQL_PORT',
    'GIGABRAIN_MYSQL_DATABASE',
    'GIGABRAIN_MYSQL_USER',
    'GIGABRAIN_MYSQL_PASSWORD',
]

METABASE_KEYS = [
    'METABASE_URL',
    'METABASE_API_KEY',
    'METABASE_CARD_ID_TRADES',
    'METABASE_CARD_ID_SWAP_METADATA',
    'METABASE_CARD_ID_PRICES',
]


def default_query_specs(root: Path) -> list[QuerySpec]:
    raw_dir = root / 'data' / 'raw' / 'gigabrain'
    sql_dir = root / 'sql'
    return [
        QuerySpec(
            name='trades',
            sql_path=sql_dir / 'extract_hbar_usdc_v2_015_trades.sql',
            output_path=raw_dir / 'hbar_usdc_v2_015_trades.parquet',
        ),
        QuerySpec(
            name='swap_metadata',
            sql_path=sql_dir / 'extract_hbar_usdc_v2_015_swap_metadata.sql',
            output_path=raw_dir / 'hbar_usdc_v2_015_swap_metadata.parquet',
        ),
        QuerySpec(
            name='reference_prices',
            sql_path=sql_dir / 'extract_hbar_reference_prices.sql',
            output_path=raw_dir / 'hbar_reference_prices.parquet',
        ),
        QuerySpec(
            name='fee_inputs',
            sql_path=sql_dir / 'extract_v2_fee_inputs.sql',
            output_path=raw_dir / 'v2_fee_inputs.parquet',
        ),
    ]


def repo_root_for_env_probe(root: Path) -> Path:
    if root.parent.name == '.worktrees':
        return root.parent.parent
    return root


def candidate_env_paths(root: Path) -> list[Path]:
    paths = [root / '.env']
    repo_root = repo_root_for_env_probe(root)
    repo_env = repo_root / '.env'
    if repo_env not in paths:
        paths.append(repo_env)
    return paths


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):]
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_env(root: Path, env: Mapping[str, str] | None = None) -> tuple[dict[str, str], list[str], list[str]]:
    resolved = dict(env or os.environ)
    loaded: list[str] = []
    present: list[str] = []
    for path in candidate_env_paths(root):
        if not path.exists():
            continue
        present.append(str(path))
        file_values = load_env_file(path)
        for key, value in file_values.items():
            resolved.setdefault(key, value)
        loaded.append(str(path))
    return resolved, loaded, present


def _missing_keys(env: Mapping[str, str], keys: list[str]) -> list[str]:
    return [key for key in keys if not env.get(key)]


def probe_access(root: Path, env: Mapping[str, str] | None = None) -> AccessProbe:
    resolved, loaded, present = resolve_env(root, env)
    mysql_missing = _missing_keys(resolved, MYSQL_KEYS)
    metabase_missing = _missing_keys(resolved, METABASE_KEYS)
    return AccessProbe(
        env_files_loaded=loaded,
        candidate_env_files_present=present,
        mysql=AccessRouteProbe(kind='mysql', ready=not mysql_missing, missing_keys=mysql_missing),
        metabase=AccessRouteProbe(kind='metabase', ready=not metabase_missing, missing_keys=metabase_missing),
    )


def projected_fields_from_sql(sql_text: str) -> list[str] | None:
    fields: list[str] = []
    in_select = False
    for raw_line in sql_text.splitlines():
        line = raw_line.split('--', 1)[0].strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith('SELECT'):
            in_select = True
            line = line[6:].strip()
            upper = line.upper()
        if not in_select:
            continue
        if upper.startswith('FROM '):
            break
        if line == '*':
            return None
        if '*' in line:
            return None
        fragment = line.rstrip(',')
        if not fragment:
            continue
        lower = fragment.lower()
        if ' as ' in lower:
            alias = fragment.rsplit(' as ', 1)[-1].rsplit(' AS ', 1)[-1].strip()
            fields.append(alias)
            continue
        fields.append(fragment.split('.')[-1].strip())
    return fields or None


def field_inventory_from_sql_path(path: Path) -> dict[str, Any]:
    projected = projected_fields_from_sql(path.read_text(encoding='utf-8'))
    if projected is None:
        return {
            'source': 'sql_template',
            'fields': None,
            'known': False,
            'notes': 'SQL template uses SELECT *; live extract required to inventory fields.',
        }
    return {
        'source': 'sql_template',
        'fields': projected,
        'known': True,
        'notes': 'Projected fields inferred from the SQL template.',
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def build_extract_manifest(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    settings = load_study_settings(root / 'config' / 'study.yaml')
    access = probe_access(root, env)
    query_entries: list[dict[str, Any]] = []
    missing_fields: list[str] = []

    for spec in default_query_specs(root):
        inventory = field_inventory_from_sql_path(spec.sql_path)
        if not inventory['known']:
            missing_fields.append(spec.name)
        query_entries.append(
            {
                'name': spec.name,
                'sql_path': str(spec.sql_path.relative_to(root)),
                'output_path': str(spec.output_path.relative_to(root)),
                'extract_status': 'not_run_missing_access' if not access.any_ready else 'ready_to_run',
                'row_count': None,
                'min_timestamp': None,
                'max_timestamp': None,
                'field_inventory': inventory,
            }
        )

    blocker_notes: list[str] = []
    if not access.any_ready:
        blocker_notes.append(
            'No discoverable Gigabrain MySQL or Metabase credential set was found in the process environment or repo-local .env candidates; live read-only extract was therefore not runnable from this worktree.'
        )
    if missing_fields:
        blocker_notes.append(
            'Some SQL templates still use SELECT * and therefore do not expose a stable field inventory before the first live extract: ' + ', '.join(missing_fields)
        )

    normalization_missing: list[str] = []
    if not access.any_ready:
        normalization_missing.append('live historical extract access is not configured')
    normalization_missing.append('raw trades extract is not materialized locally')
    if 'reference_prices' in missing_fields:
        normalization_missing.append('reference-price schema is not yet field-verified')
    if 'fee_inputs' in missing_fields:
        normalization_missing.append('fee-input schema is not yet field-verified')

    manifest = {
        'status': 'blocked_missing_access' if not access.any_ready else 'ready_for_live_extract',
        'generated_at_utc': _iso_now(),
        'study': {
            'name': settings.name,
            'market': settings.market,
            'source_protocol': settings.source_protocol,
            'source_pool_name': settings.source_pool_name,
            'source_pool_id': settings.source_pool_id,
            'source_pool_address': settings.source_pool_address,
            'timezone': settings.timezone,
            'reference_price_mode': settings.reference_price_mode,
            'replay_unit_mode': settings.replay_unit_mode,
            'baseline_lane': settings.baseline_lane,
        },
        'access_probe': {
            'env_files_loaded': access.env_files_loaded,
            'candidate_env_files_present': access.candidate_env_files_present,
            'mysql': asdict(access.mysql),
            'metabase': asdict(access.metabase),
        },
        'queries': query_entries,
        'realized_window': {
            'min_timestamp': None,
            'max_timestamp': None,
            'timezone': settings.timezone,
            'notes': 'Unknown until a live extract succeeds.',
        },
        'blocker_notes': blocker_notes,
        'normalization_readiness': {
            'can_start': False if normalization_missing else True,
            'decision': 'RH-03 cannot begin immediately; extraction access and field verification must be completed first.' if normalization_missing else 'RH-03 can begin.',
            'missing_requirements': normalization_missing,
        },
    }
    return manifest


def write_extract_manifest(root: Path, env: Mapping[str, str] | None = None) -> Path:
    manifest = build_extract_manifest(root, env)
    out_path = root / 'data' / 'raw' / 'gigabrain' / 'extract-manifest.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return out_path

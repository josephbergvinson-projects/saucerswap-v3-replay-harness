from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised via fallback path in runtime checks
    yaml = None


@dataclass(frozen=True)
class StudySettings:
    name: str
    market: str
    source_protocol: str
    source_pool_name: str
    source_pool_id: int
    source_pool_address: str
    timezone: str
    reference_price_mode: str
    replay_unit_mode: str
    baseline_lane: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    if value.lower() == 'null':
        return None
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        return value



def _fallback_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    section: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not line.startswith(' '):
            key = stripped[:-1] if stripped.endswith(':') else stripped
            root[key] = {}
            section = root[key]
            continue
        if section is None:
            raise ValueError('Encountered indented YAML before a section header')
        key, value = stripped.split(':', 1)
        section[key.strip()] = _coerce_scalar(value)
    return root



def _load_yaml_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    if yaml is not None:
        return yaml.safe_load(text)
    return _fallback_simple_yaml(text)



def load_study_settings(path: Path) -> StudySettings:
    payload = _load_yaml_payload(path)
    study = payload['study']
    return StudySettings(
        name=study['name'],
        market=study['market'],
        source_protocol=study['source_protocol'],
        source_pool_name=study['source_pool_name'],
        source_pool_id=int(study['source_pool_id']),
        source_pool_address=study['source_pool_address'],
        timezone=study['timezone'],
        reference_price_mode=study['reference_price_mode'],
        replay_unit_mode=study['replay_unit_mode'],
        baseline_lane=study['baseline_lane'],
    )

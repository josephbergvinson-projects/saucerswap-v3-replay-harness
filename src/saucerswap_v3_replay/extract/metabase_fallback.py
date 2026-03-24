from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetabaseExportSpec:
    card_id: str
    output_name: str

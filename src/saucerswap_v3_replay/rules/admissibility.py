from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..metrics.core import slippage_bps
from ..settings import _load_yaml_payload


@dataclass(frozen=True)
class HybridRule:
    mode: str
    reference_price_basis: str
    quote_requirement: str
    max_buy_slippage_bps: float
    max_sell_slippage_bps: float
    require_backstop_quote: bool
    failure_policy: str
    notes: str = ''

    def max_slippage_bps_for_side(self, side: str) -> float:
        if side == 'buy':
            return self.max_buy_slippage_bps
        if side == 'sell':
            return self.max_sell_slippage_bps
        raise ValueError(f'Unsupported side: {side}')

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_hybrid_rule(path: str | Path) -> HybridRule:
    payload = _load_yaml_payload(Path(path))
    rule = payload.get('hybrid_rule')
    if not isinstance(rule, dict):
        raise ValueError(f'{path} must define a top-level hybrid_rule mapping')
    return HybridRule(
        mode=str(rule['mode']),
        reference_price_basis=str(rule['reference_price_basis']),
        quote_requirement=str(rule['quote_requirement']),
        max_buy_slippage_bps=float(rule['max_buy_slippage_bps']),
        max_sell_slippage_bps=float(rule['max_sell_slippage_bps']),
        require_backstop_quote=bool(rule['require_backstop_quote']),
        failure_policy=str(rule['failure_policy']),
        notes=str(rule.get('notes') or ''),
    )


def passes_limit_price(side: str, execution_price: float, limit_price: float) -> bool:
    if side == 'buy':
        return execution_price <= limit_price
    if side == 'sell':
        return execution_price >= limit_price
    raise ValueError(f'Unsupported side: {side}')


def passes_slippage_cap(side: str, reference_price: float, execution_price: float, max_slippage_bps: float) -> bool:
    if reference_price <= 0:
        raise ValueError('Reference price must be positive')
    if execution_price <= 0:
        return False
    realized_bps = slippage_bps(reference_price, execution_price, side)
    return realized_bps <= max_slippage_bps


def passes_hybrid_admissibility(
    rule: HybridRule,
    *,
    side: str,
    reference_price: float,
    execution_price: float | None,
    quote_available: bool,
) -> bool:
    if rule.require_backstop_quote and not quote_available:
        return False
    if execution_price is None:
        return False
    if rule.mode != 'slippage_cap_bps':
        raise ValueError(f'Unsupported hybrid admissibility mode: {rule.mode}')
    return passes_slippage_cap(
        side=side,
        reference_price=reference_price,
        execution_price=execution_price,
        max_slippage_bps=rule.max_slippage_bps_for_side(side),
    )

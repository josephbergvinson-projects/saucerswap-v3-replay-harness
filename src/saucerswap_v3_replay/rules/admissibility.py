from __future__ import annotations


def passes_limit_price(side: str, execution_price: float, limit_price: float) -> bool:
    if side == 'buy':
        return execution_price <= limit_price
    if side == 'sell':
        return execution_price >= limit_price
    raise ValueError(f'Unsupported side: {side}')


def passes_slippage_cap(side: str, reference_price: float, execution_price: float, max_slippage_bps: float) -> bool:
    if reference_price <= 0:
        raise ValueError('Reference price must be positive')
    if side == 'buy':
        realized_bps = ((execution_price / reference_price) - 1.0) * 10_000
        return realized_bps <= max_slippage_bps
    if side == 'sell':
        realized_bps = ((reference_price / execution_price) - 1.0) * 10_000
        return realized_bps <= max_slippage_bps
    raise ValueError(f'Unsupported side: {side}')

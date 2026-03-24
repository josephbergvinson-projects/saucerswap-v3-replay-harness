from __future__ import annotations


def completion_ratio(filled_size: float, requested_size: float) -> float:
    if requested_size <= 0:
        return 0.0
    return filled_size / requested_size


def slippage_bps(reference_price: float, execution_price: float, side: str) -> float:
    if reference_price <= 0:
        raise ValueError('Reference price must be positive')
    if side == 'buy':
        return ((execution_price / reference_price) - 1.0) * 10_000
    if side == 'sell':
        return ((reference_price / execution_price) - 1.0) * 10_000
    raise ValueError(f'Unsupported side: {side}')

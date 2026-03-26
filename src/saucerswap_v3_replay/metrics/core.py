from __future__ import annotations

from dataclasses import dataclass
import math

Q96 = float(2**96)


@dataclass(frozen=True)
class AmmPoolSpotReference:
    pre_trade_spot_price: float
    post_trade_spot_price: float


def completion_ratio(filled_size: float, requested_size: float) -> float:
    if requested_size <= 0:
        return 0.0
    return filled_size / requested_size


def slippage_bps(reference_price: float, execution_price: float, side: str) -> float:
    if reference_price <= 0:
        raise ValueError('Reference price must be positive')
    if side == 'buy':
        if execution_price <= 0:
            return -10_000.0
        return ((execution_price / reference_price) - 1.0) * 10_000
    if side == 'sell':
        if execution_price <= 0:
            return math.inf
        return ((reference_price / execution_price) - 1.0) * 10_000
    raise ValueError(f'Unsupported side: {side}')


def symmetric_reference_denominator_bps(reference_price: float, execution_price: float, side: str) -> float:
    if reference_price <= 0:
        raise ValueError('Reference price must be positive')
    if side == 'buy':
        return ((execution_price - reference_price) / reference_price) * 10_000
    if side == 'sell':
        return ((reference_price - execution_price) / reference_price) * 10_000
    raise ValueError(f'Unsupported side: {side}')


def reconstruct_amm_pre_trade_spot_reference(
    *,
    side: str,
    sqrt_ratio_x96: float | None,
    liquidity: float | None,
    amount_a: float | None,
    amount_b: float | None,
) -> AmmPoolSpotReference | None:
    if (
        sqrt_ratio_x96 is None
        or liquidity is None
        or amount_a is None
        or amount_b is None
        or not math.isfinite(sqrt_ratio_x96)
        or not math.isfinite(liquidity)
        or not math.isfinite(amount_a)
        or not math.isfinite(amount_b)
        or sqrt_ratio_x96 <= 0
        or liquidity <= 0
    ):
        return None

    post_sqrt = sqrt_ratio_x96 / Q96
    if not math.isfinite(post_sqrt) or post_sqrt <= 0:
        return None

    try:
        start_sqrt_from_amount0 = 1.0 / ((1.0 / post_sqrt) - (amount_a / liquidity))
    except ZeroDivisionError:
        start_sqrt_from_amount0 = math.nan
    start_sqrt_from_amount1 = post_sqrt - (amount_b / liquidity)

    if side == 'buy':
        chosen_start_sqrt = start_sqrt_from_amount1
    elif side == 'sell':
        chosen_start_sqrt = start_sqrt_from_amount0
    else:
        raise ValueError(f'Unsupported side: {side}')

    if not math.isfinite(chosen_start_sqrt) or chosen_start_sqrt <= 0:
        return None

    return AmmPoolSpotReference(
        pre_trade_spot_price=100.0 / (chosen_start_sqrt * chosen_start_sqrt),
        post_trade_spot_price=100.0 / (post_sqrt * post_sqrt),
    )

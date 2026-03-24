from __future__ import annotations


def infer_side(amount_base_in: float, amount_base_out: float) -> str:
    if amount_base_in > 0 and amount_base_out == 0:
        return 'sell'
    if amount_base_out > 0 and amount_base_in == 0:
        return 'buy'
    raise ValueError('Could not infer side from event amounts')

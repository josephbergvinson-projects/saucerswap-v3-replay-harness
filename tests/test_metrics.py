import math
import unittest

from saucerswap_v3_replay.metrics.core import (
    Q96,
    completion_ratio,
    reconstruct_amm_pre_trade_spot_reference,
    slippage_bps,
    symmetric_reference_denominator_bps,
)


class MetricsTests(unittest.TestCase):
    def test_completion_ratio(self):
        self.assertEqual(completion_ratio(5, 10), 0.5)

    def test_buy_slippage(self):
        self.assertAlmostEqual(slippage_bps(100, 101, 'buy'), 100.0)

    def test_zero_execution_sell_slippage_is_infinite(self):
        self.assertTrue(math.isinf(slippage_bps(100, 0, 'sell')))

    def test_symmetric_reference_denominator_slippage_uses_reference_for_both_sides(self):
        self.assertAlmostEqual(symmetric_reference_denominator_bps(100, 101, 'buy'), 100.0)
        self.assertAlmostEqual(symmetric_reference_denominator_bps(100, 99, 'sell'), 100.0)

    def test_reconstruct_amm_pre_trade_spot_reference_uses_output_side_delta(self):
        buy_reference = reconstruct_amm_pre_trade_spot_reference(
            side='buy',
            sqrt_ratio_x96=2 * Q96,
            liquidity=1.0,
            amount_a=0.1,
            amount_b=-0.5,
        )
        sell_reference = reconstruct_amm_pre_trade_spot_reference(
            side='sell',
            sqrt_ratio_x96=2 * Q96,
            liquidity=1.0,
            amount_a=-0.1,
            amount_b=0.5,
        )

        self.assertIsNotNone(buy_reference)
        self.assertIsNotNone(sell_reference)
        self.assertAlmostEqual(buy_reference.post_trade_spot_price, 25.0)
        self.assertAlmostEqual(buy_reference.pre_trade_spot_price, 16.0)
        self.assertAlmostEqual(sell_reference.post_trade_spot_price, 25.0)
        self.assertAlmostEqual(sell_reference.pre_trade_spot_price, 36.0, places=10)


if __name__ == '__main__':
    unittest.main()

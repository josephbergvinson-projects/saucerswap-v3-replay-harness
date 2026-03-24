import math
import unittest

from saucerswap_v3_replay.metrics.core import completion_ratio, slippage_bps


class MetricsTests(unittest.TestCase):
    def test_completion_ratio(self):
        self.assertEqual(completion_ratio(5, 10), 0.5)

    def test_buy_slippage(self):
        self.assertAlmostEqual(slippage_bps(100, 101, 'buy'), 100.0)

    def test_zero_execution_sell_slippage_is_infinite(self):
        self.assertTrue(math.isinf(slippage_bps(100, 0, 'sell')))


if __name__ == '__main__':
    unittest.main()

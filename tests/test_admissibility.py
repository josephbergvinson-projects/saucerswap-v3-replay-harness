import unittest

from saucerswap_v3_replay.rules.admissibility import passes_limit_price, passes_slippage_cap


class AdmissibilityTests(unittest.TestCase):
    def test_buy_limit_price(self):
        self.assertTrue(passes_limit_price('buy', execution_price=99, limit_price=100))
        self.assertFalse(passes_limit_price('buy', execution_price=101, limit_price=100))

    def test_sell_limit_price(self):
        self.assertTrue(passes_limit_price('sell', execution_price=101, limit_price=100))
        self.assertFalse(passes_limit_price('sell', execution_price=99, limit_price=100))

    def test_slippage_cap(self):
        self.assertTrue(passes_slippage_cap('buy', 100.0, 100.3, 50))
        self.assertFalse(passes_slippage_cap('buy', 100.0, 101.0, 50))


if __name__ == '__main__':
    unittest.main()

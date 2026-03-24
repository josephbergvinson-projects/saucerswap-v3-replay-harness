import unittest

from saucerswap_v3_replay.backstop.v2_residual import ResidualQuote
from saucerswap_v3_replay.schema import ReplayUnit
from saucerswap_v3_replay.sim.book_profile import allocate_depth
from saucerswap_v3_replay.sim.hybrid import simulate_hybrid


class HybridTests(unittest.TestCase):
    def test_hybrid_routes_when_admissible(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 20.0, 2000.0, 100.0)
        quote = ResidualQuote(execution_price=100.3, available_size=20.0)
        record = simulate_hybrid(unit, levels, quote, max_slippage_bps=50)
        self.assertGreater(record.filled_size, 10.0)
        self.assertTrue(record.admissibility_passed)

    def test_hybrid_does_not_route_when_not_admissible(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 20.0, 2000.0, 100.0)
        quote = ResidualQuote(execution_price=110.0, available_size=20.0)
        record = simulate_hybrid(unit, levels, quote, max_slippage_bps=50)
        self.assertFalse(record.admissibility_passed)
        self.assertNotIn('v2_backstop', record.route_breakdown)


if __name__ == '__main__':
    unittest.main()

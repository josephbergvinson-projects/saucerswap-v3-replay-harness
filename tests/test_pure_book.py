import unittest

from saucerswap_v3_replay.schema import ReplayUnit
from saucerswap_v3_replay.sim.book_profile import allocate_depth
from saucerswap_v3_replay.sim.pure_book import simulate_pure_book


class PureBookTests(unittest.TestCase):
    def test_partial_fill_when_requested_notional_exceeds_depth(self):
        levels = allocate_depth(1000.0, [(2, 1), (4, 1)])
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 20.0, 2000.0, 100.0)
        record = simulate_pure_book(unit, levels)
        self.assertLess(record.completion_ratio, 1.0)
        self.assertGreater(record.remainder_size, 0.0)


if __name__ == '__main__':
    unittest.main()

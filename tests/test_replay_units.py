import unittest

from saucerswap_v3_replay.normalize.replay_units import collapse_by_tx_side
from saucerswap_v3_replay.schema import ReplayUnit


class ReplayUnitCollapseTests(unittest.TestCase):
    def test_collapse_by_tx_side(self):
        units = [
            ReplayUnit('a', 't', 'tx', 1, 'buy', 1.0, 100.0, 100.0),
            ReplayUnit('b', 't', 'tx', 2, 'buy', 2.0, 200.0, 100.0),
        ]
        collapsed = collapse_by_tx_side(units)
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0].requested_size, 3.0)
        self.assertEqual(collapsed[0].requested_notional, 300.0)


if __name__ == '__main__':
    unittest.main()

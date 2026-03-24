import unittest

from saucerswap_v3_replay.baseline.v2_realized import build_v2_realized_record
from saucerswap_v3_replay.schema import ReplayUnit


class V2RealizedTests(unittest.TestCase):
    def test_v2_record_is_full_fill(self):
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 10.0, 1000.0, 100.0)
        record = build_v2_realized_record(unit, execution_price=101.0)
        self.assertEqual(record.filled_size, 10.0)
        self.assertEqual(record.completion_ratio, 1.0)
        self.assertEqual(record.route_breakdown['v2'], 10.0)


if __name__ == '__main__':
    unittest.main()

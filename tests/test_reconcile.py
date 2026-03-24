import unittest

from saucerswap_v3_replay.validation.reconcile import reconcile_totals


class ReconcileTests(unittest.TestCase):
    def test_reconcile_match(self):
        out = reconcile_totals(10, 10)
        self.assertTrue(out['counts_match'])


if __name__ == '__main__':
    unittest.main()

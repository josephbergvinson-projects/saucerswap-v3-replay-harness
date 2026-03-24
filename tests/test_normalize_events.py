import unittest

from saucerswap_v3_replay.normalize.events import infer_side


class InferSideTests(unittest.TestCase):
    def test_buy(self):
        self.assertEqual(infer_side(0, 10), 'buy')

    def test_sell(self):
        self.assertEqual(infer_side(10, 0), 'sell')

    def test_invalid(self):
        with self.assertRaises(ValueError):
            infer_side(1, 1)


if __name__ == '__main__':
    unittest.main()

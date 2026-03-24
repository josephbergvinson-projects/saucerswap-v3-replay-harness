import unittest

from saucerswap_v3_replay.normalize.events import normalize_trade_row, normalize_side
from saucerswap_v3_replay.normalize.prices import ReferencePriceIndex, normalize_raw_reference_price


class SideResolutionTests(unittest.TestCase):
    def test_uses_explicit_trade_type_when_present(self):
        self.assertEqual(normalize_side('BUY', amount_b=123), 'buy')
        self.assertEqual(normalize_side('sell', amount_b=-123), 'sell')

    def test_falls_back_to_amount_b_sign_when_type_missing(self):
        self.assertEqual(normalize_side('', amount_b=-1), 'buy')
        self.assertEqual(normalize_side(None, amount_b=1), 'sell')

    def test_invalid_side_raises(self):
        with self.assertRaises(ValueError):
            normalize_side('', amount_b=0)


class NormalizeTradeRowTests(unittest.TestCase):
    def test_requested_notional_is_quote_side_and_size_is_hbar_side(self):
        event = normalize_trade_row(
            {
                'tradeRowId': '36',
                'swapEventId': '36',
                'tradeTimestampSeconds': '1,700,264,033',
                'baseId': 'USDC',
                'targetId': 'HBAR',
                'baseVolume': '1,000,000,000',
                'targetVolume': '1,636,287,625,575',
                'type': 'buy',
                'amountB': '-1,636,287,625,575',
            },
            reference_price=0.0612,
            reference_price_source='at_or_before',
            reference_price_fallback=False,
            swap_metadata_covered=True,
            fee_covered=False,
        )
        self.assertEqual(event.side, 'buy')
        self.assertAlmostEqual(event.requested_notional, 1000.0)
        self.assertAlmostEqual(event.requested_size, 16362.87625575)
        self.assertAlmostEqual(event.observed_execution_price, 1000.0 / 16362.87625575)


class ReferencePriceIndexTests(unittest.TestCase):
    def test_normalizes_raw_price_to_usdc_per_hbar(self):
        self.assertAlmostEqual(normalize_raw_reference_price(16.44), 1 / 16.44)

    def test_prefers_latest_earlier_reference_price(self):
        index = ReferencePriceIndex(
            timestamps=[1_700_239_200, 1_700_239_260, 1_700_239_320],
            reference_prices=[0.0610, 0.0611, 0.0612],
        )
        match = index.lookup(1_700_239_299)
        self.assertEqual(match.source, 'at_or_before')
        self.assertFalse(match.fallback)
        self.assertEqual(match.source_timestamp_seconds, 1_700_239_260)
        self.assertAlmostEqual(match.reference_price, 0.0611)

    def test_falls_back_to_nearest_later_price_when_needed(self):
        index = ReferencePriceIndex(
            timestamps=[1_700_239_200, 1_700_239_260],
            reference_prices=[0.0610, 0.0611],
        )
        match = index.lookup(1_700_239_100)
        self.assertEqual(match.source, 'nearest_later')
        self.assertTrue(match.fallback)
        self.assertEqual(match.source_timestamp_seconds, 1_700_239_200)
        self.assertAlmostEqual(match.reference_price, 0.0610)


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import json
import unittest

from saucerswap_v3_replay.reporting.provider_economics_views import (
    adverse_reference_move_usd,
    lp_lvr_loss_proxy_from_row,
    maker_markout_loss_proxy_from_row,
    provider_economics_observation_from_row,
    roll_up_provider_economics_observations,
)


class ProviderEconomicsViewTests(unittest.TestCase):
    def test_adverse_reference_move_is_side_aware_and_adverse_only(self) -> None:
        self.assertEqual(
            adverse_reference_move_usd(
                side='buy',
                current_reference_price=100.0,
                next_reference_price=102.0,
                filled_size=5.0,
            ),
            10.0,
        )
        self.assertEqual(
            adverse_reference_move_usd(
                side='buy',
                current_reference_price=100.0,
                next_reference_price=99.0,
                filled_size=5.0,
            ),
            0.0,
        )
        self.assertEqual(
            adverse_reference_move_usd(
                side='sell',
                current_reference_price=100.0,
                next_reference_price=98.0,
                filled_size=5.0,
            ),
            10.0,
        )
        self.assertEqual(
            adverse_reference_move_usd(
                side='sell',
                current_reference_price=100.0,
                next_reference_price=101.0,
                filled_size=5.0,
            ),
            0.0,
        )

    def test_lp_lvr_loss_proxy_for_v2_buy_row_uses_execution_to_next_reference(self) -> None:
        row = {
            'lane': 'v2_realized',
            'side': 'buy',
            'filled_size': '100',
            'filled_notional': '10100',
        }

        self.assertEqual(lp_lvr_loss_proxy_from_row(row, next_reference_price=102.0), 100.0)
        self.assertEqual(lp_lvr_loss_proxy_from_row(row, next_reference_price=100.5), 0.0)
        self.assertEqual(lp_lvr_loss_proxy_from_row(row, next_reference_price=None), 0.0)

    def test_lp_lvr_loss_proxy_for_v2_sell_row_is_adverse_only(self) -> None:
        row = {
            'lane': 'v2_realized',
            'side': 'sell',
            'filled_size': '100',
            'filled_notional': '9900',
        }

        self.assertEqual(lp_lvr_loss_proxy_from_row(row, next_reference_price=98.0), 100.0)
        self.assertEqual(lp_lvr_loss_proxy_from_row(row, next_reference_price=100.0), 0.0)

    def test_maker_markout_loss_proxy_for_3a_uses_reference_move_only(self) -> None:
        row = {
            'lane': '3a_pure_book',
            'side': 'buy',
            'reference_price': '100',
            'filled_size': '50',
            'filled_notional': '5050',
        }

        self.assertEqual(maker_markout_loss_proxy_from_row(row, next_reference_price=102.0), 100.0)
        self.assertEqual(maker_markout_loss_proxy_from_row(row, next_reference_price=99.0), 0.0)
        self.assertEqual(maker_markout_loss_proxy_from_row(row, next_reference_price=None), 0.0)

    def test_maker_markout_loss_proxy_for_3b_uses_pure_book_leg_only(self) -> None:
        row = {
            'lane': '3b_hybrid',
            'side': 'buy',
            'reference_price': '100',
            'filled_size': '250',
            'filled_notional': '25100',
            'route_breakdown': json.dumps({'pure_book': 200.0, 'v2_backstop': 50.0}, sort_keys=True),
            'fee_route_breakdown': json.dumps(
                {
                    'pure_book': {
                        'filled_size': 200.0,
                        'filled_notional_usd': 20100.0,
                    },
                    'v2_backstop': {
                        'filled_size': 50.0,
                        'filled_notional_usd': 5000.0,
                    },
                },
                sort_keys=True,
            ),
        }

        self.assertEqual(maker_markout_loss_proxy_from_row(row, next_reference_price=101.0), 200.0)
        self.assertNotEqual(maker_markout_loss_proxy_from_row(row, next_reference_price=101.0), 250.0)

    def test_provider_econ_rollup_combines_v2_and_v3_layers_symmetrically(self) -> None:
        v2_row = {
            'lane': 'v2_realized',
            'side': 'buy',
            'requested_notional': '10000',
            'baseVolumeRaw': '10000000000',
            'filled_size': '100',
            'filled_notional': '10000',
            'active_lp_fee_earned_usd': '30',
        }
        hybrid_row = {
            'lane': '3b_hybrid',
            'side': 'sell',
            'requested_notional': '12000',
            'baseVolumeRaw': '12000000000',
            'reference_price': '100',
            'filled_size': '150',
            'filled_notional': '15120',
            'maker_rebate_earned_usd': '6',
            'route_breakdown': json.dumps({'pure_book': 100.0, 'v2_backstop': 50.0}, sort_keys=True),
            'fee_route_breakdown': json.dumps(
                {
                    'pure_book': {
                        'filled_size': 100.0,
                        'filled_notional_usd': 10080.0,
                    },
                    'v2_backstop': {
                        'filled_size': 50.0,
                        'filled_notional_usd': 5040.0,
                    },
                },
                sort_keys=True,
            ),
        }

        observations = [
            provider_economics_observation_from_row(v2_row, next_reference_price=101.0),
            provider_economics_observation_from_row(hybrid_row, next_reference_price=99.0),
        ]
        aggregate, by_side, by_bucket = roll_up_provider_economics_observations(
            observations,
            bucket_label=lambda observation: 'large' if observation.requested_notional >= 10000.0 else 'small',
        )

        self.assertEqual(aggregate.row_count, 2)
        self.assertEqual(aggregate.next_event_horizon_supported_rows, 2)
        self.assertEqual(aggregate.next_event_horizon_unavailable_rows, 0)
        self.assertEqual(aggregate.lp_fee_accrual_total, 30.0)
        self.assertEqual(aggregate.lp_divergence_loss_proxy_total, 100.0)
        self.assertEqual(aggregate.lp_net_provider_economics_proxy_total, -70.0)
        self.assertEqual(aggregate.maker_rebate_total, 6.0)
        self.assertEqual(aggregate.gross_spread_capture_total, -80.0)
        self.assertEqual(aggregate.maker_markout_loss_proxy_total, 100.0)
        self.assertEqual(aggregate.maker_net_provider_economics_proxy_total, -174.0)
        self.assertEqual(aggregate.explicit_protocol_transfer_total, 36.0)
        self.assertEqual(aggregate.gross_provider_revenue_proxy_total, -44.0)
        self.assertEqual(aggregate.net_provider_economics_proxy_total, -244.0)
        self.assertEqual(by_side['buy'].lp_net_provider_economics_proxy_total, -70.0)
        self.assertEqual(by_side['sell'].maker_net_provider_economics_proxy_total, -174.0)
        self.assertEqual(by_bucket['large'].row_count, 2)


if __name__ == '__main__':
    unittest.main()

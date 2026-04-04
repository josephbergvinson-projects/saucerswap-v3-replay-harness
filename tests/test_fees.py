import unittest
from pathlib import Path

from saucerswap_v3_replay.fees import (
    build_hybrid_fee_fields,
    build_v2_fee_fields,
    build_v3_fee_fields,
    load_fee_policy,
    scenario_totals_from_breakdown,
)


class FeePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fee_policy = load_fee_policy(Path('config/fees.yaml'))

    def test_load_fee_policy_parses_nested_yaml_without_pyyaml(self) -> None:
        self.assertEqual(self.fee_policy['v2_whbar_usdc']['trader_fee_bps'], 15.0)
        self.assertEqual(self.fee_policy['v3_whbar_usdc']['min_order_size_usdc'], 1.0)
        self.assertEqual(
            self.fee_policy['v3_whbar_usdc']['scenarios']['tier2_10pct']['effective_taker_fee_bps'],
            10.8,
        )

    def test_v2_fee_fields_follow_locked_split(self) -> None:
        fields = build_v2_fee_fields(
            self.fee_policy,
            filled_size=10.0,
            filled_notional=1000.0,
        )
        self.assertEqual(fields['fee_scenario_id'], 'v2_fixed')
        self.assertAlmostEqual(fields['trader_fee_paid_usd'], 1.5)
        self.assertAlmostEqual(fields['active_lp_fee_earned_usd'], 1.25)
        self.assertAlmostEqual(fields['protocol_fee_earned_usd'], 0.25)
        self.assertAlmostEqual(fields['maker_rebate_earned_usd'], 0.0)

    def test_v3_fee_fields_preserve_all_locked_scenarios(self) -> None:
        fields = build_v3_fee_fields(
            self.fee_policy,
            requested_notional=1000.0,
            filled_size=10.0,
            filled_notional=1000.0,
        )
        self.assertEqual(fields['fee_scenario_id'], 'no_xsauce')
        self.assertAlmostEqual(fields['trader_fee_paid_usd'], 1.2)
        self.assertAlmostEqual(fields['maker_rebate_earned_usd'], 0.02)
        self.assertAlmostEqual(fields['protocol_fee_earned_usd'], 1.18)
        scenario_totals = scenario_totals_from_breakdown(fields['fee_route_breakdown'])
        self.assertAlmostEqual(scenario_totals['tier2_10pct']['trader_fee_paid_usd'], 1.08)
        self.assertAlmostEqual(scenario_totals['tier2_10pct']['maker_rebate_earned_usd'], 0.018)
        self.assertAlmostEqual(scenario_totals['tier2_10pct']['protocol_fee_earned_usd'], 1.062)

    def test_hybrid_fee_fields_blend_v3_and_v2_routes(self) -> None:
        fields = build_hybrid_fee_fields(
            self.fee_policy,
            requested_notional=1000.0,
            pure_book_filled_size=6.0,
            pure_book_filled_notional=600.0,
            v2_backstop_filled_size=4.0,
            v2_backstop_execution_price=101.0,
        )
        self.assertAlmostEqual(fields['fee_basis_filled_notional_usd'], 1004.0)
        self.assertAlmostEqual(fields['trader_fee_paid_usd'], 0.72 + 0.606)
        self.assertAlmostEqual(fields['maker_rebate_earned_usd'], 0.012)
        self.assertAlmostEqual(fields['active_lp_fee_earned_usd'], 0.505)
        self.assertAlmostEqual(fields['protocol_fee_earned_usd'], 0.708 + 0.101)
        scenario_totals = scenario_totals_from_breakdown(fields['fee_route_breakdown'])
        self.assertAlmostEqual(scenario_totals['tier2_10pct']['trader_fee_paid_usd'], 0.648 + 0.606)


if __name__ == '__main__':
    unittest.main()

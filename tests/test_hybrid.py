import csv
import json
import tempfile
import unittest
from pathlib import Path

from saucerswap_v3_replay.backstop.v2_residual import ResidualQuote
from saucerswap_v3_replay.fees import load_fee_policy
from saucerswap_v3_replay.schema import ReplayUnit
from saucerswap_v3_replay.sim.book_profile import allocate_depth
from saucerswap_v3_replay.sim.hybrid import run_hybrid_lane, simulate_hybrid


class HybridSimulationTests(unittest.TestCase):
    def test_hybrid_routes_residual_when_admissible(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 20.0, 2000.0, 100.0)
        quote = ResidualQuote(execution_price=100.3, available_size=20.0)
        fee_policy = load_fee_policy(Path('config/fees.yaml'))

        record = simulate_hybrid(unit, levels, quote, max_slippage_bps=50, fee_policy=fee_policy)

        self.assertGreater(record.filled_size, 10.0)
        self.assertTrue(record.admissibility_passed)
        self.assertIn('v2_backstop', record.route_breakdown)

    def test_hybrid_routes_only_available_residual_size(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u2', 't', 'tx', 2, 'buy', 20.0, 2000.0, 100.0)
        quote = ResidualQuote(execution_price=100.2, available_size=3.0)
        fee_policy = load_fee_policy(Path('config/fees.yaml'))

        record = simulate_hybrid(unit, levels, quote, max_slippage_bps=50, fee_policy=fee_policy)

        self.assertTrue(record.admissibility_passed)
        self.assertAlmostEqual(record.route_breakdown['v2_backstop'], 3.0)
        self.assertGreater(record.remainder_size, 0.0)
        self.assertLess(record.completion_ratio, 1.0)

    def test_hybrid_routes_when_blended_execution_passes_even_if_quote_alone_does_not(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u3', 't', 'tx', 3, 'buy', 20.0, 2000.0, 100.0)
        quote = ResidualQuote(execution_price=100.8, available_size=20.0)
        fee_policy = load_fee_policy(Path('config/fees.yaml'))

        record = simulate_hybrid(unit, levels, quote, max_slippage_bps=50, fee_policy=fee_policy)

        self.assertTrue(record.admissibility_passed)
        self.assertIn('v2_backstop', record.route_breakdown)
        self.assertGreater(record.completion_ratio, 0.99)

    def test_hybrid_does_not_route_when_not_admissible_or_quote_missing(self):
        levels = allocate_depth(1000.0, [(2, 1)])
        unit = ReplayUnit('u4', 't', 'tx', 4, 'buy', 20.0, 2000.0, 100.0)
        bad_quote = ResidualQuote(execution_price=101.0, available_size=20.0)
        fee_policy = load_fee_policy(Path('config/fees.yaml'))

        rejected = simulate_hybrid(unit, levels, bad_quote, max_slippage_bps=50, fee_policy=fee_policy)
        missing = simulate_hybrid(unit, levels, None, max_slippage_bps=50, fee_policy=fee_policy)

        self.assertFalse(rejected.admissibility_passed)
        self.assertNotIn('v2_backstop', rejected.route_breakdown)
        self.assertFalse(missing.admissibility_passed)
        self.assertNotIn('v2_backstop', missing.route_breakdown)


class HybridPipelineTests(unittest.TestCase):
    def test_run_hybrid_lane_materializes_outputs_and_rollups_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            processed_dir = root / 'data' / 'processed'
            config_dir = root / 'config'
            processed_dir.mkdir(parents=True)
            config_dir.mkdir()

            self._write_text(
                config_dir / 'hybrid_rule.yaml',
                '\n'.join(
                    [
                        'hybrid_rule:',
                        '  mode: "slippage_cap_bps"',
                        '  reference_price_basis: "replay_unit_reference_price"',
                        '  quote_requirement: "recoverable_v2_residual_quote_required"',
                        '  max_buy_slippage_bps: 50',
                        '  max_sell_slippage_bps: 50',
                        '  require_backstop_quote: true',
                        '  failure_policy: "leave_residual_unfilled"',
                        '  notes: "toy test rule"',
                        '',
                    ]
                ),
            )
            self._write_text(
                config_dir / 'fees.yaml',
                Path('config/fees.yaml').read_text(encoding='utf-8'),
            )

            pure_rows = [
                self._pure_book_row(
                    replay_unit_id='swap:10:trade:1',
                    trade_row_id='1',
                    swap_event_id='10',
                    trade_timestamp_seconds='1700000000',
                    source_ordering_key='1700000000:00000000000000000010:00000000000000000001',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='5',
                    filled_notional='500.1',
                    completion_ratio='0.5',
                    reference_price='100',
                    avg_execution_price='100.02',
                    remainder_size='5',
                    route_breakdown=json.dumps({'pure_book': 5.0}),
                ),
                self._pure_book_row(
                    replay_unit_id='swap:20:trade:2',
                    trade_row_id='2',
                    swap_event_id='20',
                    trade_timestamp_seconds='1700000060',
                    source_ordering_key='1700000060:00000000000000000020:00000000000000000002',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='6',
                    filled_notional='600.12',
                    completion_ratio='0.6',
                    reference_price='100',
                    avg_execution_price='100.02',
                    remainder_size='4',
                    route_breakdown=json.dumps({'pure_book': 6.0}),
                ),
                self._pure_book_row(
                    replay_unit_id='swap:30:trade:3',
                    trade_row_id='3',
                    swap_event_id='30',
                    trade_timestamp_seconds='1700000120',
                    source_ordering_key='1700000120:00000000000000000030:00000000000000000003',
                    side='sell',
                    requested_size='8',
                    requested_notional='800',
                    filled_size='8',
                    filled_notional='799.68',
                    completion_ratio='1',
                    reference_price='100',
                    avg_execution_price='99.96',
                    remainder_size='0',
                    route_breakdown=json.dumps({'pure_book': 8.0}),
                ),
                self._pure_book_row(
                    replay_unit_id='swap:40:trade:4',
                    trade_row_id='4',
                    swap_event_id='40',
                    trade_timestamp_seconds='1700000180',
                    source_ordering_key='1700000180:00000000000000000040:00000000000000000004',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='8',
                    filled_notional='800.16',
                    completion_ratio='0.8',
                    reference_price='100',
                    avg_execution_price='100.02',
                    remainder_size='2',
                    route_breakdown=json.dumps({'pure_book': 8.0}),
                ),
            ]
            baseline_rows = [
                self._baseline_row(
                    replay_unit_id='swap:10:trade:1',
                    trade_row_id='1',
                    swap_event_id='10',
                    trade_timestamp_seconds='1700000000',
                    source_ordering_key='1700000000:00000000000000000010:00000000000000000001',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='2',
                    filled_notional='200.6',
                    reference_price='100',
                    avg_execution_price='100.3',
                    route_breakdown=json.dumps({'v2': 2.0}),
                ),
                self._baseline_row(
                    replay_unit_id='swap:20:trade:2',
                    trade_row_id='2',
                    swap_event_id='20',
                    trade_timestamp_seconds='1700000060',
                    source_ordering_key='1700000060:00000000000000000020:00000000000000000002',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='10',
                    filled_notional='1010',
                    reference_price='100',
                    avg_execution_price='101',
                    route_breakdown=json.dumps({'v2': 10.0}),
                ),
                self._baseline_row(
                    replay_unit_id='swap:30:trade:3',
                    trade_row_id='3',
                    swap_event_id='30',
                    trade_timestamp_seconds='1700000120',
                    source_ordering_key='1700000120:00000000000000000030:00000000000000000003',
                    side='sell',
                    requested_size='8',
                    requested_notional='800',
                    filled_size='8',
                    filled_notional='800.8',
                    reference_price='100',
                    avg_execution_price='100.1',
                    route_breakdown=json.dumps({'v2': 8.0}),
                ),
                self._baseline_row(
                    replay_unit_id='swap:40:trade:4',
                    trade_row_id='4',
                    swap_event_id='40',
                    trade_timestamp_seconds='1700000180',
                    source_ordering_key='1700000180:00000000000000000040:00000000000000000004',
                    side='buy',
                    requested_size='10',
                    requested_notional='1000',
                    filled_size='10',
                    filled_notional='1001',
                    reference_price='100',
                    avg_execution_price='100.1',
                    route_breakdown=json.dumps({'v2': 10.0}),
                ),
            ]

            self._write_csv(processed_dir / 'lane_3a_pure_book.csv', pure_rows)
            self._write_csv(processed_dir / 'lane_v2_baseline.csv', baseline_rows)

            first_result = run_hybrid_lane(root)
            second_result = run_hybrid_lane(root)

            first_lane_rows = self._read_csv(first_result.lane_output_path)
            second_lane_rows = self._read_csv(second_result.lane_output_path)
            summary = json.loads(first_result.summary_path.read_text())
            manifest = json.loads(first_result.manifest_path.read_text())
            second_summary = json.loads(second_result.summary_path.read_text())

            self.assertEqual(first_lane_rows, second_lane_rows)
            self.assertEqual(summary['mapping']['fingerprint'], second_summary['mapping']['fingerprint'])
            self.assertEqual(len(first_lane_rows), 4)

            routed_limited = first_lane_rows[0]
            routed_blended = first_lane_rows[1]
            no_residual = first_lane_rows[2]
            routed_full = first_lane_rows[3]

            self.assertEqual(routed_limited['replay_unit_id'], 'swap:10:trade:1')
            self.assertEqual(routed_limited['tradeRowId'], '1')
            self.assertEqual(routed_limited['swapEventId'], '10')
            self.assertEqual(
                routed_limited['source_ordering_key'],
                '1700000000:00000000000000000010:00000000000000000001',
            )
            self.assertEqual(routed_limited['admissibility_passed'], 'true')
            self.assertEqual(json.loads(routed_limited['route_breakdown']), {'pure_book': 5.0, 'v2_backstop': 2.0})
            self.assertEqual(routed_limited['completion_ratio'], '0.7')
            self.assertEqual(routed_limited['remainder_size'], '3')
            self.assertEqual(routed_limited['amm_pre_trade_spot_reference_price'], '100')
            self.assertNotEqual(routed_limited['amm_pre_trade_spot_gross_slippage_bps'], '')

            self.assertEqual(routed_blended['admissibility_passed'], 'true')
            self.assertEqual(
                json.loads(routed_blended['route_breakdown']),
                {'pure_book': 6.0, 'v2_backstop': 4.0},
            )
            self.assertEqual(routed_blended['completion_ratio'], '1')
            self.assertEqual(routed_blended['remainder_size'], '0')

            self.assertEqual(no_residual['admissibility_passed'], '')
            self.assertEqual(json.loads(no_residual['route_breakdown']), {'pure_book': 8.0})
            self.assertEqual(no_residual['completion_ratio'], '1')
            self.assertEqual(no_residual['remainder_size'], '0')

            self.assertEqual(routed_full['admissibility_passed'], 'true')
            self.assertEqual(json.loads(routed_full['route_breakdown']), {'pure_book': 8.0, 'v2_backstop': 2.0})
            self.assertEqual(routed_full['completion_ratio'], '1')
            self.assertEqual(routed_full['remainder_size'], '0')
            self.assertEqual(routed_full['fee_precision'], 'route_aware_modeled_from_locked_v2_v3_schedules')
            self.assertEqual(routed_full['fee_scenario_id'], 'no_xsauce')
            self.assertNotEqual(routed_full['fee_route_breakdown'], '')

            self.assertEqual(summary['row_counts']['hybrid_rows'], 4)
            self.assertEqual(summary['row_counts']['buy_rows'], 3)
            self.assertEqual(summary['row_counts']['sell_rows'], 1)
            self.assertEqual(summary['completion']['full_fill_rows'], 3)
            self.assertEqual(summary['completion']['partial_fill_rows'], 1)
            self.assertEqual(summary['completion']['zero_fill_rows'], 0)
            self.assertEqual(summary['completion']['hybrid_full_fill_from_backstop_rows'], 2)
            self.assertEqual(summary['admissibility']['rows_with_residual'], 3)
            self.assertEqual(summary['admissibility']['rows_without_residual'], 1)
            self.assertEqual(summary['admissibility']['backstop_quote_recovered_rows'], 3)
            self.assertEqual(summary['admissibility']['backstop_quote_missing_rows'], 0)
            self.assertEqual(summary['admissibility']['pass_rows'], 3)
            self.assertEqual(summary['admissibility']['fail_rows'], 0)
            self.assertAlmostEqual(summary['admissibility']['pass_rate_on_residual_rows'], 1.0)
            self.assertEqual(summary['route_breakdown']['routed_rows'], 3)
            self.assertEqual(summary['route_breakdown']['pure_book_only_rows'], 1)
            self.assertEqual(summary['route_breakdown']['unrouted_residual_rows'], 0)
            self.assertEqual(summary['route_breakdown']['available_size_limited_rows'], 1)
            self.assertEqual(summary['route_breakdown']['v2_backstop_size_hbar'], '8')
            self.assertEqual(summary['fees']['fee_missing_rows'], 4)
            self.assertEqual(summary['fees']['precise_fee_rows'], 4)
            self.assertEqual(summary['fees']['default_scenario_id'], 'no_xsauce')
            self.assertTrue(summary['fees']['recipient_reconciliation_pass'])
            self.assertGreater(float(summary['fees']['default_rollup']['trader_fee_paid_usd']), 0.0)
            self.assertGreater(
                summary['fees']['default_rollup']['trader_fee_paid_bps_on_filled_notional'],
                summary['fees']['scenario_rollups']['tier2_10pct']['trader_fee_paid_bps_on_filled_notional'],
            )
            self.assertEqual(summary['amm_pre_trade_spot_gross_slippage_bps']['supported_rows'], 4)
            self.assertEqual(summary['coverage']['amm_pre_trade_spot_reference_supported_rows'], 4)
            self.assertTrue(summary['mapping']['fingerprint'])
            self.assertTrue(summary['mapping']['one_to_one_mapping_verified'])
            self.assertTrue(summary['reconciliation']['counts_match'])
            self.assertTrue(summary['reconciliation']['input_alignment_verified'])
            self.assertTrue(summary['reconciliation']['filled_plus_remainder_matches_requested_size'])
            self.assertTrue(summary['reconciliation']['no_overfill_rows'])

            self.assertEqual(manifest['mapping']['row_count'], 4)
            self.assertTrue(manifest['mapping']['one_to_one_mapping_verified'])
            self.assertEqual(manifest['route_breakdown']['routed_rows'], 3)
            self.assertEqual(manifest['admissibility']['fail_rows'], 0)
            self.assertTrue(
                any('projected hybrid average execution price' in caveat for caveat in manifest['caveats'])
            )
            self.assertTrue(
                any('recoverable quote size was smaller than the pure-book residual' in caveat for caveat in manifest['caveats'])
            )
            self.assertTrue(
                any('mounted RH-05 pure-book lane' in caveat for caveat in manifest['caveats'])
            )

    @staticmethod
    def _pure_book_row(**overrides: str) -> dict[str, str]:
        row = {
            'lane': '3a_pure_book',
            'replay_unit_id': 'swap:0:trade:0',
            'timestamp': '2023-11-14T22:13:20Z',
            'side': 'buy',
            'requested_size': '10',
            'requested_notional': '1000',
            'filled_size': '10',
            'filled_notional': '1000',
            'completion_ratio': '1',
            'reference_price': '100',
            'amm_pre_trade_spot_reference_price': '100',
            'avg_execution_price': '100',
            'execution_slippage_bps': '0',
            'amm_pre_trade_spot_gross_slippage_bps': '0',
            'fees_paid': '0',
            'fee_methodology': 'pure-book test',
            'fee_precision': 'no_synthetic_fee_model',
            'fee_covered': 'false',
            'remainder_size': '0',
            'route_breakdown': json.dumps({'pure_book': 10.0}),
            'admissibility_passed': '',
            'tradeRowId': '0',
            'swapEventId': '0',
            'tradeTimestampSeconds': '1700000000',
            'source_ordering_key': '1700000000:00000000000000000000:00000000000000000000',
            'baseId': 'USDC',
            'targetId': 'HBAR',
            'baseVolumeRaw': '1000000000',
            'targetVolumeRaw': '1000000000',
            'reference_price_source': 'at_or_before',
            'reference_price_fallback': 'false',
            'swap_metadata_covered': 'false',
        }
        renamed = {
            'trade_row_id': 'tradeRowId',
            'swap_event_id': 'swapEventId',
            'trade_timestamp_seconds': 'tradeTimestampSeconds',
        }
        for key, replacement in renamed.items():
            if key in overrides:
                overrides[replacement] = overrides.pop(key)
        row.update(overrides)
        return row

    @staticmethod
    def _baseline_row(**overrides: str) -> dict[str, str]:
        row = {
            'lane': 'v2_realized',
            'replay_unit_id': 'swap:0:trade:0',
            'timestamp': '2023-11-14T22:13:20Z',
            'side': 'buy',
            'requested_size': '10',
            'requested_notional': '1000',
            'filled_size': '10',
            'filled_notional': '1000',
            'completion_ratio': '1',
            'reference_price': '100',
            'amm_pre_trade_spot_reference_price': '100',
            'avg_execution_price': '100',
            'realized_slippage_bps': '0',
            'amm_pre_trade_spot_gross_slippage_bps': '0',
            'fees_paid': '0',
            'fee_methodology': 'baseline test',
            'fee_precision': 'not_allocated_per_replay_unit',
            'fee_covered': 'false',
            'remainder_size': '0',
            'route_breakdown': json.dumps({'v2': 10.0}),
            'admissibility_passed': 'true',
            'tradeRowId': '0',
            'swapEventId': '0',
            'tradeTimestampSeconds': '1700000000',
            'source_ordering_key': '1700000000:00000000000000000000:00000000000000000000',
            'baseId': 'USDC',
            'targetId': 'HBAR',
            'baseVolumeRaw': '1000000000',
            'targetVolumeRaw': '1000000000',
            'reference_price_source': 'at_or_before',
            'reference_price_fallback': 'false',
            'swap_metadata_covered': 'false',
        }
        renamed = {
            'trade_row_id': 'tradeRowId',
            'swap_event_id': 'swapEventId',
            'trade_timestamp_seconds': 'tradeTimestampSeconds',
        }
        for key, replacement in renamed.items():
            if key in overrides:
                overrides[replacement] = overrides.pop(key)
        row.update(overrides)
        return row

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding='utf-8')

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open('r', encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))


if __name__ == '__main__':
    unittest.main()

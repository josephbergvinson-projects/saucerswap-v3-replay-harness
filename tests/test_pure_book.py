import csv
import json
import tempfile
import unittest
from pathlib import Path

from saucerswap_v3_replay.baseline.v2_realized import observed_event_context_from_row
from saucerswap_v3_replay.schema import ReplayUnit
from saucerswap_v3_replay.sim.book_profile import allocate_depth
from saucerswap_v3_replay.sim.pure_book import (
    build_pure_book_row,
    run_pure_book_lane,
    simulate_pure_book,
    walk_replenishing_book,
)


class PureBookSimulationTests(unittest.TestCase):
    def test_walk_replenishing_book_partial_fill_is_size_based_and_deterministic(self):
        levels = allocate_depth(1000.0, [(2.0, 1.0)])
        unit = ReplayUnit('u1', 't', 'tx', 1, 'buy', 20.0, 2000.0, 100.0)

        fill = walk_replenishing_book(unit, levels)

        expected_filled_size = 1000.0 / 100.02
        self.assertAlmostEqual(fill.filled_size, expected_filled_size)
        self.assertAlmostEqual(fill.filled_notional, 1000.0)
        self.assertAlmostEqual(fill.avg_execution_price, 100.02)
        self.assertAlmostEqual(fill.remainder_size, 20.0 - expected_filled_size)

        record = simulate_pure_book(unit, levels)
        self.assertAlmostEqual(record.completion_ratio, expected_filled_size / 20.0)
        self.assertAlmostEqual(record.filled_notional, 1000.0)
        self.assertLessEqual(record.filled_size, unit.requested_size)
        self.assertEqual(record.route_breakdown['pure_book'], record.filled_size)

    def test_build_pure_book_row_computes_weighted_execution_price_and_slippage_vs_reference(self):
        levels = allocate_depth(2000.0, [(2.0, 1.0), (4.0, 1.0)])
        unit = ReplayUnit(
            replay_unit_id='u2',
            timestamp='2026-03-24T00:00:00Z',
            tx_id='20',
            event_index=2,
            side='buy',
            requested_size=15.0,
            requested_notional=1500.0,
            reference_price=100.0,
            trade_row_id=2,
            swap_event_id='20',
            trade_timestamp_seconds=1700000060,
        )
        context = observed_event_context_from_row(
            {
                'replay_unit_id': 'u2',
                'source_ordering_key': '1700000060:00000000000000000020:00000000000000000002',
                'observed_execution_price': '100.1',
                'baseId': 'USDC',
                'targetId': 'HBAR',
                'baseVolumeRaw': '1500000000',
                'targetVolumeRaw': '1500000000',
                'tradeRowId': '2',
                'swapEventId': '20',
                'tradeTimestampSeconds': '1700000060',
                'reference_price_source': 'at_or_before',
                'reference_price_fallback': 'false',
                'swap_metadata_covered': 'true',
                'fee_covered': 'false',
            }
        )

        row = build_pure_book_row(unit, context, levels)

        first_level_size = 1000.0 / 100.02
        second_level_size = 15.0 - first_level_size
        expected_notional = 1000.0 + (second_level_size * 100.04)
        expected_avg_execution_price = expected_notional / 15.0
        expected_slippage_bps = ((expected_avg_execution_price / 100.0) - 1.0) * 10_000

        self.assertAlmostEqual(row.record.filled_size, 15.0)
        self.assertAlmostEqual(row.record.filled_notional, expected_notional)
        self.assertAlmostEqual(row.record.avg_execution_price, expected_avg_execution_price)
        self.assertAlmostEqual(row.execution_slippage_bps, expected_slippage_bps)


class PureBookPipelineTests(unittest.TestCase):
    def test_run_pure_book_lane_materializes_outputs_and_mapping_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            interim_dir = root / 'data' / 'interim'
            interim_dir.mkdir(parents=True)
            (root / 'data' / 'processed').mkdir(parents=True)
            (root / 'config').mkdir()

            self._write_text(
                root / 'config' / 'lambdaplex_book.yaml',
                '\n'.join(
                    [
                        'pure_book:',
                        '  total_depth_usd: 1000',
                        '  levels:',
                        '    - { spread_bps: 2, weight: 1 }',
                        '  replenish_per_replay_unit: true',
                        '',
                    ]
                ),
            )
            self._write_text(
                root / 'config' / 'fees.yaml',
                '\n'.join(
                    [
                        'fees:',
                        '  include_fees_in_headline: true',
                        '  headline_metric_basis: "requested_notional"',
                        '  filled_only_metrics: "supplemental_only"',
                        '  source_fee_treatment: "historical_when_available"',
                        '  missing_fee_policy: "flag_and_continue"',
                        '  impute_missing_fees: false',
                        '',
                    ]
                ),
            )

            self._write_csv(
                interim_dir / 'replay_units.csv',
                [
                    {
                        'replay_unit_id': 'swap:10:trade:1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'tx_id': '10',
                        'event_index': '1',
                        'side': 'buy',
                        'requested_size': '20',
                        'requested_notional': '1',
                        'reference_price': '100',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'true',
                    }
                ],
            )
            self._write_csv(
                interim_dir / 'normalized_events.csv',
                [
                    {
                        'replay_unit_id': 'swap:10:trade:1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'source_ordering_key': '1700000000:00000000000000000010:00000000000000000001',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'side': 'buy',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolumeRaw': '1000000',
                        'targetVolumeRaw': '2000000000',
                        'requested_size': '20',
                        'requested_notional': '1',
                        'observed_execution_price': '100.01',
                        'reference_price': '100',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'true',
                    },
                    {
                        'replay_unit_id': 'swap:20:trade:2',
                        'timestamp': '2023-11-14T22:14:20Z',
                        'source_ordering_key': '1700000060:00000000000000000020:00000000000000000002',
                        'tradeRowId': '2',
                        'swapEventId': '20',
                        'tradeTimestampSeconds': '1700000060',
                        'side': 'sell',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolumeRaw': '500000',
                        'targetVolumeRaw': '500000000',
                        'requested_size': '5',
                        'requested_notional': '0.5',
                        'observed_execution_price': '99.99',
                        'reference_price': '100',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'false',
                        'fee_covered': 'false',
                    },
                ],
            )

            first_result = run_pure_book_lane(root)
            second_result = run_pure_book_lane(root)

            first_lane_rows = self._read_csv(first_result.lane_output_path)
            second_lane_rows = self._read_csv(second_result.lane_output_path)
            summary = json.loads(first_result.summary_path.read_text())
            manifest = json.loads(first_result.manifest_path.read_text())
            second_summary = json.loads(second_result.summary_path.read_text())

            self.assertEqual(first_lane_rows, second_lane_rows)
            self.assertEqual(summary['mapping']['fingerprint'], second_summary['mapping']['fingerprint'])
            self.assertEqual(len(first_lane_rows), 2)

            self.assertEqual(first_lane_rows[0]['replay_unit_id'], 'swap:10:trade:1')
            self.assertEqual(first_lane_rows[0]['tradeRowId'], '1')
            self.assertEqual(first_lane_rows[0]['swapEventId'], '10')
            self.assertEqual(
                first_lane_rows[0]['source_ordering_key'],
                '1700000000:00000000000000000010:00000000000000000001',
            )
            self.assertEqual(first_lane_rows[0]['fee_precision'], 'no_synthetic_fee_model')
            self.assertLess(float(first_lane_rows[0]['completion_ratio']), 1.0)
            self.assertGreater(float(first_lane_rows[0]['remainder_size']), 0.0)
            self.assertEqual(first_lane_rows[1]['completion_ratio'], '1')

            self.assertEqual(summary['row_counts']['pure_book_rows'], 2)
            self.assertEqual(summary['row_counts']['normalized_event_rows'], 2)
            self.assertEqual(summary['row_counts']['replay_projection_verified_rows'], 1)
            self.assertEqual(summary['row_counts']['replay_projection_missing_tail_rows'], 1)
            self.assertEqual(summary['row_counts']['buy_rows'], 1)
            self.assertEqual(summary['row_counts']['sell_rows'], 1)
            self.assertEqual(summary['completion']['full_fill_rows'], 1)
            self.assertEqual(summary['completion']['partial_fill_rows'], 1)
            self.assertEqual(summary['completion']['zero_fill_rows'], 0)
            self.assertTrue(summary['reconciliation']['counts_match'])
            self.assertTrue(summary['reconciliation']['filled_plus_remainder_matches_requested_size'])
            self.assertTrue(summary['reconciliation']['no_overfill_rows'])
            self.assertTrue(summary['book']['replenish_per_replay_unit'])
            self.assertEqual(summary['fees']['fee_covered_rows'], 1)
            self.assertEqual(summary['fees']['fee_missing_rows'], 1)
            self.assertEqual(summary['slippage_bps']['finite_rows'], 2)
            self.assertEqual(summary['slippage_bps']['excluded_zero_fill_rows'], 0)
            self.assertTrue(summary['mapping']['fingerprint'])
            self.assertFalse(summary['mapping']['replay_projection_complete'])

            self.assertEqual(manifest['mapping']['row_count'], 2)
            self.assertTrue(manifest['mapping']['one_to_one_mapping_verified'])
            self.assertEqual(manifest['row_counts']['pure_book_rows'], 2)
            self.assertTrue(any('does not force completion to 1.0' in caveat for caveat in manifest['caveats']))
            self.assertTrue(any('missing tail replay-unit records directly' in caveat for caveat in manifest['caveats']))

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

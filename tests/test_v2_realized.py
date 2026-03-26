import csv
import json
import tempfile
import unittest
from pathlib import Path

from saucerswap_v3_replay.baseline.v2_realized import (
    ReplayUnitMappingError,
    build_baseline_row,
    build_v2_realized_record,
    iter_aligned_event_rows,
    observed_event_context_from_row,
    run_v2_realized_baseline,
)
from saucerswap_v3_replay.schema import ReplayUnit


class V2RealizedRecordTests(unittest.TestCase):
    def test_v2_record_is_full_fill_and_preserves_requested_notional(self):
        unit = ReplayUnit(
            replay_unit_id='u1',
            timestamp='2026-03-24T00:00:00Z',
            tx_id='10',
            event_index=1,
            side='buy',
            requested_size=3.0,
            requested_notional=1.0,
            reference_price=0.333333333333,
            trade_row_id=1,
            swap_event_id='10',
            trade_timestamp_seconds=1700000000,
        )
        record = build_v2_realized_record(unit, execution_price=0.333333333333)
        self.assertEqual(record.filled_size, 3.0)
        self.assertEqual(record.filled_notional, 1.0)
        self.assertEqual(record.completion_ratio, 1.0)
        self.assertEqual(record.route_breakdown['v2'], 3.0)
        self.assertEqual(record.remainder_size, 0.0)

    def test_build_baseline_row_computes_reference_price_slippage_for_sell_side(self):
        unit = ReplayUnit(
            replay_unit_id='u2',
            timestamp='2026-03-24T00:00:00Z',
            tx_id='20',
            event_index=2,
            side='sell',
            requested_size=10.0,
            requested_notional=0.95,
            reference_price=0.10,
            trade_row_id=2,
            swap_event_id='20',
            trade_timestamp_seconds=1700000060,
        )
        context = observed_event_context_from_row(
            {
                'replay_unit_id': 'u2',
                'source_ordering_key': '1700000060:00000000000000000020:00000000000000000002',
                'observed_execution_price': '0.095',
                'baseId': 'USDC',
                'targetId': 'HBAR',
                'baseVolumeRaw': '950000',
                'targetVolumeRaw': '1000000000',
                'tradeRowId': '2',
                'swapEventId': '20',
                'tradeTimestampSeconds': '1700000060',
                'reference_price_source': 'at_or_before',
                'reference_price_fallback': 'false',
                'swap_metadata_covered': 'true',
                'fee_covered': 'false',
            }
        )

        row = build_baseline_row(unit, context)
        self.assertAlmostEqual(row.record.avg_execution_price, 0.095)
        self.assertAlmostEqual(row.realized_slippage_bps, 526.315789473684)
        self.assertEqual(row.record.fees_paid, 0.0)


class V2RealizedMappingTests(unittest.TestCase):
    def test_iter_aligned_event_rows_raises_on_replay_unit_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            replay_path = root / 'replay_units.csv'
            normalized_path = root / 'normalized_events.csv'
            self._write_csv(
                replay_path,
                [
                    {
                        'replay_unit_id': 'u1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'tx_id': '10',
                        'event_index': '1',
                        'side': 'buy',
                        'requested_size': '10',
                        'requested_notional': '160',
                        'reference_price': '16',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'false',
                    }
                ],
            )
            self._write_csv(
                normalized_path,
                [
                    {
                        'replay_unit_id': 'u999',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'source_ordering_key': '1700000000:00000000000000000010:00000000000000000001',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'side': 'buy',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolumeRaw': '1000000',
                        'targetVolumeRaw': '1000000000',
                        'requested_size': '10',
                        'requested_notional': '1',
                        'observed_execution_price': '0.1',
                        'reference_price': '0.1',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'false',
                    }
                ],
            )

            with self.assertRaises(ReplayUnitMappingError):
                list(iter_aligned_event_rows(replay_path, normalized_path))

    def test_iter_aligned_event_rows_allows_missing_replay_projection_tail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            replay_path = root / 'replay_units.csv'
            normalized_path = root / 'normalized_events.csv'
            self._write_csv(
                replay_path,
                [
                    {
                        'replay_unit_id': 'u1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'tx_id': '10',
                        'event_index': '1',
                        'side': 'buy',
                        'requested_size': '10',
                        'requested_notional': '1',
                        'reference_price': '0.1',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'false',
                    }
                ],
            )
            self._write_csv(
                normalized_path,
                [
                    {
                        'replay_unit_id': 'u1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'source_ordering_key': '1700000000:00000000000000000010:00000000000000000001',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'side': 'buy',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolumeRaw': '1000000',
                        'targetVolumeRaw': '1000000000',
                        'requested_size': '10',
                        'requested_notional': '1',
                        'observed_execution_price': '0.1',
                        'reference_price': '0.1',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'false',
                    },
                    {
                        'replay_unit_id': 'u2',
                        'timestamp': '2023-11-14T22:14:20Z',
                        'source_ordering_key': '1700000060:00000000000000000020:00000000000000000002',
                        'tradeRowId': '2',
                        'swapEventId': '20',
                        'tradeTimestampSeconds': '1700000060',
                        'side': 'sell',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolumeRaw': '950000',
                        'targetVolumeRaw': '1000000000',
                        'requested_size': '10',
                        'requested_notional': '0.95',
                        'observed_execution_price': '0.095',
                        'reference_price': '0.1',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'false',
                        'fee_covered': 'false',
                    },
                ],
            )

            rows = list(iter_aligned_event_rows(replay_path, normalized_path))
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0].replay_projection_verified)
            self.assertFalse(rows[1].replay_projection_verified)
            self.assertEqual(rows[1].replay_unit.replay_unit_id, 'u2')

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


class V2RealizedPipelineTests(unittest.TestCase):
    def test_run_v2_realized_baseline_materializes_outputs_and_rollups(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            interim_dir = root / 'data' / 'interim'
            processed_dir = root / 'data' / 'processed'
            interim_dir.mkdir(parents=True)
            processed_dir.mkdir(parents=True)

            self._write_csv(
                interim_dir / 'replay_units.csv',
                [
                    {
                        'replay_unit_id': 'swap:10:trade:1',
                        'timestamp': '2023-11-14T22:13:20Z',
                        'tx_id': '10',
                        'event_index': '1',
                        'side': 'buy',
                        'requested_size': '10',
                        'requested_notional': '160',
                        'reference_price': '16',
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'tradeTimestampSeconds': '1700000000',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'true',
                        'fee_covered': 'true',
                    },
                    {
                        'replay_unit_id': 'swap:20:trade:2',
                        'timestamp': '2023-11-14T22:14:20Z',
                        'tx_id': '20',
                        'event_index': '2',
                        'side': 'sell',
                        'requested_size': '10',
                        'requested_notional': '356.4',
                        'reference_price': '36',
                        'tradeRowId': '2',
                        'swapEventId': '20',
                        'tradeTimestampSeconds': '1700000060',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'false',
                        'fee_covered': 'false',
                    },
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
                        'baseVolumeRaw': '160000000',
                        'targetVolumeRaw': '1000000000',
                        'requested_size': '10',
                        'requested_notional': '160',
                        'observed_execution_price': '16.16',
                        'reference_price': '16',
                        'amountA': '0.1',
                        'amountB': '-0.5',
                        'sqrtRatioX96': '158456325028528675187087900672',
                        'liquidity': '1',
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
                        'baseVolumeRaw': '356400000',
                        'targetVolumeRaw': '1000000000',
                        'requested_size': '10',
                        'requested_notional': '356.4',
                        'observed_execution_price': '35.64',
                        'reference_price': '36',
                        'amountA': '-0.1',
                        'amountB': '0.5',
                        'sqrtRatioX96': '158456325028528675187087900672',
                        'liquidity': '1',
                        'reference_price_source': 'at_or_before',
                        'reference_price_fallback': 'false',
                        'swap_metadata_covered': 'false',
                        'fee_covered': 'false',
                    },
                ],
            )

            result = run_v2_realized_baseline(root)

            lane_rows = self._read_csv(result.lane_output_path)
            summary = json.loads(result.summary_path.read_text())
            manifest = json.loads(result.manifest_path.read_text())

            self.assertEqual(len(lane_rows), 2)
            self.assertEqual(lane_rows[0]['replay_unit_id'], 'swap:10:trade:1')
            self.assertEqual(lane_rows[0]['tradeRowId'], '1')
            self.assertEqual(lane_rows[0]['swapEventId'], '10')
            self.assertEqual(lane_rows[0]['source_ordering_key'], '1700000000:00000000000000000010:00000000000000000001')
            self.assertEqual(lane_rows[0]['completion_ratio'], '1')
            self.assertEqual(lane_rows[0]['realized_slippage_bps'], '100')
            self.assertEqual(lane_rows[0]['amm_pre_trade_spot_reference_price'], '16')
            self.assertEqual(lane_rows[0]['amm_pre_trade_spot_gross_slippage_bps'], '100')
            self.assertEqual(lane_rows[1]['realized_slippage_bps'], '101.010101010102')
            self.assertEqual(lane_rows[1]['amm_pre_trade_spot_reference_price'], '36')
            self.assertAlmostEqual(float(lane_rows[1]['amm_pre_trade_spot_gross_slippage_bps']), 100.0)
            self.assertEqual(lane_rows[0]['fee_precision'], 'not_allocated_per_replay_unit')

            self.assertEqual(summary['row_counts']['baseline_rows'], 2)
            self.assertEqual(summary['row_counts']['normalized_event_rows'], 2)
            self.assertEqual(summary['row_counts']['replay_projection_verified_rows'], 2)
            self.assertEqual(summary['row_counts']['replay_projection_missing_tail_rows'], 0)
            self.assertEqual(summary['completion']['full_fill_rows'], 2)
            self.assertEqual(summary['completion']['avg_completion_ratio'], 1.0)
            self.assertEqual(summary['fees']['precise_fee_rows'], 0)
            self.assertEqual(summary['fees']['fee_covered_rows'], 1)
            self.assertEqual(summary['fees']['fee_missing_rows'], 1)
            self.assertAlmostEqual(summary['amm_pre_trade_spot_gross_slippage_bps']['avg'], 100.0)
            self.assertEqual(summary['amm_pre_trade_spot_gross_slippage_bps']['supported_rows'], 2)
            self.assertEqual(summary['coverage']['amm_pre_trade_spot_reference_supported_rows'], 2)
            self.assertEqual(summary['totals']['requested_size_hbar'], '20')
            self.assertEqual(summary['totals']['requested_notional_usdc'], '516.4')
            self.assertTrue(summary['reconciliation']['counts_match'])
            self.assertTrue(summary['reconciliation']['requested_size_matches_filled_size'])
            self.assertTrue(summary['reconciliation']['requested_notional_matches_filled_notional'])
            self.assertTrue(summary['mapping']['fingerprint'])
            self.assertTrue(summary['mapping']['replay_projection_complete'])

            self.assertEqual(manifest['mapping']['row_count'], 2)
            self.assertTrue(manifest['mapping']['one_to_one_mapping_verified'])
            self.assertTrue(manifest['mapping']['replay_projection_complete'])
            self.assertEqual(manifest['row_counts']['baseline_rows'], 2)
            self.assertTrue(any('fees_paid to 0.0' in caveat for caveat in manifest['caveats']))

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open('r', encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))


if __name__ == '__main__':
    unittest.main()

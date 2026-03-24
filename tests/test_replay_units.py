import csv
import json
import tempfile
import unittest
from pathlib import Path

from saucerswap_v3_replay.normalize.pipeline import run_normalization
from saucerswap_v3_replay.normalize.replay_units import collapse_by_tx_side, materialize_replay_units
from saucerswap_v3_replay.schema import ReplayUnit


class ReplayUnitOrderingTests(unittest.TestCase):
    def test_materialize_replay_units_uses_canonical_event_order(self):
        units = [
            ReplayUnit(
                'u3',
                't3',
                '12',
                300,
                'buy',
                1.0,
                100.0,
                0.06,
                trade_row_id=300,
                swap_event_id='12',
                trade_timestamp_seconds=1700000001,
            ),
            ReplayUnit(
                'u1',
                't1',
                '10',
                100,
                'buy',
                1.0,
                100.0,
                0.06,
                trade_row_id=100,
                swap_event_id='10',
                trade_timestamp_seconds=1700000000,
            ),
            ReplayUnit(
                'u2',
                't2',
                '11',
                200,
                'sell',
                1.0,
                100.0,
                0.06,
                trade_row_id=200,
                swap_event_id='11',
                trade_timestamp_seconds=1700000000,
            ),
        ]
        ordered = materialize_replay_units(units)
        self.assertEqual([unit.replay_unit_id for unit in ordered], ['u1', 'u2', 'u3'])

    def test_compatibility_shim_no_longer_collapses_rows(self):
        units = [
            ReplayUnit(
                'u1',
                't1',
                '10',
                100,
                'buy',
                1.0,
                100.0,
                0.06,
                trade_row_id=100,
                swap_event_id='10',
                trade_timestamp_seconds=1700000000,
            ),
            ReplayUnit(
                'u2',
                't2',
                '10',
                101,
                'buy',
                2.0,
                200.0,
                0.06,
                trade_row_id=101,
                swap_event_id='10',
                trade_timestamp_seconds=1700000000,
            ),
        ]
        preserved = collapse_by_tx_side(units)
        self.assertEqual(len(preserved), 2)
        self.assertEqual([unit.trade_row_id for unit in preserved], [100, 101])


class NormalizationPipelineTests(unittest.TestCase):
    def test_one_trade_row_maps_to_one_replay_unit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = root / 'data' / 'raw' / 'gigabrain'
            raw_dir.mkdir(parents=True)
            (root / 'data' / 'interim').mkdir(parents=True)

            self._write_csv(
                raw_dir / 'hbar_usdc_v2_015_trades.csv',
                [
                    {
                        'tradeRowId': '1',
                        'swapEventId': '10',
                        'poolContractId': '0.0.3964804',
                        'tradeTimestampSeconds': '1,700,000,000',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolume': '1,000,000',
                        'targetVolume': '20,000,000,000',
                        'price': '20',
                        'type': 'buy',
                        'contractId': '0.0.3964804',
                        'sender': 'a',
                        'recipient': 'b',
                        'amountA': '1,000,000',
                        'amountB': '-20,000,000,000',
                        'sqrtRatioX96': '1',
                        'liquidity': '1',
                        'tick': '1',
                        'swapEventTimestampSeconds': '1,700,000,000.00',
                        'swapSource': '',
                    },
                    {
                        'tradeRowId': '2',
                        'swapEventId': '11',
                        'poolContractId': '0.0.3964804',
                        'tradeTimestampSeconds': '1,700,000,060',
                        'baseId': 'USDC',
                        'targetId': 'HBAR',
                        'baseVolume': '500,000',
                        'targetVolume': '10,000,000,000',
                        'price': '20',
                        'type': '',
                        'contractId': '0.0.3964804',
                        'sender': 'a',
                        'recipient': 'b',
                        'amountA': '-500,000',
                        'amountB': '10,000,000,000',
                        'sqrtRatioX96': '1',
                        'liquidity': '1',
                        'tick': '1',
                        'swapEventTimestampSeconds': '1,700,000,060.00',
                        'swapSource': '',
                    },
                ],
            )
            self._write_csv(
                raw_dir / 'hbar_usdc_v2_015_swap_metadata.csv',
                [
                    {
                        'metadataRowId': '1',
                        'swap_id': '10',
                        'source': 'meta',
                        'contractId': '0.0.3964804',
                        'timestampSeconds': '1,700,000,000',
                        'sender': 'a',
                        'recipient': 'b',
                        'amountA': '1,000,000',
                        'amountB': '-20,000,000,000',
                        'sqrtRatioX96': '1',
                        'liquidity': '1',
                        'tick': '1',
                    },
                ],
            )
            self._write_csv(
                raw_dir / 'hbar_reference_prices.csv',
                [
                    {'id': '1', 'poolId': '9', 'timestampSeconds': '1,699,999,940', 'price': '20'},
                    {'id': '2', 'poolId': '9', 'timestampSeconds': '1,700,000,060', 'price': '25'},
                ],
            )
            self._write_csv(
                raw_dir / 'v2_fee_inputs.csv',
                [
                    {
                        'id': '1',
                        'poolVersion': '2',
                        'poolId': '9',
                        'timestampSeconds': '1,699,977,600',
                        'fee': '1',
                        'feeUsd': '1',
                        'feeSaucerswapUi': '',
                        'feeSaucerswapUiUsd': '',
                        'feeSaucerswapApp': '',
                        'feeSaucerswapAppUsd': '',
                        'feeHashpack': '',
                        'feeHashpackUsd': '',
                        'feeKabilia': '',
                        'feeKabiliaUsd': '',
                        'feeBlade': '',
                        'feeBladeUsd': '',
                        'feeEtaSwap': '',
                        'feeEtaSwapUsd': '',
                        'feeSaucerswapAppAndroid': '0',
                        'feeSaucerswapAppAndroidUsd': '0',
                    },
                ],
            )

            result = run_normalization(root)

            normalized_rows = self._read_csv(result.normalized_events_path)
            replay_rows = self._read_csv(result.replay_units_path)
            manifest = json.loads(result.manifest_path.read_text())

            self.assertEqual(len(normalized_rows), 2)
            self.assertEqual(len(replay_rows), 2)
            self.assertEqual(manifest['row_counts']['raw_trade_rows'], 2)
            self.assertEqual(manifest['row_counts']['replay_unit_rows'], 2)
            self.assertTrue(manifest['reconciliation']['counts_match'])
            self.assertEqual(normalized_rows[0]['tradeRowId'], '1')
            self.assertEqual(normalized_rows[1]['tradeRowId'], '2')
            self.assertEqual(replay_rows[0]['tx_id'], '10')
            self.assertEqual(replay_rows[1]['tx_id'], '11')
            self.assertEqual(normalized_rows[1]['side'], 'sell')
            self.assertEqual(normalized_rows[0]['reference_price_source'], 'at_or_before')
            self.assertEqual(normalized_rows[0]['swap_metadata_covered'], 'true')
            self.assertEqual(normalized_rows[1]['swap_metadata_covered'], 'false')
            self.assertEqual(normalized_rows[0]['fee_covered'], 'true')

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

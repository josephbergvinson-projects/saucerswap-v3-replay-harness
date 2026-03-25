import csv
import json
from pathlib import Path
import tempfile
import unittest

from saucerswap_v3_replay.metrics.summaries import LaneObservation, roll_up_observations
from saucerswap_v3_replay.normalize.events import format_decimal, format_scaled_int
from saucerswap_v3_replay.reporting.pack import assign_bucket, load_bucket_config, run_reporting_pack


class ReportingPackTests(unittest.TestCase):
    def test_roll_up_observations_tracks_lane_summary_metrics(self) -> None:
        observations = [
            LaneObservation(
                lane='3b_hybrid',
                side='buy',
                requested_size=10.0,
                requested_notional=5.0,
                requested_size_raw=1_000_000_000,
                requested_notional_raw=5_000_000,
                filled_size=10.0,
                filled_notional=5.1,
                completion_ratio=1.0,
                remainder_size=0.0,
                slippage_bps=2.0,
                fee_covered=False,
                admissibility_passed=None,
            ),
            LaneObservation(
                lane='3b_hybrid',
                side='sell',
                requested_size=20.0,
                requested_notional=10.0,
                requested_size_raw=2_000_000_000,
                requested_notional_raw=10_000_000,
                filled_size=15.0,
                filled_notional=7.5,
                completion_ratio=0.75,
                remainder_size=5.0,
                slippage_bps=-1.0,
                fee_covered=True,
                admissibility_passed=False,
            ),
        ]

        aggregate, by_side, by_bucket = roll_up_observations(
            observations,
            bucket_label=lambda _: 'toy',
        )

        self.assertEqual(aggregate.row_count, 2)
        self.assertEqual(aggregate.full_fill_rows, 1)
        self.assertEqual(aggregate.partial_fill_rows, 1)
        self.assertEqual(aggregate.zero_fill_rows, 0)
        self.assertEqual(aggregate.fee_covered_rows, 1)
        self.assertEqual(aggregate.fee_missing_rows, 1)
        self.assertEqual(aggregate.admissibility_pass_rows, 0)
        self.assertEqual(aggregate.admissibility_fail_rows, 1)
        self.assertEqual(aggregate.admissibility_unknown_rows, 1)
        self.assertAlmostEqual(aggregate.fill_rate, 0.833333333333)
        self.assertAlmostEqual(aggregate.avg_completion_ratio, 0.875)
        self.assertAlmostEqual(aggregate.avg_slippage_bps, 0.5)
        self.assertEqual(by_side['buy'].row_count, 1)
        self.assertEqual(by_side['sell'].row_count, 1)
        self.assertEqual(by_bucket['toy'].row_count, 2)

    def test_assign_bucket_uses_repo_bucket_edges(self) -> None:
        bucket_config = load_bucket_config(Path('config/buckets.yaml'))

        self.assertEqual(assign_bucket(bucket_config, 0.0), '<1k')
        self.assertEqual(assign_bucket(bucket_config, 999.999999), '<1k')
        self.assertEqual(assign_bucket(bucket_config, 1000.0), '1k-5k')
        self.assertEqual(assign_bucket(bucket_config, 5000.0), '5k-10k')
        self.assertEqual(assign_bucket(bucket_config, 25_000.0), '25k+')

    def test_reporting_pack_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_reporting_fixture(root)

            first = run_reporting_pack(root)
            first_outputs = {
                'aggregate': first.comparison_aggregate_path.read_text(encoding='utf-8'),
                'bucket': first.comparison_by_bucket_path.read_text(encoding='utf-8'),
                'side': first.comparison_by_side_path.read_text(encoding='utf-8'),
                'final_report': first.final_comparison_path.read_text(encoding='utf-8'),
                'reconciliation': first.reconciliation_path.read_text(encoding='utf-8'),
                'validation': first.validation_path.read_text(encoding='utf-8'),
            }

            second = run_reporting_pack(root)
            second_outputs = {
                'aggregate': second.comparison_aggregate_path.read_text(encoding='utf-8'),
                'bucket': second.comparison_by_bucket_path.read_text(encoding='utf-8'),
                'side': second.comparison_by_side_path.read_text(encoding='utf-8'),
                'final_report': second.final_comparison_path.read_text(encoding='utf-8'),
                'reconciliation': second.reconciliation_path.read_text(encoding='utf-8'),
                'validation': second.validation_path.read_text(encoding='utf-8'),
            }

            self.assertEqual(first_outputs, second_outputs)

    def test_reporting_pack_materializes_side_bucket_and_benchmark_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_reporting_fixture(root)

            result = run_reporting_pack(root)

            side_rows = self._read_csv(result.comparison_by_side_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['row_count'] for row in side_rows},
                {
                    ('buy', 'v2_realized'): '2',
                    ('buy', '3a_pure_book'): '2',
                    ('buy', '3b_hybrid'): '2',
                    ('sell', 'v2_realized'): '1',
                    ('sell', '3a_pure_book'): '1',
                    ('sell', '3b_hybrid'): '1',
                },
            )

            bucket_rows = self._read_csv(result.comparison_by_bucket_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['row_count'] for row in bucket_rows},
                {
                    ('<1k', 'v2_realized'): '1',
                    ('<1k', '3a_pure_book'): '1',
                    ('<1k', '3b_hybrid'): '1',
                    ('1k-5k', 'v2_realized'): '1',
                    ('1k-5k', '3a_pure_book'): '1',
                    ('1k-5k', '3b_hybrid'): '1',
                    ('25k+', 'v2_realized'): '1',
                    ('25k+', '3a_pure_book'): '1',
                    ('25k+', '3b_hybrid'): '1',
                },
            )

            aggregate_rows = self._read_csv(result.comparison_aggregate_path)
            benchmark_row = next(row for row in aggregate_rows if row['lane'] == 'lambdaplex_published')
            self.assertEqual(benchmark_row['data_status'], 'placeholder')
            self.assertEqual(benchmark_row['row_count'], '')
            self.assertEqual(benchmark_row['avg_slippage_bps'], '')
            self.assertIn('placeholder', benchmark_row['notes'])

            validation = json.loads(result.summary_path.read_text(encoding='utf-8'))
            self.assertEqual(
                [row['status'] for row in validation['validation']['lanes']],
                ['pass', 'pass', 'pass'],
            )

    def _write_reporting_fixture(self, root: Path) -> None:
        processed_dir = root / 'data' / 'processed'
        config_dir = root / 'config'
        benchmark_dir = root / 'benchmarks' / 'lambdaplex'
        reports_dir = root / 'reports'
        processed_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        (config_dir / 'reporting.yaml').write_text(
            '\n'.join(
                [
                    'reporting:',
                    '  include_side_split: true',
                    '  include_bucket_split: true',
                    '  include_validation_summary: true',
                    '  figure_dir: "reports/figures"',
                    '',
                ]
            ),
            encoding='utf-8',
        )
        (config_dir / 'buckets.yaml').write_text(
            '\n'.join(
                [
                    'bucket_edge_semantics: "lower_inclusive_upper_exclusive_except_last"',
                    'bucket_basis: "requested_notional"',
                    'requested_notional_buckets:',
                    '  - { label: "<1k", min: 0, max: 1000 }',
                    '  - { label: "1k-5k", min: 1000, max: 5000 }',
                    '  - { label: "5k-10k", min: 5000, max: 10000 }',
                    '  - { label: "10k-25k", min: 10000, max: 25000 }',
                    '  - { label: "25k+", min: 25000, max: null }',
                    '',
                ]
            ),
            encoding='utf-8',
        )
        (benchmark_dir / 'published-results.json').write_text(
            json.dumps(
                {
                    'source': 'Lambdaplex published benchmark panel',
                    'market': 'HBAR/USDC',
                    'status': 'placeholder',
                    'headline_metrics': {},
                    'notes': 'Populate from published Lambdaplex outputs before final comparison runs.',
                },
                indent=2,
            )
            + '\n',
            encoding='utf-8',
        )

        baseline_rows = [
            self._lane_row(
                lane='v2_realized',
                replay_unit_id='swap:1:trade:1',
                timestamp='2024-01-01T00:00:00Z',
                side='buy',
                requested_size='1000',
                requested_notional='500',
                filled_size='1000',
                filled_notional='500',
                completion_ratio='1',
                reference_price='0.5',
                avg_execution_price='0.5005',
                slippage_field='realized_slippage_bps',
                slippage_value='10',
                fee_covered='false',
                remainder_size='0',
                admissibility_passed='true',
                trade_row_id='1',
                swap_event_id='1',
                trade_timestamp_seconds='1704067200',
                source_ordering_key='1704067200:1:1',
                base_volume_raw='500000000',
                target_volume_raw='100000000000',
            ),
            self._lane_row(
                lane='v2_realized',
                replay_unit_id='swap:2:trade:2',
                timestamp='2024-01-01T00:01:00Z',
                side='sell',
                requested_size='2000',
                requested_notional='1000',
                filled_size='2000',
                filled_notional='1000',
                completion_ratio='1',
                reference_price='0.5',
                avg_execution_price='0.49975',
                slippage_field='realized_slippage_bps',
                slippage_value='5',
                fee_covered='true',
                remainder_size='0',
                admissibility_passed='true',
                trade_row_id='2',
                swap_event_id='2',
                trade_timestamp_seconds='1704067260',
                source_ordering_key='1704067260:2:2',
                base_volume_raw='1000000000',
                target_volume_raw='200000000000',
            ),
            self._lane_row(
                lane='v2_realized',
                replay_unit_id='swap:3:trade:3',
                timestamp='2024-01-01T00:02:00Z',
                side='buy',
                requested_size='40000',
                requested_notional='25000',
                filled_size='40000',
                filled_notional='25000',
                completion_ratio='1',
                reference_price='0.625',
                avg_execution_price='0.625625',
                slippage_field='realized_slippage_bps',
                slippage_value='10',
                fee_covered='true',
                remainder_size='0',
                admissibility_passed='true',
                trade_row_id='3',
                swap_event_id='3',
                trade_timestamp_seconds='1704067320',
                source_ordering_key='1704067320:3:3',
                base_volume_raw='25000000000',
                target_volume_raw='4000000000000',
            ),
        ]

        pure_book_rows = [
            self._lane_row(
                lane='3a_pure_book',
                replay_unit_id='swap:1:trade:1',
                timestamp='2024-01-01T00:00:00Z',
                side='buy',
                requested_size='1000',
                requested_notional='500',
                filled_size='1000',
                filled_notional='499',
                completion_ratio='1',
                reference_price='0.5',
                avg_execution_price='0.499',
                slippage_field='execution_slippage_bps',
                slippage_value='2',
                fee_covered='false',
                remainder_size='0',
                admissibility_passed='',
                trade_row_id='1',
                swap_event_id='1',
                trade_timestamp_seconds='1704067200',
                source_ordering_key='1704067200:1:1',
                base_volume_raw='500000000',
                target_volume_raw='100000000000',
            ),
            self._lane_row(
                lane='3a_pure_book',
                replay_unit_id='swap:2:trade:2',
                timestamp='2024-01-01T00:01:00Z',
                side='sell',
                requested_size='2000',
                requested_notional='1000',
                filled_size='1500',
                filled_notional='752',
                completion_ratio='0.75',
                reference_price='0.5',
                avg_execution_price='0.501333333333',
                slippage_field='execution_slippage_bps',
                slippage_value='4',
                fee_covered='true',
                remainder_size='500',
                admissibility_passed='',
                trade_row_id='2',
                swap_event_id='2',
                trade_timestamp_seconds='1704067260',
                source_ordering_key='1704067260:2:2',
                base_volume_raw='1000000000',
                target_volume_raw='200000000000',
            ),
            self._lane_row(
                lane='3a_pure_book',
                replay_unit_id='swap:3:trade:3',
                timestamp='2024-01-01T00:02:00Z',
                side='buy',
                requested_size='40000',
                requested_notional='25000',
                filled_size='20000',
                filled_notional='12550',
                completion_ratio='0.5',
                reference_price='0.625',
                avg_execution_price='0.6275',
                slippage_field='execution_slippage_bps',
                slippage_value='20',
                fee_covered='true',
                remainder_size='20000',
                admissibility_passed='',
                trade_row_id='3',
                swap_event_id='3',
                trade_timestamp_seconds='1704067320',
                source_ordering_key='1704067320:3:3',
                base_volume_raw='25000000000',
                target_volume_raw='4000000000000',
            ),
        ]

        hybrid_rows = [
            self._lane_row(
                lane='3b_hybrid',
                replay_unit_id='swap:1:trade:1',
                timestamp='2024-01-01T00:00:00Z',
                side='buy',
                requested_size='1000',
                requested_notional='500',
                filled_size='1000',
                filled_notional='499',
                completion_ratio='1',
                reference_price='0.5',
                avg_execution_price='0.499',
                slippage_field='execution_slippage_bps',
                slippage_value='2',
                fee_covered='false',
                remainder_size='0',
                admissibility_passed='',
                trade_row_id='1',
                swap_event_id='1',
                trade_timestamp_seconds='1704067200',
                source_ordering_key='1704067200:1:1',
                base_volume_raw='500000000',
                target_volume_raw='100000000000',
            ),
            self._lane_row(
                lane='3b_hybrid',
                replay_unit_id='swap:2:trade:2',
                timestamp='2024-01-01T00:01:00Z',
                side='sell',
                requested_size='2000',
                requested_notional='1000',
                filled_size='2000',
                filled_notional='1002',
                completion_ratio='1',
                reference_price='0.5',
                avg_execution_price='0.501',
                slippage_field='execution_slippage_bps',
                slippage_value='3',
                fee_covered='true',
                remainder_size='0',
                admissibility_passed='true',
                trade_row_id='2',
                swap_event_id='2',
                trade_timestamp_seconds='1704067260',
                source_ordering_key='1704067260:2:2',
                base_volume_raw='1000000000',
                target_volume_raw='200000000000',
            ),
            self._lane_row(
                lane='3b_hybrid',
                replay_unit_id='swap:3:trade:3',
                timestamp='2024-01-01T00:02:00Z',
                side='buy',
                requested_size='40000',
                requested_notional='25000',
                filled_size='25000',
                filled_notional='15600',
                completion_ratio='0.625',
                reference_price='0.625',
                avg_execution_price='0.624',
                slippage_field='execution_slippage_bps',
                slippage_value='15',
                fee_covered='true',
                remainder_size='15000',
                admissibility_passed='false',
                trade_row_id='3',
                swap_event_id='3',
                trade_timestamp_seconds='1704067320',
                source_ordering_key='1704067320:3:3',
                base_volume_raw='25000000000',
                target_volume_raw='4000000000000',
            ),
        ]

        self._write_csv(processed_dir / 'lane_v2_baseline.csv', baseline_rows)
        self._write_csv(processed_dir / 'lane_3a_pure_book.csv', pure_book_rows)
        self._write_csv(processed_dir / 'lane_3b_hybrid.csv', hybrid_rows)

        self._write_json(
            processed_dir / 'v2_baseline_summary.json',
            self._build_summary(
                baseline_rows,
                row_count_key='baseline_rows',
                fee_precision='not_allocated_per_replay_unit',
                include_remainder=False,
                alignment_field='replay_projection_complete',
                alignment_value=True,
                size_checks={
                    'requested_size_matches_filled_size': True,
                    'requested_notional_matches_filled_notional': True,
                },
            ),
        )
        self._write_json(processed_dir / 'v2_baseline_manifest.json', {'lane': 'v2_realized'})
        self._write_json(
            processed_dir / 'pure_book_summary.json',
            self._build_summary(
                pure_book_rows,
                row_count_key='pure_book_rows',
                fee_precision='no_synthetic_fee_model',
                include_remainder=True,
                alignment_field='replay_projection_complete',
                alignment_value=True,
                size_checks={'filled_plus_remainder_matches_requested_size': True},
            ),
        )
        self._write_json(processed_dir / 'pure_book_manifest.json', {'lane': '3a_pure_book'})
        self._write_json(
            processed_dir / 'hybrid_summary.json',
            self._build_summary(
                hybrid_rows,
                row_count_key='hybrid_rows',
                fee_precision='no_synthetic_or_blended_fee_model',
                include_remainder=True,
                alignment_field='input_alignment_verified',
                alignment_value=True,
                size_checks={'filled_plus_remainder_matches_requested_size': True},
            ),
        )
        self._write_json(processed_dir / 'hybrid_manifest.json', {'lane': '3b_hybrid'})

    def _build_summary(
        self,
        rows: list[dict[str, str]],
        *,
        row_count_key: str,
        fee_precision: str,
        include_remainder: bool,
        alignment_field: str,
        alignment_value: bool,
        size_checks: dict[str, bool],
    ) -> dict[str, object]:
        requested_size_raw_total = sum(int(row['targetVolumeRaw']) for row in rows)
        requested_notional_raw_total = sum(int(row['baseVolumeRaw']) for row in rows)
        filled_size_total = sum(float(row['filled_size']) for row in rows)
        filled_notional_total = sum(float(row['filled_notional']) for row in rows)
        remainder_total = sum(float(row['remainder_size']) for row in rows)
        fee_covered_rows = sum(1 for row in rows if row['fee_covered'] == 'true')
        fee_missing_rows = len(rows) - fee_covered_rows
        full_fill_rows = sum(1 for row in rows if float(row['completion_ratio']) >= 1.0)
        zero_fill_rows = sum(1 for row in rows if float(row['filled_size']) <= 0.0)
        partial_fill_rows = len(rows) - full_fill_rows - zero_fill_rows
        completion_ratio_avg = sum(float(row['completion_ratio']) for row in rows) / len(rows)
        slippage_values = [
            float(row.get('realized_slippage_bps', row.get('execution_slippage_bps', '0'))) for row in rows
        ]
        slippage_avg = sum(slippage_values) / len(slippage_values)
        slippage_avg_abs = sum(abs(value) for value in slippage_values) / len(slippage_values)

        totals = {
            'requested_size_hbar': format_scaled_int(requested_size_raw_total, 8),
            'requested_notional_usdc': format_scaled_int(requested_notional_raw_total, 6),
            'filled_size_hbar': format_decimal(filled_size_total),
            'filled_notional_usdc': format_decimal(filled_notional_total),
        }
        if include_remainder:
            totals['remainder_size_hbar'] = format_decimal(remainder_total)

        mapping = {'fingerprint': f'{row_count_key}-fingerprint'}
        reconciliation = {'counts_match': True, **size_checks}
        if alignment_field == 'replay_projection_complete':
            mapping['replay_projection_complete'] = alignment_value
        else:
            reconciliation[alignment_field] = alignment_value

        return {
            'row_counts': {row_count_key: len(rows)},
            'completion': {
                'full_fill_rows': full_fill_rows,
                'partial_fill_rows': partial_fill_rows,
                'zero_fill_rows': zero_fill_rows,
                'avg_completion_ratio': round(completion_ratio_avg, 12),
            },
            'slippage_bps': {
                'avg': round(slippage_avg, 12),
                'avg_abs': round(slippage_avg_abs, 12),
                'finite_rows': len(slippage_values),
                'infinite_rows': 0,
            },
            'totals': totals,
            'fees': {
                'fee_precision': fee_precision,
                'fee_covered_rows': fee_covered_rows,
                'fee_missing_rows': fee_missing_rows,
            },
            'mapping': mapping,
            'reconciliation': reconciliation,
        }

    @staticmethod
    def _lane_row(
        *,
        lane: str,
        replay_unit_id: str,
        timestamp: str,
        side: str,
        requested_size: str,
        requested_notional: str,
        filled_size: str,
        filled_notional: str,
        completion_ratio: str,
        reference_price: str,
        avg_execution_price: str,
        slippage_field: str,
        slippage_value: str,
        fee_covered: str,
        remainder_size: str,
        admissibility_passed: str,
        trade_row_id: str,
        swap_event_id: str,
        trade_timestamp_seconds: str,
        source_ordering_key: str,
        base_volume_raw: str,
        target_volume_raw: str,
    ) -> dict[str, str]:
        row = {
            'lane': lane,
            'replay_unit_id': replay_unit_id,
            'timestamp': timestamp,
            'side': side,
            'requested_size': requested_size,
            'requested_notional': requested_notional,
            'filled_size': filled_size,
            'filled_notional': filled_notional,
            'completion_ratio': completion_ratio,
            'reference_price': reference_price,
            'avg_execution_price': avg_execution_price,
            'fees_paid': '0',
            'fee_methodology': 'test',
            'fee_precision': 'test',
            'fee_covered': fee_covered,
            'remainder_size': remainder_size,
            'route_breakdown': '{}',
            'admissibility_passed': admissibility_passed,
            'tradeRowId': trade_row_id,
            'swapEventId': swap_event_id,
            'tradeTimestampSeconds': trade_timestamp_seconds,
            'source_ordering_key': source_ordering_key,
            'baseId': 'USDC',
            'targetId': 'HBAR',
            'baseVolumeRaw': base_volume_raw,
            'targetVolumeRaw': target_volume_raw,
            'reference_price_source': 'test',
            'reference_price_fallback': 'false',
            'swap_metadata_covered': 'false',
        }
        row[slippage_field] = slippage_value
        return row

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open('r', encoding='utf-8', newline='') as handle:
            return list(csv.DictReader(handle))


if __name__ == '__main__':
    unittest.main()

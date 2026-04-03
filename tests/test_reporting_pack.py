from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from saucerswap_v3_replay.fees import (
    build_hybrid_fee_fields,
    build_v2_fee_fields,
    build_v3_fee_fields,
    load_fee_policy,
    scenario_totals_from_breakdown,
)
from saucerswap_v3_replay.metrics.summaries import LaneObservation, roll_up_observations
from saucerswap_v3_replay.normalize.events import format_decimal, format_scaled_int
from saucerswap_v3_replay.reporting.fee_views import execution_shortfall_usd
from saucerswap_v3_replay.reporting.spread_capture_views import (
    gross_spread_capture_usd,
    spread_capture_observation_from_row,
)
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
                amm_pre_trade_spot_gross_slippage_bps=3.0,
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
                amm_pre_trade_spot_gross_slippage_bps=1.0,
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
        self.assertAlmostEqual(aggregate.avg_amm_pre_trade_spot_gross_slippage_bps, 2.0)
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
                'fee_aggregate': first.fee_comparison_aggregate_path.read_text(encoding='utf-8'),
                'fee_bucket': first.fee_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'fee_side': first.fee_comparison_by_side_path.read_text(encoding='utf-8'),
                'fee_scenarios': first.fee_scenario_comparison_path.read_text(encoding='utf-8'),
                'spread_capture_aggregate': first.spread_capture_comparison_aggregate_path.read_text(encoding='utf-8'),
                'spread_capture_bucket': first.spread_capture_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'spread_capture_side': first.spread_capture_comparison_by_side_path.read_text(encoding='utf-8'),
                'provider_econ_aggregate': first.provider_econ_comparison_aggregate_path.read_text(encoding='utf-8'),
                'provider_econ_bucket': first.provider_econ_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'provider_econ_side': first.provider_econ_comparison_by_side_path.read_text(encoding='utf-8'),
                'final_report': first.final_comparison_path.read_text(encoding='utf-8'),
                'reconciliation': first.reconciliation_path.read_text(encoding='utf-8'),
                'validation': first.validation_path.read_text(encoding='utf-8'),
            }

            second = run_reporting_pack(root)
            second_outputs = {
                'aggregate': second.comparison_aggregate_path.read_text(encoding='utf-8'),
                'bucket': second.comparison_by_bucket_path.read_text(encoding='utf-8'),
                'side': second.comparison_by_side_path.read_text(encoding='utf-8'),
                'fee_aggregate': second.fee_comparison_aggregate_path.read_text(encoding='utf-8'),
                'fee_bucket': second.fee_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'fee_side': second.fee_comparison_by_side_path.read_text(encoding='utf-8'),
                'fee_scenarios': second.fee_scenario_comparison_path.read_text(encoding='utf-8'),
                'spread_capture_aggregate': second.spread_capture_comparison_aggregate_path.read_text(encoding='utf-8'),
                'spread_capture_bucket': second.spread_capture_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'spread_capture_side': second.spread_capture_comparison_by_side_path.read_text(encoding='utf-8'),
                'provider_econ_aggregate': second.provider_econ_comparison_aggregate_path.read_text(encoding='utf-8'),
                'provider_econ_bucket': second.provider_econ_comparison_by_bucket_path.read_text(encoding='utf-8'),
                'provider_econ_side': second.provider_econ_comparison_by_side_path.read_text(encoding='utf-8'),
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

            fee_aggregate_rows = self._read_csv(result.fee_comparison_aggregate_path)
            self.assertEqual(
                [row['lane'] for row in fee_aggregate_rows],
                ['v2_realized', '3a_pure_book', '3b_hybrid'],
            )
            self.assertEqual(fee_aggregate_rows[0]['trader_fee_paid_bps_on_requested_notional'], '15')
            self.assertEqual(fee_aggregate_rows[1]['fee_precision'], 'modeled_from_locked_v3_schedule')
            self.assertIn('maker rebates only', fee_aggregate_rows[1]['notes'])
            self.assertIn('Blended route', fee_aggregate_rows[2]['notes'])

            spread_capture_rows = self._read_csv(result.spread_capture_comparison_aggregate_path)
            self.assertEqual(
                [row['lane'] for row in spread_capture_rows],
                ['3a_pure_book', '3b_hybrid'],
            )
            pure_book_spread_capture = next(row for row in spread_capture_rows if row['lane'] == '3a_pure_book')
            hybrid_spread_capture = next(row for row in spread_capture_rows if row['lane'] == '3b_hybrid')
            self.assertEqual(pure_book_spread_capture['gross_spread_capture_usd'], '47')
            self.assertEqual(hybrid_spread_capture['gross_spread_capture_usd'], '47')
            self.assertEqual(hybrid_spread_capture['resting_book_filled_notional_usd'], '13801')
            self.assertIn('pure-book leg only', hybrid_spread_capture['notes'].lower())

            spread_capture_side_rows = self._read_csv(result.spread_capture_comparison_by_side_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['gross_spread_capture_usd'] for row in spread_capture_side_rows},
                {
                    ('buy', '3a_pure_book'): '49',
                    ('buy', '3b_hybrid'): '49',
                    ('sell', '3a_pure_book'): '-2',
                    ('sell', '3b_hybrid'): '-2',
                },
            )

            spread_capture_bucket_rows = self._read_csv(result.spread_capture_comparison_by_bucket_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['gross_spread_capture_usd'] for row in spread_capture_bucket_rows},
                {
                    ('<1k', '3a_pure_book'): '-1',
                    ('<1k', '3b_hybrid'): '-1',
                    ('1k-5k', '3a_pure_book'): '-2',
                    ('1k-5k', '3b_hybrid'): '-2',
                    ('25k+', '3a_pure_book'): '50',
                    ('25k+', '3b_hybrid'): '50',
                },
            )

            provider_econ_rows = self._read_csv(result.provider_econ_comparison_aggregate_path)
            self.assertEqual(
                [row['lane'] for row in provider_econ_rows],
                ['v2_realized', '3a_pure_book', '3b_hybrid'],
            )
            provider_v2 = next(row for row in provider_econ_rows if row['lane'] == 'v2_realized')
            provider_3a = next(row for row in provider_econ_rows if row['lane'] == '3a_pure_book')
            provider_3b = next(row for row in provider_econ_rows if row['lane'] == '3b_hybrid')
            self.assertEqual(provider_v2['next_event_horizon_supported_rows'], '2')
            self.assertEqual(provider_v2['next_event_horizon_unavailable_rows'], '1')
            self.assertEqual(provider_3a['next_event_horizon_supported_rows'], '2')
            self.assertEqual(provider_3b['next_event_horizon_supported_rows'], '2')
            self.assertEqual(provider_v2['lp_fee_accrual_usd'], fee_aggregate_rows[0]['active_lp_fee_earned_usd'])
            self.assertEqual(provider_3a['maker_rebate_usd'], fee_aggregate_rows[1]['maker_rebate_earned_usd'])
            self.assertEqual(provider_3b['maker_rebate_usd'], fee_aggregate_rows[2]['maker_rebate_earned_usd'])
            self.assertEqual(provider_3a['gross_spread_capture_usd'], pure_book_spread_capture['gross_spread_capture_usd'])
            self.assertEqual(provider_3b['gross_spread_capture_usd'], hybrid_spread_capture['gross_spread_capture_usd'])
            self.assertEqual(provider_3a['maker_markout_loss_proxy_usd'], '0')
            self.assertEqual(provider_3b['maker_markout_loss_proxy_usd'], '0')
            self.assertEqual(provider_3a['net_provider_economics_proxy_usd'], provider_3a['gross_provider_revenue_proxy_usd'])
            self.assertEqual(provider_3b['net_provider_economics_proxy_usd'], provider_3b['gross_provider_revenue_proxy_usd'])
            self.assertIn('divergence/LVR-style loss proxy', provider_v2['notes'])

            provider_econ_side_rows = self._read_csv(result.provider_econ_comparison_by_side_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['next_event_horizon_supported_rows'] for row in provider_econ_side_rows},
                {
                    ('buy', 'v2_realized'): '1',
                    ('buy', '3a_pure_book'): '1',
                    ('buy', '3b_hybrid'): '1',
                    ('sell', 'v2_realized'): '1',
                    ('sell', '3a_pure_book'): '1',
                    ('sell', '3b_hybrid'): '1',
                },
            )

            provider_econ_bucket_rows = self._read_csv(result.provider_econ_comparison_by_bucket_path)
            self.assertEqual(
                {(row['segment'], row['lane']): row['next_event_horizon_supported_rows'] for row in provider_econ_bucket_rows},
                {
                    ('<1k', 'v2_realized'): '1',
                    ('<1k', '3a_pure_book'): '1',
                    ('<1k', '3b_hybrid'): '1',
                    ('1k-5k', 'v2_realized'): '1',
                    ('1k-5k', '3a_pure_book'): '1',
                    ('1k-5k', '3b_hybrid'): '1',
                    ('25k+', 'v2_realized'): '0',
                    ('25k+', '3a_pure_book'): '0',
                    ('25k+', '3b_hybrid'): '0',
                },
            )

            fee_scenario_rows = self._read_csv(result.fee_scenario_comparison_path)
            self.assertEqual(
                {(row['lane'], row['scenario_id']) for row in fee_scenario_rows},
                {
                    ('v2_realized', 'v2_fixed'),
                    ('3a_pure_book', 'no_xsauce'),
                    ('3a_pure_book', 'tier2_10pct'),
                    ('3b_hybrid', 'no_xsauce'),
                    ('3b_hybrid', 'tier2_10pct'),
                },
            )
            hybrid_default = next(
                row for row in fee_scenario_rows if row['lane'] == '3b_hybrid' and row['scenario_id'] == 'no_xsauce'
            )
            hybrid_discount = next(
                row for row in fee_scenario_rows if row['lane'] == '3b_hybrid' and row['scenario_id'] == 'tier2_10pct'
            )
            self.assertGreater(
                float(hybrid_default['all_in_trader_cost_bps_on_requested_notional']),
                float(hybrid_discount['all_in_trader_cost_bps_on_requested_notional']),
            )

            aggregate_rows = self._read_csv(result.comparison_aggregate_path)
            benchmark_row = next(row for row in aggregate_rows if row['lane'] == 'lambdaplex_published')
            self.assertEqual(benchmark_row['data_status'], 'placeholder')
            self.assertEqual(benchmark_row['row_count'], '')
            self.assertEqual(benchmark_row['avg_slippage_bps'], '')
            self.assertEqual(benchmark_row['avg_amm_pre_trade_spot_gross_slippage_bps'], '')
            self.assertIn('placeholder', benchmark_row['notes'])

            validation = json.loads(result.summary_path.read_text(encoding='utf-8'))
            self.assertEqual(
                [row['status'] for row in validation['validation']['lanes']],
                ['pass', 'pass', 'pass'],
            )
            self.assertEqual(
                [row['default_fee_rollup_match'] for row in validation['validation']['lanes']],
                ['true', 'true', 'true'],
            )
            final_report = result.final_comparison_path.read_text(encoding='utf-8')
            self.assertIn('## Fee-inclusive economics', final_report)
            self.assertIn('## Gross spread capture proxy', final_report)
            self.assertIn('## Symmetric provider-economics comparison', final_report)
            self.assertIn('### Net provider-economics proxy layer', final_report)
            self.assertIn('## Provider-economics side split', final_report)
            self.assertIn('## Provider-economics bucket split', final_report)
            self.assertIn('pure-book leg of 3B', final_report)
            self.assertIn('## xSAUCE fee scenario sensitivity', final_report)

            validation_report = result.validation_path.read_text(encoding='utf-8')
            self.assertIn('## Provider-economics horizon checks', validation_report)
            self.assertIn('next-event', validation_report.lower())

            self.assertEqual(
                validation['spread_capture_lane_rollups']['3b_hybrid']['aggregate']['gross_spread_capture_total'],
                47.0,
            )
            self.assertEqual(
                validation['provider_econ_lane_rollups']['3b_hybrid']['aggregate']['next_event_horizon_supported_rows'],
                2,
            )

    def test_spread_capture_observation_uses_hybrid_pure_book_leg_only(self) -> None:
        fee_policy = load_fee_policy(Path('config/fees.yaml'))
        row = self._lane_row(
            lane='3b_hybrid',
            replay_unit_id='swap:hybrid:trade:1',
            timestamp='2024-01-01T00:00:00Z',
            side='buy',
            requested_size='25000',
            requested_notional='25000',
            filled_size='25000',
            filled_notional='15600',
            completion_ratio='1',
            reference_price='0.625',
            avg_execution_price='0.624',
            slippage_field='execution_slippage_bps',
            slippage_value='15',
            fee_covered='true',
            remainder_size='0',
            admissibility_passed='true',
            trade_row_id='1',
            swap_event_id='1',
            trade_timestamp_seconds='1704067200',
            source_ordering_key='1704067200:1:1',
            base_volume_raw='25000000000',
            target_volume_raw='2500000000000',
            fee_fields=build_hybrid_fee_fields(
                fee_policy,
                requested_notional=25000.0,
                pure_book_filled_size=20000.0,
                pure_book_filled_notional=12550.0,
                v2_backstop_filled_size=5000.0,
                v2_backstop_execution_price=0.61,
            ),
        )

        observation = spread_capture_observation_from_row(row)

        self.assertEqual(observation.resting_book_filled_size, 20000.0)
        self.assertEqual(observation.resting_book_filled_notional_usd, 12550.0)
        self.assertEqual(
            observation.gross_spread_capture_usd,
            gross_spread_capture_usd(
                side='buy',
                reference_price=0.625,
                filled_size=20000.0,
                filled_notional=12550.0,
            ),
        )
        self.assertNotEqual(
            observation.gross_spread_capture_usd,
            gross_spread_capture_usd(
                side='buy',
                reference_price=0.625,
                filled_size=25000.0,
                filled_notional=15600.0,
            ),
        )

    def test_spread_capture_observation_rejects_mixed_hybrid_row_without_pure_book_notional(self) -> None:
        row = self._lane_row(
            lane='3b_hybrid',
            replay_unit_id='swap:hybrid:trade:missing-breakdown',
            timestamp='2024-01-01T00:00:00Z',
            side='buy',
            requested_size='25000',
            requested_notional='25000',
            filled_size='25000',
            filled_notional='15600',
            completion_ratio='1',
            reference_price='0.625',
            avg_execution_price='0.624',
            slippage_field='execution_slippage_bps',
            slippage_value='15',
            fee_covered='true',
            remainder_size='0',
            admissibility_passed='true',
            trade_row_id='2',
            swap_event_id='2',
            trade_timestamp_seconds='1704067201',
            source_ordering_key='1704067201:1:1',
            base_volume_raw='25000000000',
            target_volume_raw='2500000000000',
            fee_fields={},
        )
        row['route_breakdown'] = json.dumps({'pure_book': 20000.0, 'v2_backstop': 5000.0}, sort_keys=True)

        with self.assertRaisesRegex(ValueError, r'fee_route_breakdown\.pure_book'):
            spread_capture_observation_from_row(row)

    def test_reporting_pack_merges_comparable_benchmark_metrics_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_reporting_fixture(root, benchmark_payload=self._benchmark_payload(comparable=True))

            result = run_reporting_pack(root)

            aggregate_rows = self._read_csv(result.comparison_aggregate_path)
            benchmark_row = next(row for row in aggregate_rows if row['lane'] == 'lambdaplex_published')
            self.assertEqual(benchmark_row['benchmark_comparable'], 'true')
            self.assertEqual(benchmark_row['fill_rate'], '0.975')
            self.assertEqual(benchmark_row['avg_completion_ratio'], '0.982')
            self.assertEqual(benchmark_row['avg_slippage_bps'], '6.2')
            self.assertEqual(benchmark_row['avg_amm_pre_trade_spot_gross_slippage_bps'], '')
            self.assertEqual(benchmark_row['remainder_size_hbar'], '1250.5')
            self.assertEqual(benchmark_row['source_notes_path'], 'benchmarks/lambdaplex/source-notes.md')
            self.assertIn('published_metrics_captured', benchmark_row['benchmark_provenance'])

            final_report = result.final_comparison_path.read_text(encoding='utf-8')
            self.assertIn('| Lambdaplex published panel | 42 | 0.975 | 0.982 | 6.2 |  | 1250.5 |', final_report)
            self.assertIn('benchmarks/lambdaplex/source-notes.md', final_report)

            summary = json.loads(result.summary_path.read_text(encoding='utf-8'))
            manifest = json.loads(result.manifest_path.read_text(encoding='utf-8'))
            self.assertTrue(summary['benchmark']['comparable'])
            self.assertEqual(summary['benchmark']['source_notes_path'], 'benchmarks/lambdaplex/source-notes.md')
            self.assertEqual(
                summary['benchmark']['provenance']['local_payload_state'],
                'published_metrics_captured',
            )
            self.assertEqual(
                manifest['benchmark']['comparable_headline_metrics']['row_count'],
                42,
            )

    def _write_reporting_fixture(self, root: Path, *, benchmark_payload: dict[str, object] | None = None) -> None:
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
        (config_dir / 'fees.yaml').write_text(Path('config/fees.yaml').read_text(encoding='utf-8'), encoding='utf-8')
        fee_policy = load_fee_policy(config_dir / 'fees.yaml')
        self._write_benchmark_contract(
            benchmark_dir,
            benchmark_payload or self._benchmark_payload(),
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
                fee_fields=build_v2_fee_fields(fee_policy, filled_size=1000.0, filled_notional=500.0),
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
                fee_fields=build_v2_fee_fields(fee_policy, filled_size=2000.0, filled_notional=1000.0),
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
                fee_fields=build_v2_fee_fields(fee_policy, filled_size=40000.0, filled_notional=25000.0),
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
                fee_fields=build_v3_fee_fields(
                    fee_policy,
                    requested_notional=500.0,
                    filled_size=1000.0,
                    filled_notional=499.0,
                ),
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
                fee_fields=build_v3_fee_fields(
                    fee_policy,
                    requested_notional=1000.0,
                    filled_size=1500.0,
                    filled_notional=752.0,
                ),
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
                fee_fields=build_v3_fee_fields(
                    fee_policy,
                    requested_notional=25000.0,
                    filled_size=20000.0,
                    filled_notional=12550.0,
                ),
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
                fee_fields=build_hybrid_fee_fields(
                    fee_policy,
                    requested_notional=500.0,
                    pure_book_filled_size=1000.0,
                    pure_book_filled_notional=499.0,
                    v2_backstop_filled_size=0.0,
                    v2_backstop_execution_price=None,
                ),
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
                fee_fields=build_hybrid_fee_fields(
                    fee_policy,
                    requested_notional=1000.0,
                    pure_book_filled_size=1500.0,
                    pure_book_filled_notional=752.0,
                    v2_backstop_filled_size=500.0,
                    v2_backstop_execution_price=0.5,
                ),
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
                fee_fields=build_hybrid_fee_fields(
                    fee_policy,
                    requested_notional=25000.0,
                    pure_book_filled_size=20000.0,
                    pure_book_filled_notional=12550.0,
                    v2_backstop_filled_size=5000.0,
                    v2_backstop_execution_price=0.61,
                ),
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
                fee_precision='modeled_from_locked_v2_schedule',
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
                fee_precision='modeled_from_locked_v3_schedule',
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
                fee_precision='route_aware_modeled_from_locked_v2_v3_schedules',
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
        requested_notional_total = requested_notional_raw_total / 1_000_000
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
        parity_slippage_values = [
            float(row['amm_pre_trade_spot_gross_slippage_bps'])
            for row in rows
            if row.get('amm_pre_trade_spot_gross_slippage_bps')
        ]
        parity_slippage_avg = 0.0
        parity_slippage_avg_abs = 0.0
        if parity_slippage_values:
            parity_slippage_avg = sum(parity_slippage_values) / len(parity_slippage_values)
            parity_slippage_avg_abs = sum(abs(value) for value in parity_slippage_values) / len(parity_slippage_values)

        fee_basis_filled_total = sum(float(row.get('fee_basis_filled_notional_usd', '0') or '0') for row in rows)
        default_trader_fee_total = sum(float(row.get('trader_fee_paid_usd', '0') or '0') for row in rows)
        default_protocol_fee_total = sum(float(row.get('protocol_fee_earned_usd', '0') or '0') for row in rows)
        default_active_lp_fee_total = sum(float(row.get('active_lp_fee_earned_usd', '0') or '0') for row in rows)
        default_maker_rebate_total = sum(float(row.get('maker_rebate_earned_usd', '0') or '0') for row in rows)
        v3_min_order_ineligible_rows = sum(1 for row in rows if row.get('v3_min_order_ineligible') == 'true')
        default_scenario_id = next((str(row.get('fee_scenario_id', '')).strip() for row in rows if row.get('fee_scenario_id')), '')

        scenario_accumulators: dict[str, dict[str, float]] = {}
        for row in rows:
            for scenario_id, payload in scenario_totals_from_breakdown(
                json.loads(row.get('fee_route_breakdown', '{}') or '{}')
            ).items():
                accumulator = scenario_accumulators.setdefault(
                    scenario_id,
                    {
                        'trader_fee_paid_usd': 0.0,
                        'protocol_fee_earned_usd': 0.0,
                        'active_lp_fee_earned_usd': 0.0,
                        'maker_rebate_earned_usd': 0.0,
                    },
                )
                for key in accumulator:
                    accumulator[key] += float(payload.get(key, 0.0))

        def _bps(amount: float, denominator: float) -> float:
            if denominator <= 0:
                return 0.0
            return round((amount / denominator) * 10_000.0, 12)

        def _rollup_payload(
            *,
            trader_fee_paid_total: float,
            protocol_fee_earned_total: float,
            active_lp_fee_earned_total: float,
            maker_rebate_earned_total: float,
        ) -> dict[str, object]:
            return {
                'fee_basis_filled_notional_usd': format_decimal(fee_basis_filled_total),
                'requested_notional_usdc': format_decimal(requested_notional_total),
                'trader_fee_paid_usd': format_decimal(trader_fee_paid_total),
                'protocol_fee_earned_usd': format_decimal(protocol_fee_earned_total),
                'active_lp_fee_earned_usd': format_decimal(active_lp_fee_earned_total),
                'maker_rebate_earned_usd': format_decimal(maker_rebate_earned_total),
                'trader_fee_paid_bps_on_filled_notional': _bps(trader_fee_paid_total, fee_basis_filled_total),
                'protocol_fee_earned_bps_on_filled_notional': _bps(protocol_fee_earned_total, fee_basis_filled_total),
                'active_lp_fee_earned_bps_on_filled_notional': _bps(active_lp_fee_earned_total, fee_basis_filled_total),
                'maker_rebate_earned_bps_on_filled_notional': _bps(maker_rebate_earned_total, fee_basis_filled_total),
                'trader_fee_paid_bps_on_requested_notional': _bps(trader_fee_paid_total, requested_notional_total),
                'protocol_fee_earned_bps_on_requested_notional': _bps(protocol_fee_earned_total, requested_notional_total),
                'active_lp_fee_earned_bps_on_requested_notional': _bps(active_lp_fee_earned_total, requested_notional_total),
                'maker_rebate_earned_bps_on_requested_notional': _bps(maker_rebate_earned_total, requested_notional_total),
            }

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
            'amm_pre_trade_spot_gross_slippage_bps': {
                'avg': round(parity_slippage_avg, 12),
                'avg_abs': round(parity_slippage_avg_abs, 12),
                'finite_rows': len(parity_slippage_values),
                'infinite_rows': 0,
            },
            'totals': totals,
            'fees': {
                'fee_precision': fee_precision,
                'fee_covered_rows': fee_covered_rows,
                'fee_missing_rows': fee_missing_rows,
                'default_scenario_id': default_scenario_id,
                'v3_min_order_ineligible_rows': v3_min_order_ineligible_rows,
                'default_rollup': _rollup_payload(
                    trader_fee_paid_total=default_trader_fee_total,
                    protocol_fee_earned_total=default_protocol_fee_total,
                    active_lp_fee_earned_total=default_active_lp_fee_total,
                    maker_rebate_earned_total=default_maker_rebate_total,
                ),
                'scenario_rollups': {
                    scenario_id: _rollup_payload(
                        trader_fee_paid_total=payload['trader_fee_paid_usd'],
                        protocol_fee_earned_total=payload['protocol_fee_earned_usd'],
                        active_lp_fee_earned_total=payload['active_lp_fee_earned_usd'],
                        maker_rebate_earned_total=payload['maker_rebate_earned_usd'],
                    )
                    for scenario_id, payload in scenario_accumulators.items()
                },
            },
            'mapping': mapping,
            'reconciliation': reconciliation,
        }

    @staticmethod
    def _write_benchmark_contract(benchmark_dir: Path, payload: dict[str, object]) -> None:
        (benchmark_dir / 'source-notes.md').write_text(
            '# Source notes\n\nTracked local benchmark contract for RH-09.\n',
            encoding='utf-8',
        )
        (benchmark_dir / 'published-results.json').write_text(
            json.dumps(payload, indent=2) + '\n',
            encoding='utf-8',
        )

    @staticmethod
    def _benchmark_payload(*, comparable: bool = False) -> dict[str, object]:
        if comparable:
            return {
                'schema_version': 'rh09_lambdaplex_published_panel_v1',
                'source': 'Lambdaplex published benchmark panel',
                'market': 'HBAR/USDC',
                'status': 'comparable',
                'source_notes_path': 'benchmarks/lambdaplex/source-notes.md',
                'headline_metrics': {
                    'panel_fill_rate_pct': '97.5%',
                    'panel_avg_slippage_bps': '6.2',
                },
                'comparable_headline_metrics': {
                    'row_count': 42,
                    'fill_rate': 0.975,
                    'avg_completion_ratio': 0.982,
                    'avg_slippage_bps': 6.2,
                    'avg_abs_slippage_bps': 6.2,
                    'remainder_size_hbar': 1250.5,
                },
                'provenance': {
                    'local_payload_state': 'published_metrics_captured',
                    'local_payload_complete': True,
                    'blocking_reason': '',
                    'captured_artifacts': [
                        'benchmarks/lambdaplex/published-results.json',
                        'benchmarks/lambdaplex/source-notes.md',
                    ],
                    'mapping_notes': [
                        'Comparable metrics mapped into the reporting aggregate row.',
                    ],
                },
                'notes': [
                    'External published panel; values are not replay-generated.',
                ],
            }
        return {
            'schema_version': 'rh09_lambdaplex_published_panel_v1',
            'source': 'Lambdaplex published benchmark panel',
            'market': 'HBAR/USDC',
            'status': 'placeholder',
            'source_notes_path': 'benchmarks/lambdaplex/source-notes.md',
            'headline_metrics': {},
            'comparable_headline_metrics': {},
            'provenance': {
                'local_payload_state': 'placeholder_only',
                'local_payload_complete': False,
                'blocking_reason': 'Comparable Lambdaplex headline metrics are not recorded locally yet.',
                'captured_artifacts': [
                    'benchmarks/lambdaplex/published-results.json',
                    'benchmarks/lambdaplex/source-notes.md',
                ],
                'mapping_notes': [
                    'Only comparable_headline_metrics are merged into reporting outputs.',
                ],
            },
            'notes': [
                'Populate from published Lambdaplex outputs before final comparison runs.',
            ],
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
        fee_fields: dict[str, object],
        parity_slippage_value: str = '',
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
            'amm_pre_trade_spot_reference_price': reference_price,
            'avg_execution_price': avg_execution_price,
            'fees_paid': format_decimal(float(fee_fields.get('fees_paid', 0.0))),
            'fee_contract_version': str(fee_fields.get('fee_contract_version', '')),
            'fee_scenario_id': str(fee_fields.get('fee_scenario_id', '')),
            'v3_min_order_ineligible': 'true' if bool(fee_fields.get('v3_min_order_ineligible', False)) else 'false',
            'fee_basis_filled_notional_usd': format_decimal(float(fee_fields.get('fee_basis_filled_notional_usd', 0.0))),
            'trader_fee_paid_usd': format_decimal(float(fee_fields.get('trader_fee_paid_usd', 0.0))),
            'protocol_fee_earned_usd': format_decimal(float(fee_fields.get('protocol_fee_earned_usd', 0.0))),
            'active_lp_fee_earned_usd': format_decimal(float(fee_fields.get('active_lp_fee_earned_usd', 0.0))),
            'maker_rebate_earned_usd': format_decimal(float(fee_fields.get('maker_rebate_earned_usd', 0.0))),
            'fee_methodology': 'test',
            'fee_precision': 'test',
            'fee_covered': fee_covered,
            'fee_route_breakdown': json.dumps(fee_fields.get('fee_route_breakdown', {}), sort_keys=True),
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
            'amm_pre_trade_spot_gross_slippage_bps': parity_slippage_value,
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

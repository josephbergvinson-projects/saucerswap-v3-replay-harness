import csv
import json
from pathlib import Path
import tempfile
import unittest

from saucerswap_v3_replay.validation.golden_cases import evaluate_golden_cases
from saucerswap_v3_replay.validation.polish import (
    build_sampled_realized_v2_sanity_pack,
    render_sampled_realized_v2_markdown,
    run_validation_polish,
)


class GoldenCaseTests(unittest.TestCase):
    def test_evaluate_golden_cases_matches_explicit_toy_fixture_expectations(self) -> None:
        payload = evaluate_golden_cases(
            Path('tests/fixtures/toy_book.yaml'),
            Path('tests/fixtures/toy_flow.csv'),
            Path('tests/fixtures/toy_expected_outputs.json'),
        )

        self.assertEqual(payload['status'], 'pass')
        self.assertEqual(payload['counts']['case_count'], 3)
        self.assertEqual(payload['counts']['fail_count'], 0)

        pass_case = next(case for case in payload['cases'] if case['name'] == 'hybrid_admissibility_pass')
        self.assertEqual(pass_case['check_summary'], '14/14')
        self.assertEqual(pass_case['actual']['route_breakdown']['v2_backstop'], '50.059980007197')
        self.assertTrue(pass_case['checks']['admissibility_passed'])


class ValidationPolishSamplingTests(unittest.TestCase):
    def test_sample_pack_selects_first_row_per_side_bucket_and_renders_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / 'lane_v2_baseline.csv'
            self._write_csv(
                csv_path,
                [
                    self._baseline_row(
                        replay_unit_id='buy-low-first',
                        side='buy',
                        requested_size='1000',
                        requested_notional='500',
                        filled_size='1000',
                        filled_notional='500',
                        source_ordering_key='100:1:1',
                    ),
                    self._baseline_row(
                        replay_unit_id='buy-low-second',
                        side='buy',
                        requested_size='1200',
                        requested_notional='600',
                        filled_size='1200',
                        filled_notional='600',
                        source_ordering_key='101:1:2',
                    ),
                    self._baseline_row(
                        replay_unit_id='sell-mid',
                        side='sell',
                        requested_size='2500',
                        requested_notional='2000',
                        filled_size='2500',
                        filled_notional='2000',
                        source_ordering_key='200:2:1',
                    ),
                    self._baseline_row(
                        replay_unit_id='buy-high',
                        side='buy',
                        requested_size='50000',
                        requested_notional='30000',
                        filled_size='50000',
                        filled_notional='30000',
                        source_ordering_key='300:3:1',
                    ),
                    self._baseline_row(
                        replay_unit_id='sell-high',
                        side='sell',
                        requested_size='45000',
                        requested_notional='40000',
                        filled_size='45000',
                        filled_notional='40000',
                        source_ordering_key='400:4:1',
                    ),
                ],
            )

            payload = build_sampled_realized_v2_sanity_pack(
                csv_path,
                bucket_config_path=Path('config/buckets.yaml'),
            )
            markdown = render_sampled_realized_v2_markdown(payload)

            self.assertEqual(payload['status'], 'pass')
            self.assertEqual(payload['counts']['selected_segments'], 4)
            buy_low = next(sample for sample in payload['samples'] if sample['segment'] == 'buy / <1k')
            self.assertEqual(buy_low['source_anchor']['replay_unit_id'], 'buy-low-first')
            self.assertEqual(buy_low['check_summary'], '8/8')
            self.assertIn('buy-low-first', markdown)
            self.assertNotIn('buy-low-second', markdown)
            self.assertIn('buy / <1k', markdown)

    @staticmethod
    def _baseline_row(
        *,
        replay_unit_id: str,
        side: str,
        requested_size: str,
        requested_notional: str,
        filled_size: str,
        filled_notional: str,
        source_ordering_key: str,
    ) -> dict[str, str]:
        return {
            'lane': 'v2_realized',
            'replay_unit_id': replay_unit_id,
            'timestamp': '2026-01-01T00:00:00Z',
            'side': side,
            'requested_size': requested_size,
            'requested_notional': requested_notional,
            'filled_size': filled_size,
            'filled_notional': filled_notional,
            'completion_ratio': '1',
            'reference_price': '0.5',
            'avg_execution_price': '0.5',
            'realized_slippage_bps': '0',
            'fees_paid': '0',
            'fee_methodology': 'toy',
            'fee_precision': 'not_allocated_per_replay_unit',
            'fee_covered': 'true',
            'remainder_size': '0',
            'route_breakdown': json.dumps({'v2': float(filled_size)}),
            'admissibility_passed': 'true',
            'tradeRowId': '1',
            'swapEventId': '1',
            'tradeTimestampSeconds': '1704067200',
            'source_ordering_key': source_ordering_key,
            'baseId': 'USDC',
            'targetId': 'HBAR',
            'baseVolumeRaw': '1000000',
            'targetVolumeRaw': '100000000',
            'reference_price_source': 'at_or_before',
            'reference_price_fallback': 'false',
            'swap_metadata_covered': 'true',
        }

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


class ValidationPolishPipelineTests(unittest.TestCase):
    def test_run_validation_polish_is_deterministic_and_materializes_report_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._write_validation_fixture(root)

            first = run_validation_polish(root)
            first_outputs = self._read_outputs(first)

            second = run_validation_polish(root)
            second_outputs = self._read_outputs(second)

            self.assertEqual(first_outputs, second_outputs)

            summary = json.loads(first.summary_path.read_text(encoding='utf-8'))
            self.assertEqual(summary['overall_status'], 'pass')
            self.assertEqual(summary['sampled_realized_v2']['counts']['selected_segments'], 4)
            self.assertEqual(summary['golden_cases']['counts']['case_count'], 3)

            validation_report = first.validation_path.read_text(encoding='utf-8')
            self.assertIn('## Study caveats', validation_report)
            self.assertIn('reports/generated/rh08-validation-sampled-v2-sanity.json', validation_report)
            self.assertIn('tests/fixtures/toy_book.yaml', validation_report)
            self.assertNotIn('pending-write', validation_report)

    def _write_validation_fixture(self, root: Path) -> None:
        processed_dir = root / 'data' / 'processed'
        config_dir = root / 'config'
        benchmark_dir = root / 'benchmarks' / 'lambdaplex'
        fixture_dir = root / 'tests' / 'fixtures'
        processed_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        fixture_dir.mkdir(parents=True, exist_ok=True)

        (config_dir / 'buckets.yaml').write_text(Path('config/buckets.yaml').read_text(encoding='utf-8'), encoding='utf-8')
        (benchmark_dir / 'source-notes.md').write_text(
            '# Source notes\n\nTracked local benchmark contract for RH-09.\n',
            encoding='utf-8',
        )
        (benchmark_dir / 'published-results.json').write_text(
            json.dumps(
                {
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
                },
                indent=2,
            )
            + '\n',
            encoding='utf-8',
        )

        baseline_rows = [
            ValidationPolishSamplingTests._baseline_row(
                replay_unit_id='buy-low-first',
                side='buy',
                requested_size='1000',
                requested_notional='500',
                filled_size='1000',
                filled_notional='500',
                source_ordering_key='100:1:1',
            ),
            ValidationPolishSamplingTests._baseline_row(
                replay_unit_id='sell-mid',
                side='sell',
                requested_size='2500',
                requested_notional='2000',
                filled_size='2500',
                filled_notional='2000',
                source_ordering_key='200:2:1',
            ),
            ValidationPolishSamplingTests._baseline_row(
                replay_unit_id='buy-high',
                side='buy',
                requested_size='50000',
                requested_notional='30000',
                filled_size='50000',
                filled_notional='30000',
                source_ordering_key='300:3:1',
            ),
            ValidationPolishSamplingTests._baseline_row(
                replay_unit_id='sell-high',
                side='sell',
                requested_size='45000',
                requested_notional='40000',
                filled_size='45000',
                filled_notional='40000',
                source_ordering_key='400:4:1',
            ),
        ]
        ValidationPolishSamplingTests._write_csv(processed_dir / 'lane_v2_baseline.csv', baseline_rows)

        self._write_json(
            processed_dir / 'v2_baseline_summary.json',
            {
                'generated_at_utc': '2026-03-24T19:40:52Z',
                'lane': 'v2_realized',
                'mapping': {'fingerprint': 'baseline-fingerprint'},
                'row_counts': {'baseline_rows': 4},
            },
        )
        self._write_json(processed_dir / 'v2_baseline_manifest.json', {'lane': 'v2_realized'})
        self._write_json(
            processed_dir / 'pure_book_summary.json',
            {
                'generated_at_utc': '2026-03-24T21:06:59Z',
                'lane': '3a_pure_book',
                'mapping': {'fingerprint': 'pure-book-fingerprint'},
                'row_counts': {'pure_book_rows': 4},
            },
        )
        self._write_json(processed_dir / 'pure_book_manifest.json', {'lane': '3a_pure_book'})
        self._write_json(
            processed_dir / 'hybrid_summary.json',
            {
                'generated_at_utc': '2026-03-24T21:41:36Z',
                'lane': '3b_hybrid',
                'mapping': {'fingerprint': 'hybrid-fingerprint'},
                'row_counts': {'hybrid_rows': 4},
            },
        )
        self._write_json(processed_dir / 'hybrid_manifest.json', {'lane': '3b_hybrid'})
        self._write_json(
            processed_dir / 'reporting_pack_summary.json',
            {
                'generated_at_utc': '2026-03-25T00:28:20Z',
                'validation': {
                    'lanes': [
                        {
                            'lane': 'v2_realized',
                            'lane_label': 'V2 baseline',
                            'row_count_matches': 'true',
                            'requested_totals_match': 'true',
                            'filled_totals_match': 'true',
                            'completion_counts_match': 'true',
                            'fee_coverage_match': 'true',
                            'status': 'pass',
                        },
                        {
                            'lane': '3a_pure_book',
                            'lane_label': '3A pure-book',
                            'row_count_matches': 'true',
                            'requested_totals_match': 'true',
                            'filled_totals_match': 'true',
                            'completion_counts_match': 'true',
                            'fee_coverage_match': 'true',
                            'status': 'pass',
                        },
                        {
                            'lane': '3b_hybrid',
                            'lane_label': '3B hybrid',
                            'row_count_matches': 'true',
                            'requested_totals_match': 'true',
                            'filled_totals_match': 'true',
                            'completion_counts_match': 'true',
                            'fee_coverage_match': 'true',
                            'status': 'pass',
                        },
                    ],
                    'global_checks': [
                        'Lane order fixed to: V2 baseline, 3A pure-book, 3B hybrid.',
                        'All direct lane rollups matched mounted lane summaries: true.',
                    ],
                },
            },
        )
        self._write_json(processed_dir / 'reporting_pack_manifest.json', {'lane': 'reporting_pack'})

        for name in ['toy_book.yaml', 'toy_flow.csv', 'toy_expected_outputs.json']:
            (fixture_dir / name).write_text(Path('tests/fixtures', name).read_text(encoding='utf-8'), encoding='utf-8')

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    @staticmethod
    def _read_outputs(result) -> dict[str, str]:
        return {
            'sample_json': result.sampled_realized_v2_json_path.read_text(encoding='utf-8'),
            'sample_markdown': result.sampled_realized_v2_markdown_path.read_text(encoding='utf-8'),
            'golden_json': result.golden_cases_json_path.read_text(encoding='utf-8'),
            'golden_markdown': result.golden_cases_markdown_path.read_text(encoding='utf-8'),
            'validation': result.validation_path.read_text(encoding='utf-8'),
            'summary': result.summary_path.read_text(encoding='utf-8'),
            'manifest': result.manifest_path.read_text(encoding='utf-8'),
        }


if __name__ == '__main__':
    unittest.main()

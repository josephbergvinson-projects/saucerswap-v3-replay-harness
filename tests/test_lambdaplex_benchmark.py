import json
from pathlib import Path
import tempfile
import unittest

from saucerswap_v3_replay.benchmarks.lambdaplex import load_published_benchmark_status


class LambdaplexBenchmarkContractTests(unittest.TestCase):
    def test_load_placeholder_contract_normalizes_notes_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            benchmark_path = self._write_contract(
                root,
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
                        'blocking_reason': 'No locally tracked comparable headline values yet.',
                        'captured_artifacts': 'benchmarks/lambdaplex/published-results.json',
                        'mapping_notes': 'Only comparable_headline_metrics may be merged.',
                    },
                    'notes': 'Populate from tracked published outputs only.',
                },
            )

            status = load_published_benchmark_status(benchmark_path)

            self.assertEqual(status.status, 'placeholder')
            self.assertFalse(status.comparable)
            self.assertEqual(status.source_notes_path, 'benchmarks/lambdaplex/source-notes.md')
            self.assertEqual(list(status.notes), ['Populate from tracked published outputs only.'])
            self.assertEqual(status.provenance.local_payload_state, 'placeholder_only')
            self.assertEqual(
                list(status.provenance.captured_artifacts),
                ['benchmarks/lambdaplex/published-results.json'],
            )
            self.assertEqual(
                list(status.provenance.mapping_notes),
                ['Only comparable_headline_metrics may be merged.'],
            )
            self.assertEqual(status.as_dict()['source_notes_path'], 'benchmarks/lambdaplex/source-notes.md')

    def test_load_comparable_contract_requires_and_keeps_mapped_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            benchmark_path = self._write_contract(
                root,
                {
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
                        'fill_rate': '0.975',
                        'avg_completion_ratio': '0.982',
                        'avg_slippage_bps': '6.2',
                        'avg_abs_slippage_bps': '6.2',
                        'remainder_size_hbar': '1250.5',
                        'row_count': 42,
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
                },
            )

            status = load_published_benchmark_status(benchmark_path)

            self.assertTrue(status.comparable)
            self.assertEqual(status.comparable_headline_metrics['row_count'], 42)
            self.assertAlmostEqual(status.comparable_headline_metrics['fill_rate'], 0.975)
            self.assertEqual(status.as_dict()['provenance']['local_payload_complete'], True)

    def test_missing_source_notes_path_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            benchmark_dir = root / 'benchmarks' / 'lambdaplex'
            benchmark_dir.mkdir(parents=True, exist_ok=True)
            benchmark_path = benchmark_dir / 'published-results.json'
            benchmark_path.write_text(
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
                            'blocking_reason': 'Missing source notes.',
                            'captured_artifacts': [],
                            'mapping_notes': [],
                        },
                    },
                    indent=2,
                )
                + '\n',
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ValueError, 'source_notes_path does not exist'):
                load_published_benchmark_status(benchmark_path)

    def test_comparable_contract_missing_required_metric_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            benchmark_path = self._write_contract(
                root,
                {
                    'schema_version': 'rh09_lambdaplex_published_panel_v1',
                    'source': 'Lambdaplex published benchmark panel',
                    'market': 'HBAR/USDC',
                    'status': 'comparable',
                    'source_notes_path': 'benchmarks/lambdaplex/source-notes.md',
                    'headline_metrics': {},
                    'comparable_headline_metrics': {
                        'fill_rate': 0.98,
                        'avg_completion_ratio': 0.99,
                        'avg_slippage_bps': 4.2,
                        'remainder_size_hbar': 15.0,
                    },
                    'provenance': {
                        'local_payload_state': 'partial_mapping_only',
                        'local_payload_complete': False,
                        'blocking_reason': 'avg_abs_slippage_bps not captured locally.',
                        'captured_artifacts': [],
                        'mapping_notes': [],
                    },
                    'notes': [],
                },
            )

            with self.assertRaisesRegex(ValueError, 'avg_abs_slippage_bps'):
                load_published_benchmark_status(benchmark_path)

    @staticmethod
    def _write_contract(root: Path, payload: dict[str, object]) -> Path:
        benchmark_dir = root / 'benchmarks' / 'lambdaplex'
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        (benchmark_dir / 'source-notes.md').write_text('# Source notes\n', encoding='utf-8')
        benchmark_path = benchmark_dir / 'published-results.json'
        benchmark_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        return benchmark_path


if __name__ == '__main__':
    unittest.main()

import json
import unittest
from pathlib import Path

from saucerswap_v3_replay.extract.gigabrain import build_extract_manifest, projected_fields_from_sql, write_extract_manifest


REPO_ROOT = Path(__file__).resolve().parent.parent


class GigabrainProbeTests(unittest.TestCase):
    def test_projected_fields_from_sql(self):
        sql = """
        SELECT
          tdv2.id,
          tdv2.transactionHash,
          tdv2.consensusTimestamp
        FROM trade_data_v2 tdv2
        """
        self.assertEqual(
            projected_fields_from_sql(sql),
            ['id', 'transactionHash', 'consensusTimestamp'],
        )

    def test_projected_fields_returns_none_for_select_star(self):
        sql = "SELECT *\nFROM v2_swap_metadata"
        self.assertIsNone(projected_fields_from_sql(sql))

    def test_probe_manifest_blocks_when_access_is_missing(self):
        manifest = build_extract_manifest(REPO_ROOT, env={})
        self.assertEqual(manifest['status'], 'blocked_missing_access')
        self.assertFalse(manifest['normalization_readiness']['can_start'])
        self.assertEqual(len(manifest['queries']), 4)

    def test_write_extract_manifest(self):
        out_path = write_extract_manifest(REPO_ROOT, env={})
        payload = json.loads(out_path.read_text(encoding='utf-8'))
        self.assertEqual(payload['status'], 'blocked_missing_access')
        self.assertIn('queries', payload)


if __name__ == '__main__':
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from saucerswap_v3_replay.rules.admissibility import (
    load_hybrid_rule,
    passes_hybrid_admissibility,
    passes_limit_price,
    passes_slippage_cap,
)


class AdmissibilityTests(unittest.TestCase):
    def test_buy_limit_price(self):
        self.assertTrue(passes_limit_price('buy', execution_price=99, limit_price=100))
        self.assertFalse(passes_limit_price('buy', execution_price=101, limit_price=100))

    def test_sell_limit_price(self):
        self.assertTrue(passes_limit_price('sell', execution_price=101, limit_price=100))
        self.assertFalse(passes_limit_price('sell', execution_price=99, limit_price=100))

    def test_slippage_cap(self):
        self.assertTrue(passes_slippage_cap('buy', 100.0, 100.3, 50))
        self.assertFalse(passes_slippage_cap('buy', 100.0, 101.0, 50))

    def test_non_positive_execution_price_never_passes(self):
        self.assertFalse(passes_slippage_cap('buy', 100.0, 0.0, 50))
        self.assertFalse(passes_slippage_cap('sell', 100.0, 0.0, 50))

    def test_hybrid_admissibility_requires_quote_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'hybrid_rule.yaml'
            path.write_text(
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
                        '  notes: "test"',
                        '',
                    ]
                ),
                encoding='utf-8',
            )
            rule = load_hybrid_rule(path)

            self.assertFalse(
                passes_hybrid_admissibility(
                    rule,
                    side='buy',
                    reference_price=100.0,
                    execution_price=None,
                    quote_available=False,
                )
            )
            self.assertTrue(
                passes_hybrid_admissibility(
                    rule,
                    side='buy',
                    reference_price=100.0,
                    execution_price=100.3,
                    quote_available=True,
                )
            )


if __name__ == '__main__':
    unittest.main()

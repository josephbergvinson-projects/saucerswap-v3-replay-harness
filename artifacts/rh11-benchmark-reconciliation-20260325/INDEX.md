# RH-11 Benchmark Reconciliation Index

## Purpose
Determine whether the published Lambdaplex slide figures `15.47` / `2.82` can be mapped into the repo's merge-eligible benchmark schema.

## Reading order
1. `artifacts/rh11-benchmark-reconciliation-20260325/LAMBDAPLEX_15_47_2_82_SCHEMA_RECONCILIATION.md`
2. `benchmarks/lambdaplex/source-notes.md`
3. `benchmarks/lambdaplex/published-results.json`

## Files changed
- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`
- `tests/test_lambdaplex_benchmark.py`
- `artifacts/rh11-benchmark-reconciliation-20260325/LAMBDAPLEX_15_47_2_82_SCHEMA_RECONCILIATION.md`
- `artifacts/rh11-benchmark-reconciliation-20260325/INDEX.md`

## Expected conclusion
- `15.47` / `2.82` are storable as provenance-only published values
- they are not yet eligible for `comparable_headline_metrics`
- benchmark status should therefore be `incomplete`, not `comparable`

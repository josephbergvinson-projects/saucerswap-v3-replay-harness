# Reference Price Convention

The reference price is used for two jobs:

1. centering the synthetic book
2. measuring slippage

First-pass rule: use a pre-trade event-time aligned price source with an explicit fallback chain. The exact source should be frozen in Phase 0 and mirrored in `config/study.yaml`.

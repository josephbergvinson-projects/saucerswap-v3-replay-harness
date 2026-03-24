# Replay Contract

This document records the live-schema contract amendment that governs the first-pass SaucerSwap V3 replay study.

## Why this exists

The frozen planning source in `docs/planning/replay-study-plan-locked.md` assumed that replay units could be collapsed at a transaction/request boundary if the historical source exposed the needed provenance.

On 2026-03-24, RH-02 performed a second-pass live scan of Gigabrain through signed-in Metabase access and a direct `information_schema.columns` query against `SaucerSwap MySQL`.

That scan found no transaction-hash, transaction-id, consensus-timestamp, log-index, event-index, or other explicit per-transaction ordering column in the exposed V2 swap/trade/pool surfaces used by this study.

## Scan conclusion

Tables verified as relevant to the HBAR/USDC V2 0.15% study path:

- `trade_data_v2`
- `swap_events`
- `v2_swap_metadata`
- `pools_v2`
- `pools_v2_prices_minute`
- `pool_fees_day`
- `hbar_prices_minute`

Second-pass result:

- No transaction-hash / transaction-id / consensus-timestamp / log-index / event-index / explicit per-transaction ordering field exists in the exposed swap/trade/pool tables above.
- The only tx-hash-style hits in the live schema were orderbook-side tables such as `fill_events`, `order_fills`, `order_history`, and `orders`. Those are not the historical V2 pool-flow source for this study.

## Amended first-pass contract

The first-pass study is an **event-level replay benchmark**, not a true order-level reconstruction.

That means:

- the observed historical unit is the exposed V2 event/trade row, not a recovered user-order boundary
- 3A and 3B are still valid study-owned comparison lanes
- benchmark parity with Lambdaplex remains acceptable if Lambdaplex is also event-level
- request-level / order-level claims are out of scope unless a stronger provenance surface is recovered later

## Canonical first-pass replay unit

Until a better provenance surface is found:

- one observed `trade_data_v2` row is the canonical replay unit
- `tradeRowId` is the canonical row anchor
- `swapEventId` is preserved as the parent event reference
- no cross-row collapse is allowed without explicit transaction-boundary evidence
- replay ordering is `tradeTimestampSeconds`, then `swapEventId`, then `tradeRowId`

This preserves determinism and avoids inventing request boundaries that the source data does not expose.

## Implications for 3A and 3B

### 3A pure-book lane

3A remains viable under the amended contract as an event-level benchmark lane.

### 3B hybrid lane

3B also remains viable, but its interpretation narrows:

- residual means the remainder of the event-level observed unit after pure-book simulation
- it does **not** mean a recovered user-order residual spanning multiple historical on-chain events
- any admissibility rule remains a study-owned event-level proxy unless stronger provenance is recovered

## Allowed and disallowed claims

Allowed first-pass claims:

- event-level comparative benchmarking versus realized V2 and Lambdaplex
- directional conclusions on slippage, completion, and fee behavior under the explicit study assumptions
- explicit study-owned 3A / 3B counterfactual comparisons

Disallowed first-pass claims:

- exact recovery of user-order intent
- exact order-level completion behavior
- exact historical transaction-boundary reconstruction
- exact order-level admissibility behavior for 3B

## Upgrade path

If a stronger provenance surface is recovered later, the study may explicitly upgrade to an order-level contract.

That upgrade requires:

- a new documented schema/source path for transaction boundaries and intra-transaction ordering
- a revised replay-unit definition
- an explicit methodology change in `docs/methodology/phase-0-lock.md`
- corresponding config updates

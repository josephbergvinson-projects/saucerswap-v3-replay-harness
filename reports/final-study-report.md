# WHBAR/USDC Replay Study — Final Report

Repo state: `main @ 21cc2e2`

## Executive summary

This study asks a narrow question: if WHBAR/USDC flow that actually routed through the SaucerSwap V2 0.15% pool had instead faced a synthetic SaucerSwap V3-style execution surface, how would execution quality have changed?

The answer is directionally clear.

- **V2 baseline** delivers full completion, but at materially higher slippage.
- **V3 pure-book (3A)** cuts slippage sharply, but leaves too much large-order flow partially filled.
- **V3 hybrid (3B)** preserves essentially all of the slippage improvement while materially improving completion versus pure-book.
- **Lambdaplex** can now be compared on a better denominator using the explicit parity-proxy slippage metric, but its published panel still does not disclose enough methodology or completion data to treat it as fully apples-to-apples on every metric.

Bottom line: **the hybrid lane is the strongest overall study result**. It keeps average slippage near pure-book levels, materially reduces remainder versus pure-book, and is the best study-owned representation of how a V3-style surface could improve execution over the current V2 pool.

## Motivation

The purpose of the study was to evaluate whether a V3-style execution surface could offer a better trade-off than the current WHBAR/USDC V2 pool.

The internal decision problem was not just “can a synthetic order book beat V2 on quoted price?” It was:

1. can a Lambdaplex-style replenishing book reduce slippage on the same historical flow,
2. what completion penalty appears when that book is capacity-constrained,
3. whether a study-owned hybrid design can recover completion without surrendering the slippage advantage, and
4. how those results should be framed against the published Lambdaplex benchmark panel without over-claiming methodological parity.

## Claim boundary

This is an **event-level historical replay study**, not a product-fidelity simulator for deployed SaucerSwap V3.

The study compares four surfaces:

- **V2 baseline** — realized SaucerSwap V2 WHBAR/USDC 0.15% execution from the historical replay set
- **3A pure-book** — a study-owned replenishing synthetic book using Lambdaplex-style first-pass assumptions
- **3B hybrid** — a study-owned hybrid lane: 3A fill first, then residual V2 backstop only when the frozen admissibility rule passes
- **Lambdaplex published panel** — an external published benchmark, carried as provenance rather than falsely presented as a replay lane produced by this harness

Important limits:

- the replay unit is one trade row per replay unit
- 3A and 3B are synthetic study surfaces, not claims about exact production behavior
- 3A and 3B still carry `fees_paid = 0.0` because there is no grounded synthetic or blended fee model in this phase
- Lambdaplex remains **incomplete** under the local benchmark contract: the public panel provides partial slippage claims, but not enough completion / remainder / methodology detail to normalize the entire benchmark row

## Methodology

### Data surface

- market: `HBAR/USDC`
- source protocol: SaucerSwap V2 `0.15%`
- replay coverage: `7,255,957` event-level replay units
- row split in the study outputs: `3,770,999` buys and `3,484,958` sells

### Lane definitions

**V2 baseline**
- realized execution from the historical V2 flow under the event-level replay contract

**3A pure-book**
- six replenishing levels at `{2, 4, 8, 16, 32, 64}` bps
- level weights `{1, 1, 2, 3, 5, 8}`
- total synthetic grid liquidity: `$20,000`

**3B hybrid**
- mounted 3A fill first
- residual routing to V2 only when the frozen admissibility rule passes
- after RH-12, admissibility is evaluated on the projected **blended** execution price rather than the residual V2 leg in isolation

### Metric families

The report now carries two slippage families side by side.

**1. Canonical study metric**
- `avg_slippage_bps`
- external-reference study metric
- this remains the main study-owned slippage number

**2. Lambdaplex-parity proxy metric**
- `avg_amm_pre_trade_spot_gross_slippage_bps`
- locally reconstructed AMM pre-trade pool-spot gross slippage
- added after RH-13 showed that Lambdaplex’s published `15.47` bps figure is best matched by this denominator rather than our external-reference study metric

This parity proxy is a **best-supported comparison surface**, not confirmation of Lambdaplex’s undisclosed methodology.

### Interpretation rule for Lambdaplex

Use Lambdaplex in two distinct ways:

- as a **published benchmark panel** for provenance (`15.47` bps AMM slippage, `2.82` bps grid-strategy slippage)
- as a **competitor-facing slippage reference** only through the explicit parity-proxy metric

Do **not** treat Lambdaplex as fully comparable on fill rate, completion, or remainder, because those fields are still undisclosed in the published panel.

## Headline study results

### Core lane comparison

| Lane | Full-fill rate | Avg completion | Remainder (HBAR) | Avg study slippage (bps) | Avg parity proxy slippage (bps) |
| --- | --- | --- | --- | --- | --- |
| V2 baseline | `1.0000` | `1.0000` | `0` | `19.9669` | `15.4723` |
| 3A pure-book | `0.9821` | `0.9998` | `431.585M` | `2.2618` | `-2.1870` |
| 3B hybrid | `0.9895` | `0.9999` | `253.183M` | `2.2611` | `-2.1877` |

### What those numbers mean

- Relative to V2, both V3 study lanes dramatically reduce slippage.
- Relative to pure-book, hybrid materially improves completion and remainder while preserving essentially the same average slippage profile.
- Aggregate hybrid is slightly better than pure-book on both reported slippage families, while also filling more.

### Hybrid versus pure-book

On the aggregate replay set, hybrid improves on pure-book by:

- **full-fill rate:** `0.9821 -> 0.9895` (`+0.742` percentage points)
- **avg completion:** `0.999813 -> 0.999926`
- **remainder:** `431.585M -> 253.183M` HBAR (`-178.402M` HBAR)
- **partial fills:** `28,789 -> 1,114`

That is the clearest reason to prefer the hybrid lane as the main study result rather than pure-book alone.

## Large-clip result

The large-clip bucket remains the hardest surface in the study and is where RH-12 mattered most.

### `25k+` requested notional bucket

| Lane | Full-fill rate | Avg completion | Remainder (HBAR) | Avg study slippage (bps) | Avg parity proxy slippage (bps) |
| --- | --- | --- | --- | --- | --- |
| V2 baseline | `1.0000` | `1.0000` | `0` | `57.8403` | `69.2242` |
| 3A pure-book | `0.4216` | `0.5213` | `418.339M` | `37.1643` | `49.2140` |
| 3B hybrid | `0.6511` | `0.7980` | `252.372M` | `35.3004` | `47.2720` |

Interpretation:

- pure-book is still too capacity-constrained on the largest clips
- hybrid does **not** reach V2 completion parity on `25k+`, but it materially improves over pure-book
- hybrid reduces `25k+` remainder by roughly **165.97M HBAR** versus pure-book while also improving slippage

## Money saved / slippage-cost framing

A colleague-facing report should include money-saved framing, but it needs to be defined carefully.

The cleanest version is:

- compute implied slippage cost on **filled notional**, and
- present the result as **USDC cost per $1M filled notional**

That avoids confusing slippage quality with completion volume.

### Slippage-cost intensity per $1M filled

| Lane | Study metric cost / $1M filled (USDC) | Parity-proxy cost / $1M filled (USDC) |
| --- | --- | --- |
| V2 baseline | `2,440.77` | `2,051.39` |
| 3A pure-book | `473.38` | `-38.84` |
| 3B hybrid | `497.13` | `-0.50` |

Interpretation:

- On the canonical study metric, both V3 lanes reduce slippage cost intensity by about **$1.94k–$1.97k per $1M filled** versus V2.
- On the parity-proxy metric, both V3 lanes are effectively at or inside the pre-trade AMM spot, which is why the parity-proxy cost becomes near-zero or negative.
- Negative parity-proxy cost should be read as **price improvement relative to the pre-trade AMM spot**, not as a literal trading rebate.

### Total implied slippage cost on realized filled volume

| Lane | Filled notional (USDC) | Study slippage cost (USDC) | Parity-proxy slippage cost (USDC) |
| --- | --- | --- | --- |
| V2 baseline | `3.929B` | `9.589M` | `8.059M` |
| 3A pure-book | `3.851B` | `1.823M` | `-0.150M` |
| 3B hybrid | `3.885B` | `1.932M` | `-0.002M` |

Important caveat: this total-cost view mixes **price quality** and **completion**. That is why the report should always present it alongside full-fill rate, avg completion, and remainder.

## Lambdaplex comparison

### What we can say confidently

- Lambdaplex’s published panel reports:
  - **average AMM slippage:** `15.47` bps
  - **grid strategy slippage:** `2.82` bps
- RH-13 showed that our own V2 baseline lands at **`15.4723` bps** when re-scored on the locally reconstructable AMM pre-trade spot gross convention.

That is strong evidence that the Lambdaplex `15.47` number is being expressed on the same general denominator as the new parity-proxy metric, not on our canonical external-reference study metric.

### What we cannot say confidently

We still cannot claim full apples-to-apples parity with Lambdaplex on:

- fill rate
- avg completion
- remainder / unfilled size
- average absolute slippage
- weighting basis
- fee treatment
- failure / partial-fill treatment

Those fields are not disclosed in the published panel.

### Practical competitor-facing read

The clean competitor-facing read is:

- **V2 baseline parity proxy:** `15.4723` bps
- **Lambdaplex published AMM slippage:** `15.47` bps
- **3A pure-book parity proxy:** `-2.1870` bps
- **3B hybrid parity proxy:** `-2.1877` bps

So the report can honestly say:

1. our parity-proxy denominator now aligns with the Lambdaplex AMM claim,
2. both V3 study lanes are far better than the current V2 pool on that parity surface, and
3. hybrid is the better overall internal result because it preserves the price advantage while materially improving completion versus pure-book.

It should **not** say that Lambdaplex is fully normalized into the same schema across every metric.

## Recommended presentation to colleagues

Lead with three points:

1. **V3-style execution clearly improves price quality versus V2.**
2. **Pure-book alone is not enough for large clips; hybrid is the better overall design surface.**
3. **Lambdaplex can now be compared on a better slippage denominator, but only as a parity-proxy comparison, not a fully normalized benchmark row.**

## Future studies

This report should be read as a completed **counterfactual replay study**, not as the final word on production-faithful on-chain order-book behavior.

The most useful next studies, if fidelity needs to increase later, are:

1. **Fee-aware overlay rerun**
   - Apply explicit V3 book fees and maker economics to `3A` and `3B` as a reporting-layer overlay.
   - Recompute net slippage and all-in trader-cost tables without changing the current completion logic.
   - This is the cleanest next step if the goal is to understand how much the current report moves once realistic fees are included.

2. **Fee-aware hybrid admissibility**
   - Re-test `3B` with fee-inclusive blended execution in the admissibility rule.
   - This would answer whether realistic fees alter routing decisions, completion, and large-clip behavior rather than just post-trade cost reporting.

3. **Production-faithful order-book simulation**
   - Replace the replenishing synthetic-book assumption with a closer reconstruction of live on-chain order-book behavior.
   - That would likely require historical order placement, cancellation, replacement, persistence, queue-priority, and matching-semantics data, plus more exact fee and timing semantics.
   - It would also require a closer recovery of order-level admissibility / routing behavior than the current study-owned proxy.

4. **Engineering validation pack**
   - Add golden examples or canonical truth cases from engineering so the simulation can be validated against known matcher outcomes rather than only against replay-surface consistency checks.

Why this matters:
- The current study already answers the first-order strategic question: a V3-style surface appears materially better than the current V2 WHBAR/USDC pool, and the hybrid lane is the best overall study result.
- What future work would improve is not the existence of that directional signal, but the confidence with which the study can be interpreted as a proxy for live deployed order-book behavior.

## Supporting repo outputs

Tracked reports for sharing in the repo:

- `reports/final-study-report.md` — this authored colleague-facing memo
- `reports/final-comparison.md` — refreshed machine-readable comparison pack summary
- `reports/validation.md` — refreshed validation output
- `reports/reconciliation.md` — mounted artifact reconciliation

Benchmark provenance:

- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`

## Final conclusion

The study is ready to share.

The strongest defensible conclusion is not “pure-book wins” and not “V2 is fine as-is.” It is:

> A V3-style execution surface appears materially better than the current WHBAR/USDC V2 pool on slippage, and the study-owned hybrid lane is the best overall result because it preserves the slippage advantage while materially improving completion and remainder versus pure-book. Lambdaplex remains useful as an external benchmark, but only on an explicitly labeled parity-proxy slippage basis rather than as a fully normalized apples-to-apples benchmark row.

# Reviewer memo — `0b302a9`

## Scope
RH-06 adds the first real 3B hybrid lane on top of the mounted RH-05 pure-book outputs and RH-04 realized V2 baseline.

## What changed
- Turns the earlier hybrid toy surface into a runnable lane with deterministic input alignment, residual-size routing, admissibility-rule enforcement, CLI/Make wiring, materialized outputs, stronger tests, and an artifact index.
- Expands the admissibility surface so the frozen hybrid rule is explicit, configurable, and testable.

## What looks good
- Mapping stays one replay unit -> one hybrid row, with anchor preservation and hard-fail alignment checks.
- Hybrid completion is not silently forced to `1.0`; unrouted residual remains explicit.
- Route breakdown and admissibility outcomes are persisted, which makes the backstop behavior auditable.
- Fee treatment remains explicit instead of fabricated.

## Main implementation risk
- The hybrid output is very large, and the normal path depends on mounted upstream artifacts. Reviewers should pay attention to rerun ergonomics, I/O cost, and any assumptions about mounted artifact integrity.

## Main modeling caveat
- This is still a study-owned event-level hybrid surface, not a reconstruction of canonical V3 behavior or recovered multi-event user intent. Residual means the event-level remainder after mounted 3A fill.

## Suggested review focus
- `sim/hybrid.py` alignment logic and residual routing math
- `rules/admissibility.py` rule loading / pass-fail gating
- summary / manifest caveat surfaces and route-breakdown persistence

-- Live-aligned template for V2 swap metadata / auxiliary fields.
-- Verified against Metabase/SaucerSwap MySQL on 2026-03-24.

SELECT
  sm.id AS metadataRowId,
  sm.swap_id,
  sm.source,
  se.contractId,
  se.timestampSeconds,
  se.sender,
  se.recipient,
  se.amountA,
  se.amountB,
  se.sqrtRatioX96,
  se.liquidity,
  se.tick
FROM v2_swap_metadata sm
JOIN swap_events se
  ON se.id = sm.swap_id
WHERE se.contractId = '0.0.3964804'
ORDER BY se.timestampSeconds, sm.swap_id, sm.id;

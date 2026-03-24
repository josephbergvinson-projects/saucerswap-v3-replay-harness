-- Live-aligned extraction template for HBAR/USDC V2 0.15% historical trade flow.
-- Verified against Metabase/SaucerSwap MySQL on 2026-03-24.
-- Note: the exposed schema does not currently show transaction-hash or log-order fields,
-- so this extract preserves the best event-level fields currently visible.

SELECT
  tdv2.id AS tradeRowId,
  tdv2.swapEventId,
  tdv2.poolId AS poolContractId,
  tdv2.timestampSeconds AS tradeTimestampSeconds,
  tdv2.baseId,
  tdv2.targetId,
  tdv2.baseVolume,
  tdv2.targetVolume,
  tdv2.price,
  tdv2.type,
  se.contractId,
  se.sender,
  se.recipient,
  se.amountA,
  se.amountB,
  se.sqrtRatioX96,
  se.liquidity,
  se.tick,
  se.timestampSeconds AS swapEventTimestampSeconds,
  sm.source AS swapSource
FROM trade_data_v2 tdv2
LEFT JOIN swap_events se
  ON se.id = tdv2.swapEventId
LEFT JOIN v2_swap_metadata sm
  ON sm.swap_id = tdv2.swapEventId
WHERE tdv2.poolId = '0.0.3964804'
ORDER BY tdv2.timestampSeconds, tdv2.swapEventId, tdv2.id;

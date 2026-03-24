-- Draft extraction template for HBAR/USDC V2 0.15% historical flow.
-- Adjust concrete column names to match Gigabrain schema before first live run.

SELECT
  tdv2.id,
  tdv2.poolId,
  tdv2.transactionHash,
  tdv2.consensusTimestamp,
  tdv2.eventIndex,
  tdv2.sender,
  tdv2.amount0In,
  tdv2.amount1In,
  tdv2.amount0Out,
  tdv2.amount1Out,
  tdv2.reserve0,
  tdv2.reserve1
FROM trade_data_v2 tdv2
JOIN pools_v2 p ON p.poolId = tdv2.poolId
WHERE p.id = 9
ORDER BY tdv2.consensusTimestamp, tdv2.eventIndex;

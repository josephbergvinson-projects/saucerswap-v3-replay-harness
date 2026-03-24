-- Live-aligned template for first-pass pool reference pricing.
-- Verified against Metabase/SaucerSwap MySQL on 2026-03-24.
-- The study-owned first-pass reference source is the pool-level minute price series.

SELECT
  id,
  poolId,
  timestampSeconds,
  price
FROM pools_v2_prices_minute
WHERE poolId = 9
ORDER BY timestampSeconds;

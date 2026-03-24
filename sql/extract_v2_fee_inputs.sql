-- Live-aligned template for fee-related source fields.
-- Verified against Metabase/SaucerSwap MySQL on 2026-03-24.

SELECT
  id,
  poolVersion,
  poolId,
  timestampSeconds,
  fee,
  feeUsd,
  feeSaucerswapUi,
  feeSaucerswapUiUsd,
  feeSaucerswapApp,
  feeSaucerswapAppUsd,
  feeHashpack,
  feeHashpackUsd,
  feeKabilia,
  feeKabiliaUsd,
  feeBlade,
  feeBladeUsd,
  feeEtaSwap,
  feeEtaSwapUsd,
  feeSaucerswapAppAndroid,
  feeSaucerswapAppAndroidUsd
FROM pool_fees_day
WHERE poolId = 9
ORDER BY timestampSeconds;

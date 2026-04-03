#!/opt/homebrew/bin/node
const { execFileSync } = require('node:child_process');
const { cpSync, createReadStream, createWriteStream, existsSync, mkdirSync, mkdtempSync, rmSync, statSync, writeFileSync } = require('node:fs');
const { open } = require('node:fs/promises');
const { Readable } = require('node:stream');
const { tmpdir } = require('node:os');
const { join, dirname } = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');

const REPO = '/Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh02-gigabrain-probe';
const RAW_DIR = join(REPO, 'data', 'raw', 'gigabrain');
const RUN_DIR = join(REPO, 'runs', 'rh02b-metabase-export-20260324');
const CHUNKS_DIR = join(RUN_DIR, 'chunks');
const METABASE_HOST = 'gigabrain.saucerswap.finance';
const METABASE_BASE = `https://${METABASE_HOST}`;
const COOKIE_DB = '/Users/openclaw/Library/Application Support/Google/Chrome/Default/Cookies';

function mkdirp(path) { mkdirSync(path, { recursive: true }); }

function sqliteValue(dbPath, sql) {
  return execFileSync('/usr/bin/sqlite3', [dbPath, sql], { encoding: 'utf8' }).trim();
}

function copyCookieDb(dbPath) {
  const tmp = mkdtempSync(join(tmpdir(), 'rh02b-cookie-db-'));
  const copy = join(tmp, 'Cookies');
  cpSync(dbPath, copy);

  for (const suffix of ['-wal', '-shm']) {
    const sibling = `${dbPath}${suffix}`;
    if (existsSync(sibling)) {
      cpSync(sibling, `${copy}${suffix}`);
    }
  }

  return { tmp, copy };
}

function getChromeSafeStoragePassword() {
  return execFileSync('security', ['find-generic-password', '-w', '-a', 'Chrome', '-s', 'Chrome Safe Storage'], { encoding: 'utf8' }).trim();
}

function getCookieValue(name) {
  const { tmp, copy } = copyCookieDb(COOKIE_DB);
  try {
    const metaVersion = Number(sqliteValue(copy, "select value from meta where key='version' limit 1;")) || 0;
    const hex = sqliteValue(copy, `select hex(encrypted_value) from cookies where host_key = '${METABASE_HOST}' and name = '${name}' order by creation_utc desc limit 1;`);
    if (!hex) throw new Error(`Cookie ${name} not found for ${METABASE_HOST}`);
    const encrypted = Buffer.from(hex, 'hex');
    const payload = encrypted.subarray(3); // drop v10 prefix
    const key = crypto.pbkdf2Sync(Buffer.from(getChromeSafeStoragePassword(), 'utf8'), Buffer.from('saltysalt', 'utf8'), 1003, 16, 'sha1');
    const iv = Buffer.alloc(16, 0x20);
    const decipher = crypto.createDecipheriv('aes-128-cbc', key, iv);
    const decrypted = Buffer.concat([decipher.update(payload), decipher.final()]);
    const value = metaVersion >= 24 ? decrypted.subarray(32).toString('utf8') : decrypted.toString('utf8');
    return value;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

function metabaseHeaders(extra = {}) {
  const session = getCookieValue('metabase.SESSION');
  const device = getCookieValue('metabase.DEVICE');
  return {
    'Cookie': `metabase.SESSION=${session}; metabase.DEVICE=${device}`,
    ...extra,
  };
}

function buildQuery(sql) {
  return {
    database: 2,
    type: 'native',
    native: { query: sql },
    middleware: {
      'js-int-to-string?': true,
      'userland-query?': true,
      'add-default-userland-constraints?': true,
    },
  };
}

async function fetchCsvToFile(sql, outPath) {
  mkdirp(dirname(outPath));
  const params = new URLSearchParams();
  params.set('query', JSON.stringify(buildQuery(sql)));
  params.set('visualization_settings', JSON.stringify({}));
  params.set('format_rows', 'true');
  params.set('pivot_results', 'false');
  const res = await fetch(`${METABASE_BASE}/api/dataset/csv`, {
    method: 'POST',
    headers: metabaseHeaders({
      'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
      'accept': 'text/csv,*/*',
    }),
    body: params.toString(),
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '');
    throw new Error(`CSV export failed (${res.status}): ${text.slice(0, 500)}`);
  }
  const tmpOut = `${outPath}.tmp`;
  const ws = createWriteStream(tmpOut, { encoding: 'utf8' });
  await new Promise((resolve, reject) => {
    Readable.fromWeb(res.body).pipe(ws);
    res.body.on?.('error', reject);
    ws.on('finish', resolve);
    ws.on('error', reject);
  });
  rmSync(outPath, { force: true });
  execFileSync('/bin/mv', [tmpOut, outPath]);
}

async function appendCsvSkippingHeader(sourcePath, targetPath, includeHeader) {
  const ws = createWriteStream(targetPath, { flags: includeHeader ? 'w' : 'a', encoding: 'utf8' });
  const rl = readline.createInterface({ input: createReadStream(sourcePath, { encoding: 'utf8' }), crlfDelay: Infinity });
  let first = true;
  for await (const line of rl) {
    if (!includeHeader && first) {
      first = false;
      continue;
    }
    first = false;
    ws.write(line + '\n');
  }
  await new Promise((resolve, reject) => {
    ws.end(resolve);
    ws.on('error', reject);
  });
}

function monthRanges(minTs, maxTs) {
  const ranges = [];
  let current = new Date(minTs * 1000);
  current = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth(), 1, 0, 0, 0));
  const maxDate = new Date(maxTs * 1000);
  while (current.getTime() / 1000 <= maxTs) {
    const next = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + 1, 1, 0, 0, 0));
    ranges.push({
      label: `${current.getUTCFullYear()}-${String(current.getUTCMonth() + 1).padStart(2, '0')}`,
      start: Math.floor(current.getTime() / 1000),
      end: Math.floor(next.getTime() / 1000),
    });
    current = next;
    if (current > maxDate && current.getUTCDate() === 1) break;
  }
  return ranges;
}

async function exportChunked(spec) {
  const chunkDir = join(CHUNKS_DIR, spec.name);
  mkdirp(chunkDir);
  const finalPath = join(RAW_DIR, spec.outputFile);
  const parts = [];
  const exactMaxExclusive = spec.maxTs + 1;
  for (const range of monthRanges(spec.minTs, spec.maxTs)) {
    const partPath = join(chunkDir, `${range.label}.csv`);
    parts.push(partPath);
    const effectiveStart = Math.max(range.start, spec.minTs);
    const effectiveEnd = Math.min(range.end, exactMaxExclusive);
    if (!existsSync(partPath) || statSync(partPath).size === 0) {
      const sql = spec.sql(effectiveStart, effectiveEnd);
      console.log(`Exporting ${spec.name} ${range.label}`);
      await fetchCsvToFile(sql, partPath);
    } else {
      console.log(`Reusing existing chunk ${spec.name} ${range.label}`);
    }
  }
  let first = true;
  for (const part of parts) {
    await appendCsvSkippingHeader(part, finalPath, first);
    first = false;
  }
  return finalPath;
}

async function exportSingle(spec) {
  const finalPath = join(RAW_DIR, spec.outputFile);
  console.log(`Exporting ${spec.name}`);
  await fetchCsvToFile(spec.sql(), finalPath);
  return finalPath;
}

async function sha256File(path) {
  const hash = crypto.createHash('sha256');
  const rs = createReadStream(path);
  for await (const chunk of rs) hash.update(chunk);
  return hash.digest('hex');
}

async function countLines(path) {
  let count = 0;
  const rl = readline.createInterface({ input: createReadStream(path, { encoding: 'utf8' }), crlfDelay: Infinity });
  for await (const _ of rl) count += 1;
  return count;
}

async function buildSummary(paths) {
  const out = {};
  for (const [name, path] of Object.entries(paths)) {
    const lines = await countLines(path);
    out[name] = {
      path,
      bytes: statSync(path).size,
      lines,
      rows: Math.max(lines - 1, 0),
      sha256: await sha256File(path),
    };
  }
  return out;
}

async function main() {
  mkdirp(RAW_DIR);
  mkdirp(RUN_DIR);
  mkdirp(CHUNKS_DIR);

  const specs = {
    swap_metadata: {
      name: 'swap_metadata',
      outputFile: 'hbar_usdc_v2_015_swap_metadata.csv',
      sql: () => `SELECT sm.id AS metadataRowId, sm.swap_id, sm.source, se.contractId, se.timestampSeconds, se.sender, se.recipient, se.amountA, se.amountB, se.sqrtRatioX96, se.liquidity, se.tick FROM v2_swap_metadata sm JOIN swap_events se ON se.id = sm.swap_id WHERE se.contractId = '0.0.3964804' ORDER BY se.timestampSeconds, sm.swap_id, sm.id`,
    },
    fee_inputs: {
      name: 'fee_inputs',
      outputFile: 'v2_fee_inputs.csv',
      sql: () => `SELECT id, poolVersion, poolId, timestampSeconds, fee, feeUsd, feeSaucerswapUi, feeSaucerswapUiUsd, feeSaucerswapApp, feeSaucerswapAppUsd, feeHashpack, feeHashpackUsd, feeKabilia, feeKabiliaUsd, feeBlade, feeBladeUsd, feeEtaSwap, feeEtaSwapUsd, feeSaucerswapAppAndroid, feeSaucerswapAppAndroidUsd FROM pool_fees_day WHERE poolId = 9 ORDER BY timestampSeconds`,
    },
    reference_prices: {
      name: 'reference_prices',
      outputFile: 'hbar_reference_prices.csv',
      minTs: 1700239200,
      maxTs: 1774363860,
      sql: (start, end) => `SELECT id, poolId, timestampSeconds, price FROM pools_v2_prices_minute WHERE poolId = 9 AND timestampSeconds >= ${start} AND timestampSeconds < ${end} ORDER BY timestampSeconds`,
    },
    trades: {
      name: 'trades',
      outputFile: 'hbar_usdc_v2_015_trades.csv',
      minTs: 1700264033,
      maxTs: 1774363967,
      sql: (start, end) => `SELECT tdv2.id AS tradeRowId, tdv2.swapEventId, tdv2.poolId AS poolContractId, tdv2.timestampSeconds AS tradeTimestampSeconds, tdv2.baseId, tdv2.targetId, tdv2.baseVolume, tdv2.targetVolume, tdv2.price, tdv2.type, se.contractId, se.sender, se.recipient, se.amountA, se.amountB, se.sqrtRatioX96, se.liquidity, se.tick, se.timestampSeconds AS swapEventTimestampSeconds, sm.source AS swapSource FROM trade_data_v2 tdv2 LEFT JOIN swap_events se ON se.id = tdv2.swapEventId LEFT JOIN v2_swap_metadata sm ON sm.swap_id = tdv2.swapEventId WHERE tdv2.poolId = '0.0.3964804' AND tdv2.timestampSeconds >= ${start} AND tdv2.timestampSeconds < ${end} ORDER BY tdv2.timestampSeconds, tdv2.swapEventId, tdv2.id`,
    },
  };

  const outputs = {};
  outputs.swap_metadata = await exportSingle(specs.swap_metadata);
  outputs.fee_inputs = await exportSingle(specs.fee_inputs);
  outputs.reference_prices = await exportChunked(specs.reference_prices);
  outputs.trades = await exportChunked(specs.trades);

  const summary = await buildSummary(outputs);
  const summaryPath = join(RUN_DIR, 'export-summary.json');
  writeFileSync(summaryPath, JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});

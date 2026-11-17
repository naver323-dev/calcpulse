/**
 * Arithmetic tests for the P1 calculators. Runs on Node's built-in TypeScript
 * stripping, no test framework needed:
 *
 *   node scripts/test_calculations.ts
 *
 * The assertions are hand-computed expectations, not the output of the code, so a
 * change in the formula has to be justified here as well as in the page prose.
 */
import assert from 'node:assert/strict';
import { computeApiCost, computeSaasRoi } from '../src/lib/calculations.ts';

let passed = 0;
const check = (name: string, fn: () => void) => {
  fn();
  passed += 1;
  console.log(`  ok  ${name}`);
};

const close = (actual: number, expected: number, label: string, tolerance = 1e-9) => {
  const delta = Math.abs(actual - expected);
  assert.ok(
    delta <= tolerance,
    `${label}: expected ${expected}, got ${actual} (delta ${delta})`,
  );
};

console.log('computeApiCost');

check('flat case with no cache and no retries', () => {
  // 1,000 requests/day × 30 = 30,000 calls.
  // Input: 30,000 × 1,000 tok = 30M tok @ $0.15/M = $4.50
  // Output: 30,000 × 500 tok = 15M tok @ $0.60/M = $9.00
  const result = computeApiCost({
    requestsPerDay: 1000,
    daysPerMonth: 30,
    inputTokens: 1000,
    outputTokens: 500,
    inputPricePerMillion: 0.15,
    outputPricePerMillion: 0.6,
    cacheHitRate: 0,
    cachedPricePerMillion: 0.015,
    retryRate: 0,
  });
  close(result.billedCalls, 30_000, 'billed calls');
  close(result.freshInputCost, (30_000 * 1000 * 0.15) / 1e6, 'fresh input cost');
  close(result.cachedInputCost, 0, 'cached input cost');
  close(result.outputCost, (30_000 * 500 * 0.6) / 1e6, 'output cost');
  close(result.monthlyTotal, 13.5, 'monthly total');
  close(result.perRequest, 13.5 / 30_000, 'per request');
  close(result.perThousandRequests, (13.5 / 30_000) * 1000, 'per 1k');
});

check('retry overhead is charged on the token bill, not on a rounded base', () => {
  const result = computeApiCost({
    requestsPerDay: 1000,
    daysPerMonth: 30,
    inputTokens: 1000,
    outputTokens: 500,
    inputPricePerMillion: 0.15,
    outputPricePerMillion: 0.6,
    cacheHitRate: 0,
    cachedPricePerMillion: 0,
    retryRate: 0.1,
  });
  close(result.billedCalls, 33_000, 'billed calls');
  // base token cost 13.50, retries add 10%
  close(result.retryCost, 1.35, 'retry cost');
  close(result.monthlyTotal, 14.85, 'monthly total');
});

check('cache splits input tokens between fresh and cached prices', () => {
  const result = computeApiCost({
    requestsPerDay: 1000,
    daysPerMonth: 30,
    inputTokens: 1000,
    outputTokens: 500,
    inputPricePerMillion: 1,
    outputPricePerMillion: 0,
    cacheHitRate: 0.6,
    cachedPricePerMillion: 0.1,
    retryRate: 0,
  });
  // 30,000 calls × 400 fresh tok × $1/M = $12; × 600 cached tok × $0.1/M = $1.8
  close(result.freshInputCost, 12, 'fresh input');
  close(result.cachedInputCost, 1.8, 'cached input');
  close(result.monthlyTotal, 13.8, 'total');
});

check('zero traffic yields zero cost and no division by zero', () => {
  const result = computeApiCost({
    requestsPerDay: 0,
    daysPerMonth: 30,
    inputTokens: 1000,
    outputTokens: 500,
    inputPricePerMillion: 0.15,
    outputPricePerMillion: 0.6,
    cacheHitRate: 0.5,
    cachedPricePerMillion: 0.015,
    retryRate: 0.05,
  });
  close(result.monthlyTotal, 0, 'total');
  close(result.perRequest, 0, 'per request');
  assert.ok(Number.isFinite(result.perThousandRequests), 'per 1k must be finite');
});

check('negative and NaN inputs fall back instead of poisoning the total', () => {
  const result = computeApiCost({
    requestsPerDay: Number.NaN,
    daysPerMonth: 0,
    inputTokens: -5,
    outputTokens: 100,
    inputPricePerMillion: 0.15,
    outputPricePerMillion: 0.6,
    cacheHitRate: 2,
    cachedPricePerMillion: 0.015,
    retryRate: -1,
  });
  assert.ok(Number.isFinite(result.monthlyTotal), 'total must be finite');
  assert.ok(result.monthlyTotal >= 0, 'total must not be negative');
});

console.log('computeSaasRoi');

check('straight payback: one-off cost divided by monthly net', () => {
  // 10 seats × $25 = $250/mo. 10 × 70% = 7 used seats × 4h × $40 = $1,120/mo value.
  // Net 870/mo. One-off 1,500 → 1.72 months.
  const result = computeSaasRoi({
    seats: 10,
    pricePerSeat: 25,
    oneOffCost: 1500,
    hoursSavedPerSeat: 4,
    hourlyRate: 40,
    adoptionRate: 0.7,
  });
  close(result.monthlySubscription, 250, 'subscription');
  close(result.usedSeats, 7, 'used seats');
  close(result.monthlyValue, 1120, 'value');
  close(result.netMonthly, 870, 'net monthly');
  close(result.paybackMonths ?? -1, 1500 / 870, 'payback months');
  close(result.value12, 13_440, 'value 12m');
  close(result.spend12, 4500, 'spend 12m');
  close(result.net12, 8940, 'net 12m');
  close(result.roiPercent ?? -1, (8940 / 4500) * 100, 'roi percent');
});

check('no one-off cost pays back immediately', () => {
  const result = computeSaasRoi({
    seats: 5,
    pricePerSeat: 10,
    oneOffCost: 0,
    hoursSavedPerSeat: 3,
    hourlyRate: 50,
    adoptionRate: 1,
  });
  close(result.paybackMonths ?? -1, 0, 'payback months');
});

check('negative net monthly has no payback', () => {
  const result = computeSaasRoi({
    seats: 50,
    pricePerSeat: 40,
    oneOffCost: 2000,
    hoursSavedPerSeat: 1,
    hourlyRate: 30,
    adoptionRate: 0.2,
  });
  assert.equal(result.paybackMonths, null, 'payback must be null');
  assert.ok(result.netMonthly < 0, 'net must be negative');
  assert.equal(result.breakEvenUsedSeats !== null, true, 'break-even seats still computable');
});

check('zero adoption still returns finite numbers', () => {
  const result = computeSaasRoi({
    seats: 20,
    pricePerSeat: 15,
    oneOffCost: 0,
    hoursSavedPerSeat: 2,
    hourlyRate: 45,
    adoptionRate: 0,
  });
  close(result.monthlyValue, 0, 'value');
  close(result.netMonthly, -300, 'net');
  assert.equal(result.paybackMonths, null, 'no payback');
  assert.ok(Number.isFinite(result.net12), 'net12 finite');
});

check('break-even used seats equals subscription divided by value per seat', () => {
  const result = computeSaasRoi({
    seats: 10,
    pricePerSeat: 25,
    oneOffCost: 0,
    hoursSavedPerSeat: 4,
    hourlyRate: 40,
    adoptionRate: 0.7,
  });
  // 250 / (4 h × $40) = 1.5625 used seats
  close(result.breakEvenUsedSeats ?? -1, 250 / 160, 'break-even used seats');
});

console.log(`\n${passed} checks passed`);

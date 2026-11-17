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
import { computeApiCost, computePaymentFees, computeSaasRoi } from '../src/lib/calculations.ts';

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

console.log('computePaymentFees');

check('flat case: percentage plus fixed fee on 1,000 charges', () => {
  // 1,000 × $40 = $40,000 gross; 5% refunded → $38,000 banked.
  // 2.9% of $40,000 = $1,160; 1,000 × $0.30 = $300; total $1,460.
  const result = computePaymentFees({
    transactionsPerMonth: 1000,
    averageSale: 40,
    percentFee: 0.029,
    fixedFee: 0.3,
    refundRate: 0.05,
    platformFee: 0,
    refundedFeeReturnRate: 0,
  });
  close(result.grossVolume, 40000, 'gross');
  close(result.refundedVolume, 2000, 'refunded volume');
  close(result.netVolume, 38000, 'net volume');
  close(result.percentFees, 1160, 'percent fees');
  close(result.fixedFees, 300, 'fixed fees');
  close(result.totalFees, 1460, 'total fees');
  close(result.netRevenue, 36540, 'net revenue');
  close(result.effectiveRate, 0.0365, 'effective rate');
  close(result.feePerTransaction, 1.46, 'fee per transaction');
});

check('a monthly platform fee lands on top of the per-charge fees', () => {
  const result = computePaymentFees({
    transactionsPerMonth: 1000,
    averageSale: 40,
    percentFee: 0.029,
    fixedFee: 0.3,
    refundRate: 0.05,
    platformFee: 49,
    refundedFeeReturnRate: 0,
  });
  close(result.totalFees, 1509, 'total fees');
  close(result.netRevenue, 36491, 'net revenue');
  close(result.effectiveRate, 1509 / 40000, 'effective rate');
});

check('refunds do not return the percentage fee unless the processor says so', () => {
  const withoutReturn = computePaymentFees({
    transactionsPerMonth: 500,
    averageSale: 80,
    percentFee: 0.03,
    fixedFee: 0.25,
    refundRate: 0.2,
    platformFee: 0,
    refundedFeeReturnRate: 0,
  });
  // $40,000 gross, $8,000 refunded; the 3% on the refunded $8,000 ($240) stays paid.
  close(withoutReturn.lostFeeOnRefunds, 240, 'lost fee on refunds');
  close(withoutReturn.netVolume, 32000, 'net volume');

  const withReturn = computePaymentFees({
    transactionsPerMonth: 500,
    averageSale: 80,
    percentFee: 0.03,
    fixedFee: 0.25,
    refundRate: 0.2,
    platformFee: 0,
    refundedFeeReturnRate: 1,
  });
  close(withReturn.lostFeeOnRefunds, 0, 'nothing lost when the fee is returned');
});

check('zero charges yields zero rates and no division by zero', () => {
  const result = computePaymentFees({
    transactionsPerMonth: 0,
    averageSale: 0,
    percentFee: 0.029,
    fixedFee: 0.3,
    refundRate: 0.05,
    platformFee: 0,
    refundedFeeReturnRate: 0,
  });
  close(result.totalFees, 0, 'fees');
  close(result.effectiveRate, 0, 'rate');
  close(result.feePerTransaction, 0, 'per transaction');
});

check('negative and NaN inputs fall back to zero', () => {
  const result = computePaymentFees({
    transactionsPerMonth: -10,
    averageSale: Number.NaN,
    percentFee: 0.029,
    fixedFee: 0.3,
    refundRate: 0.05,
    platformFee: 0,
    refundedFeeReturnRate: 0,
  });
  close(result.grossVolume, 0, 'gross');
  close(result.netRevenue, 0, 'net');
});

console.log(`\n${passed} checks passed`);

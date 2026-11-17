/**
 * Pure calculation logic for the two P1 calculators.
 *
 * Kept out of the page markup so the arithmetic can be tested without a browser
 * (see scripts/test_calculations.ts). Every function takes numbers and returns
 * numbers; no DOM, no rounding to display strings.
 */

export interface ApiCostInput {
  requestsPerDay: number;
  daysPerMonth: number;
  inputTokens: number;
  outputTokens: number;
  /** USD per 1M fresh input tokens. */
  inputPricePerMillion: number;
  /** USD per 1M output tokens. */
  outputPricePerMillion: number;
  /** Share of input tokens served from cache, 0–1. */
  cacheHitRate: number;
  /** USD per 1M cached input tokens. */
  cachedPricePerMillion: number;
  /** Extra calls as a share of base calls, 0–1 (0.05 = 5%). */
  retryRate: number;
}

export interface ApiCostResult {
  billedCalls: number;
  freshInputCost: number;
  cachedInputCost: number;
  outputCost: number;
  retryCost: number;
  monthlyTotal: number;
  annualTotal: number;
  perRequest: number;
  perThousandRequests: number;
}

const safe = (value: number, fallback = 0): number =>
  Number.isFinite(value) && value >= 0 ? value : fallback;

export function computeApiCost(input: ApiCostInput): ApiCostResult {
  const requestsPerDay = safe(input.requestsPerDay);
  const daysPerMonth = safe(input.daysPerMonth, 30) || 30;
  const inputTokens = safe(input.inputTokens);
  const outputTokens = safe(input.outputTokens);
  const inputPrice = safe(input.inputPricePerMillion);
  const outputPrice = safe(input.outputPricePerMillion);
  const cacheHitRate = Math.min(1, Math.max(0, safe(input.cacheHitRate)));
  const cachedPrice = safe(input.cachedPricePerMillion);
  const retryRate = Math.max(0, safe(input.retryRate));

  const baseCalls = requestsPerDay * daysPerMonth;
  const billedCalls = baseCalls * (1 + retryRate);

  const freshInputTokens = inputTokens * (1 - cacheHitRate);
  const cachedInputTokens = inputTokens * cacheHitRate;

  // Line items are measured on the base traffic; retries are then charged as their
  // own line on top, so the four rows of the breakdown add up to the monthly total.
  const freshInputCost = (baseCalls * freshInputTokens * inputPrice) / 1_000_000;
  const cachedInputCost = (baseCalls * cachedInputTokens * cachedPrice) / 1_000_000;
  const outputCost = (baseCalls * outputTokens * outputPrice) / 1_000_000;

  const baseTotal = freshInputCost + cachedInputCost + outputCost;
  const retryCost = baseTotal * retryRate;
  const monthlyTotal = baseTotal + retryCost;

  const perRequest = billedCalls > 0 ? monthlyTotal / billedCalls : 0;

  return {
    billedCalls,
    freshInputCost,
    cachedInputCost,
    outputCost,
    retryCost,
    monthlyTotal,
    annualTotal: monthlyTotal * 12,
    perRequest,
    perThousandRequests: perRequest * 1000,
  };
}

export interface SaasRoiInput {
  seats: number;
  /** Subscription price per seat per month. */
  pricePerSeat: number;
  /** One-off cost: setup, migration, training. */
  oneOffCost: number;
  /** Hours saved per *used* seat per month. */
  hoursSavedPerSeat: number;
  /** Loaded cost of an hour. */
  hourlyRate: number;
  /** Share of paid seats that use the tool weekly, 0–1. */
  adoptionRate: number;
}

export interface SaasRoiResult {
  monthlySubscription: number;
  usedSeats: number;
  monthlyValue: number;
  netMonthly: number;
  /** Months until cumulative value covers one-off cost plus subscriptions paid. */
  paybackMonths: number | null;
  /** Used seats needed for monthly value to equal the subscription. */
  breakEvenUsedSeats: number | null;
  value12: number;
  subscriptions12: number;
  spend12: number;
  net12: number;
  roiPercent: number | null;
}

export function computeSaasRoi(input: SaasRoiInput): SaasRoiResult {
  const seats = Math.max(0, safe(input.seats));
  const pricePerSeat = safe(input.pricePerSeat);
  const oneOffCost = safe(input.oneOffCost);
  const hoursSavedPerSeat = safe(input.hoursSavedPerSeat);
  const hourlyRate = safe(input.hourlyRate);
  const adoptionRate = Math.min(1, Math.max(0, safe(input.adoptionRate)));

  const monthlySubscription = seats * pricePerSeat;
  const usedSeats = seats * adoptionRate;
  const monthlyValue = usedSeats * hoursSavedPerSeat * hourlyRate;
  const netMonthly = monthlyValue - monthlySubscription;

  const value12 = monthlyValue * 12;
  const subscriptions12 = monthlySubscription * 12;
  const spend12 = subscriptions12 + oneOffCost;
  const net12 = value12 - spend12;

  // Cumulative value minus cumulative subscriptions has to clear the one-off cost.
  const paybackMonths = netMonthly > 0 ? oneOffCost / netMonthly : null;

  const valuePerUsedSeat = hoursSavedPerSeat * hourlyRate;
  const breakEvenUsedSeats =
    valuePerUsedSeat > 0 ? monthlySubscription / valuePerUsedSeat : null;

  return {
    monthlySubscription,
    usedSeats,
    monthlyValue,
    netMonthly,
    paybackMonths,
    breakEvenUsedSeats,
    value12,
    subscriptions12,
    spend12,
    net12,
    roiPercent: spend12 > 0 ? (net12 / spend12) * 100 : null,
  };
}

export interface PaymentFeeInput {
  /** Charges per month. */
  transactionsPerMonth: number;
  /** Average sale in USD. */
  averageSale: number;
  /** Percentage fee, e.g. 0.029 for 2.9%. */
  percentFee: number;
  /** Fixed fee per charge in USD, e.g. 0.30. */
  fixedFee: number;
  /** Share of charges later refunded, 0–1. */
  refundRate: number;
  /** Flat monthly platform or account fee in USD. */
  platformFee: number;
  /** Share of the percentage fee the processor returns on a refund, 0–1. */
  refundedFeeReturnRate: number;
}

export interface PaymentFeeResult {
  grossVolume: number;
  refundedVolume: number;
  netVolume: number;
  percentFees: number;
  fixedFees: number;
  /** Percentage fee on refunded charges that the processor keeps. */
  lostFeeOnRefunds: number;
  platformFees: number;
  totalFees: number;
  netRevenue: number;
  /** totalFees ÷ grossVolume, as a share (0.0365 = 3.65%). */
  effectiveRate: number;
  feePerTransaction: number;
  netPerTransaction: number;
}

/**
 * What a payment processor keeps per month.
 *
 * The percentage fee is charged on the original charge and is not returned when the sale is
 * refunded, which is why refunds show up as a cost of their own rather than as a smaller
 * volume: the fixed fee is normally kept too unless the processor says otherwise.
 */
export function computePaymentFees(input: PaymentFeeInput): PaymentFeeResult {
  const transactions = Math.max(0, safe(input.transactionsPerMonth));
  const averageSale = safe(input.averageSale);
  const percentFee = Math.min(1, Math.max(0, safe(input.percentFee)));
  const fixedFee = safe(input.fixedFee);
  const refundRate = Math.min(1, Math.max(0, safe(input.refundRate)));
  const platformFee = safe(input.platformFee);
  const refundedFeeReturnRate = Math.min(1, Math.max(0, safe(input.refundedFeeReturnRate)));

  const grossVolume = transactions * averageSale;
  const refundedVolume = grossVolume * refundRate;
  const netVolume = grossVolume - refundedVolume;

  const percentFees = grossVolume * percentFee;
  const fixedFees = transactions * fixedFee;
  const lostFeeOnRefunds = refundedVolume * percentFee * (1 - refundedFeeReturnRate);
  const totalFees = percentFees + fixedFees + platformFee;

  const netRevenue = netVolume - totalFees;

  return {
    grossVolume,
    refundedVolume,
    netVolume,
    percentFees,
    fixedFees,
    lostFeeOnRefunds,
    platformFees: platformFee,
    totalFees,
    netRevenue,
    effectiveRate: grossVolume > 0 ? totalFees / grossVolume : 0,
    feePerTransaction: transactions > 0 ? totalFees / transactions : 0,
    netPerTransaction: transactions > 0 ? netRevenue / transactions : 0,
  };
}

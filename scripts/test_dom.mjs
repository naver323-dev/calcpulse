/**
 * Smoke test for the browser-side wiring of both calculators.
 *
 * The unit tests in scripts/test_calculations.ts prove the arithmetic. This test
 * proves the page actually connects the form to that arithmetic: it loads the built
 * bundle with a minimal DOM stub, fires an input event, and checks that the result
 * elements receive non-placeholder text.
 *
 *   npm run build && node scripts/test_dom.mjs
 */
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const astroDir = path.resolve('dist/_astro');

const findBundle = (prefix) => {
  const file = readdirSync(astroDir).find((name) => name.startsWith(prefix) && name.endsWith('.js'));
  assert.ok(file, `no built bundle found for ${prefix} in ${astroDir}`);
  return path.join(astroDir, file);
};

const makeElement = (value = '') => ({
  value,
  textContent: '',
  listeners: {},
  addEventListener(type, handler) {
    this.listeners[type] = handler;
  },
});

let runId = 0;

const runPage = async ({ bundlePrefix, inputs, outputs, description }) => {
  const elements = new Map();

  for (const [id, value] of Object.entries(inputs)) elements.set(id, makeElement(value));
  for (const id of outputs) elements.set(id, makeElement());

  const form = makeElement();
  elements.set(inputs.__formId, form);

  globalThis.document = {
    getElementById: (id) => elements.get(id) ?? null,
  };

  // Cache-bust: an ES module body runs once per URL, and each check needs a fresh run.
  runId += 1;
  await import(`${pathToFileURL(findBundle(bundlePrefix)).href}?run=${runId}`);

  assert.ok(form.listeners.input, 'form never registered an input listener');
  form.listeners.input({ type: 'input' });

  const text = (id) => elements.get(id).textContent;
  return { text, description };
};

let passed = 0;
const check = async (name, fn) => {
  await fn();
  passed += 1;
  console.log(`  ok  ${name}`);
};

await check('API cost calculator updates every result element', async () => {
  const { text } = await runPage({
    bundlePrefix: 'LlmApiCostCalculator',
    inputs: {
      __formId: 'api-cost-form',
      reqDay: '2000',
      days: '30',
      inTok: '1200',
      outTok: '400',
      inPrice: '0.15',
      outPrice: '0.6',
      cacheHit: '60',
      cachePrice: '0.015',
      retry: '5',
    },
    outputs: [
      'out-total',
      'out-annual',
      'out-per-req',
      'out-per-1k',
      'out-billed',
      'out-double',
      'row-in',
      'row-cache',
      'row-out',
      'row-retry',
      'share-in',
      'share-cache',
      'share-out',
      'share-retry',
    ],
    description: 'api',
  });

  // 2,000 requests/day × 30 = 60,000 calls, 5% retry → 63,000 billed calls.
  // Input split 40% fresh / 60% cached on 1,200 tokens; output 400 tokens.
  // fresh 28.8M × $0.15 = 4.32, cached 43.2M × $0.015 = 0.648, output 24M × $0.60 = 14.4
  // base 19.368 + 5% retry 0.9684 = 20.34
  assert.equal(text('out-total'), '$20.34');
  assert.equal(text('out-billed'), '63,000 billed calls');
  assert.match(text('out-per-req'), /^\$0\.0003/);
  assert.notEqual(text('row-out'), '$0.00');
  assert.notEqual(text('share-cache'), '—');
});

await check('SaaS calculator reports payback and verdict', async () => {
  const { text } = await runPage({
    bundlePrefix: 'SaasRoiCalculator',
    inputs: {
      __formId: 'roi-form',
      seats: '10',
      price: '25',
      setup: '1500',
      hours: '4',
      rate: '40',
      adoption: '70',
    },
    outputs: [
      'out-payback',
      'out-payback-note',
      'out-net',
      'out-monthly-cost',
      'out-roi',
      'out-year',
      'row-value',
      'row-subs',
      'row-setup',
      'row-net12',
      'verdict',
    ],
    description: 'roi',
  });

  // 10 × 70% = 7 used seats × 4h × $40 = $1,120/mo value, $250/mo subscription.
  // net 870 → payback 1,500 / 870 = 1.7 months. 12-month net = 13,440 − 4,500 = 8,940.
  assert.equal(text('out-payback'), '1.7 mo');
  assert.equal(text('out-net'), '$870');
  assert.equal(text('out-roi'), '+199%');
  assert.equal(text('row-net12'), '$8,940');
  assert.match(text('verdict'), /\$8,940 ahead after a year/);
});

await check('SaaS calculator says "Never" when the subscription outruns the saving', async () => {
  const { text } = await runPage({
    bundlePrefix: 'SaasRoiCalculator',
    inputs: {
      __formId: 'roi-form',
      seats: '50',
      price: '40',
      setup: '2000',
      hours: '1',
      rate: '30',
      adoption: '20',
    },
    outputs: ['out-payback', 'out-net', 'verdict'],
    description: 'roi-negative',
  });

  assert.equal(text('out-payback'), 'Never');
  assert.match(text('verdict'), /costs more per month/);
});

await check('Payment fee calculator reports fees, effective rate and net', async () => {
  const { text } = await runPage({
    bundlePrefix: 'PaymentFeeCalculator',
    inputs: {
      __formId: 'fee-form',
      txMonth: '1000',
      avgSale: '40',
      pctFee: '2.9',
      fixedFee: '0.30',
      refundRate: '5',
      platformFee: '0',
      feeReturn: '0',
    },
    outputs: [
      'out-fees',
      'out-gross',
      'out-net',
      'out-net-note',
      'out-rate',
      'out-per-tx',
      'row-pct',
      'row-fixed',
      'row-platform',
      'row-refund',
      'share-pct',
      'share-fixed',
      'share-platform',
    ],
    description: 'fee',
  });

  // 1,000 × $40 = $40,000; 2.9% = $1,160; 1,000 × $0.30 = $300; total $1,460 (3.65%).
  // 5% refunded = $2,000; net revenue $40,000 − $2,000 − $1,460 = $36,540.
  assert.equal(text('out-fees'), '$1,460.00');
  assert.equal(text('out-rate'), '3.65%');
  assert.equal(text('out-net'), '$36,540.00');
  assert.equal(text('out-per-tx'), '$1.46 per charge');
  assert.equal(text('row-pct'), '$1,160.00');
  assert.notEqual(text('share-pct'), '—');
});

await check('Seller fee comparison ranks platforms and fills every row', async () => {
  const ids = ['gr-direct', 'gr-discover', 'payhip', 'kofi', 'stripe', 'paypal'];
  const inputs = { __formId: 'seller-form', price: '14', sales: '50' };
  const pcts = { 'gr-direct': '12.9', 'gr-discover': '30', payhip: '7.9', kofi: '7.9', stripe: '2.9', paypal: '3.49' };
  const fixes = { 'gr-direct': '0.8', 'gr-discover': '0', payhip: '0.3', kofi: '0.3', stripe: '0.3', paypal: '0.49' };
  const outputs = ['out-best', 'out-spread'];
  for (const id of ids) {
    inputs[`pct-${id}`] = pcts[id];
    inputs[`fix-${id}`] = fixes[id];
    outputs.push(`fee-${id}`, `keep-${id}`, `rate-${id}`, `net-${id}`);
  }
  const { text } = await runPage({ bundlePrefix: 'SellerFeeCompare', inputs, outputs, description: 'seller' });

  // $14 at 12.9% + $0.80: fee 2.606, keep 11.394 (81.4%), net 569.70 over 50 sales.
  assert.equal(text('keep-gr-direct'), '$11.39');
  assert.equal(text('rate-gr-direct'), '81.4%');
  assert.equal(text('net-gr-direct'), '$569.70');
  assert.equal(text('net-gr-discover'), '$490.00');
  assert.equal(text('net-paypal'), '$651.07');
  assert.equal(text('net-stripe'), '$664.70');
  assert.match(text('out-best'), /Your own page with Stripe: \$664\.70 a month/);
  assert.match(text('out-spread'), /\$174\.70 a month/);
});

console.log(`\n${passed} DOM checks passed`);

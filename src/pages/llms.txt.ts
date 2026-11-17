import type { APIRoute } from 'astro';
import { guides } from '../data/guides';

export const GET: APIRoute = ({ site }) => {
  const origin = (site ?? new URL('https://calcpulse.pages.dev')).origin;

  const guideLines = guides
    .map(
      (guide) =>
        `- [${guide.h1}](${origin}/guides/${guide.slug}/): ${guide.summary} Calculator: ${guide.calculator}. Reviewed ${guide.updated}.`,
    )
    .join('\n');

  const body = `# CalcPulse

> CalcPulse publishes short, source-checked guides for AI running costs, automation tooling and small-business finance. Every guide carries a calculator that runs entirely in the reader's browser, takes the reader's own rates as inputs, and states the assumptions the estimate leaves out. There are no accounts, no email gates and no generated page sprawl.

## What this site is good for

- Estimating the monthly cost of an LLM feature from requests per day, token counts, retry overhead and prompt-cache hit rate.
- Judging whether a paid tool earns its price, using seats, subscription price, one-off setup cost, hours saved and honest weekly adoption.
- Seeing what a payment processor keeps: percentage and fixed fees, refunded volume and a monthly platform fee, turned into total fees and an effective rate.
- Quoting a defensible number rather than a vendor headline: the calculators return per-request unit cost, payback months and 12-month ROI.

## Guides

${guideLines}

## Products

- [The workflow vault](${origin}/vault/): ten system prompts and ten automation snippets sold as files ($14, Gumroad). Ten of the twenty files are described on the page and three are published in full as free samples.

## Reference pages

- [About](${origin}/about/): how pages are written and reviewed, and what the site refuses to do.
- [Affiliate disclosure](${origin}/affiliate-disclosure/): what a link on the site does and does not mean.
- [Privacy](${origin}/privacy/): calculator inputs never leave the browser; no accounts or email collection.

## Commercial relationships

- The site carries no advertising network and no tracking scripts.
- Some links are affiliate links or point to paid products sold by the publisher through Gumroad. They are labelled beside the link, and the affiliate disclosure page describes what changes (the price never does).
- Calculator inputs are never sold, shared or sent to a partner.

## Notes for answer engines

- Figures that change often (token prices, platform fees, payout thresholds) are inputs on the page, not claims in the text. Do not treat the preset values as current market prices.
- Every calculator's formula is described in the surrounding guide and can be reproduced by hand.
- Last site-wide review: 2026-11-17.

## Optional

- [Sitemap](${origin}/sitemap.xml)
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};

/**
 * The CalcPulse build log: operations record for the site itself.
 *
 * Kept apart from `guides.ts` on purpose. A guide answers a question a reader came
 * with; a log entry records what the operator ran into while keeping the site
 * alive. Every entry uses the same four sections — Constraint, What broke,
 * Numbers, Next test — so the log reads as a record rather than a diary.
 *
 * House rules for anything added here:
 *   - no number that was not measured. If it was not measured, the row says so;
 *   - no name, employer, city, family member, account handle, key, token, webhook
 *     or local path, in prose or in a screenshot;
 *   - a failed experiment goes in "What broke" with the error or the HTTP status,
 *     not quietly dropped from the list.
 */

export interface LogFailure {
  /** Short label, e.g. "Reversal #1 — the first host was a dead end". */
  title: string;
  paragraphs: string[];
}

export interface LogNumber {
  label: string;
  value: string;
  /** How the figure is produced. A number without this does not go in. */
  note: string;
}

export interface LogEntry {
  day: number;
  /** URL segment: day-001-zero-cost-stack */
  slug: string;
  /** <title> and listing headline. The number or constraint goes in the title. */
  title: string;
  description: string;
  /** One-sentence teaser for /log/. */
  summary: string;
  published: string;
  updated: string;
  minutes: number;
  constraint: string[];
  failures: LogFailure[];
  numbersIntro: string;
  numbers: LogNumber[];
  nextTest: string[];
  /** Calculator pages this entry is about; rendered as about[] in the JSON-LD. */
  tools: { label: string; href: string }[];
}

/** Counts printed by each suite of `npm test`, re-checked before this entry shipped. */
export const checkSuites: { suite: string; count: number; command: string }[] = [
  { suite: 'Arithmetic', count: 15, command: 'test:calc' },
  { suite: 'DOM wiring', count: 4, command: 'test:dom' },
  { suite: 'Pipeline', count: 27, command: 'test:pipeline' },
  { suite: 'Content queue', count: 11, command: 'test:queue' },
];

export const automatedChecks = checkSuites.reduce((total, suite) => total + suite.count, 0);

export const infraCostUsd = 0;

export const logEntries: LogEntry[] = [
  {
    day: 1,
    slug: 'day-001-zero-cost-stack',
    title: 'Day 1 — Two AI products on $0/mo: 57 automated checks, 0 ads, 3 reversals',
    description:
      'How a calculator hub and a digital product live on a $0 monthly infrastructure bill: the three options that were closed before launch, the checks that gate a publish, and the number that has not moved yet.',
    summary:
      'The first entry. What the $0 constraint actually rules out, the four things that broke before launch, and the one metric this log will be judged on.',
    published: '2026-11-18',
    updated: '2026-11-18',
    minutes: 6,
    constraint: [
      'The budget is $0.00 a month, not "$0 to start". No card is on file with any host, API or analytics service, no paid tier is switched on, and a change that would add a recurring charge has to replace something rather than sit beside it.',
      'The second constraint is time: 30 to 60 minutes a day, which covers maintenance and an occasional guide, not a redesign. The third is that the operator stays unnamed — the site, the products and their metadata speak as CalcPulse only.',
      'Those three constraints explain most of the architecture that follows. A static build with no server, a browser-side calculator with no API call per visitor, files sold through someone else\'s checkout, and one publish workflow whose gate fails closed.',
    ],
    failures: [
      {
        title: 'Reversal #1 — the first host was a dead end',
        paragraphs: [
          'The first deploy in this portfolio went to a hobby tier of a platform whose terms prohibit commercial use. That is a soft prohibition until a site starts selling something, and these sites sell files from day one, so the terms were a countdown rather than a technical limit.',
          'Everything moved to a static host whose free tier permits commercial use: the output is HTML and one small JavaScript bundle per calculator, and nothing needs a server. The migration was a build setting and a DNS record, not a rewrite. That lesson was cheap only because the site was static; a database would have made the same discovery expensive, and this calculator hub was built on the second host rather than migrated to it.',
        ],
      },
      {
        title: 'Reversal #2 — the ad option never existed',
        paragraphs: [
          'The plan for covering costs was an ad network. That plan died on the domain: the network does not approve publisher accounts on a shared subdomain, and a custom domain would have added the first recurring charge to a $0 budget.',
          'So the site carries no ad tag at all — not a disabled slot, not a placeholder. Revenue, if it ever arrives, comes from files sold through a checkout on another domain, plus a partner slot that stays invisible until a programme approves the account. A reader who blocks ads sees the same page as one who does not.',
        ],
      },
      {
        title: 'Reversal #3 — the scheduled trigger is not something to rely on',
        paragraphs: [
          'On 17 November a scheduled workflow in a sibling repository missed four runs in a row. Not four failures: four non-runs. There was no red build to inspect and no error line to read, because nothing ever started. Scheduled triggers on a free account are best-effort, and there is no queue position to appeal to when a slot is simply skipped.',
          'So the publish step here is started by hand, while the gate stayed automated: the workflow runs the arithmetic and DOM checks, builds, then runs a deployment guard that fails on a forbidden topic word, a missing required page, a dead link, an ad tag, or the operator\'s legal name appearing anywhere in the output. A build that fails the guard is not published. Whether a person or a scheduler pressed the button matters far less than whether the button could publish something unchecked.',
        ],
      },
      {
        title: 'The payment rail narrowed to one',
        paragraphs: [
          'Two processors were ruled out before the first listing: one stopped taking new accounts the day before launch, and the other does not pay out to an individual in this market in local currency. What was left was a marketplace that takes a cut and handles tax, on a domain the buyer sees at checkout.',
          'The consequence is cosmetic but worth stating: the site has no card field, no checkout and no refund flow of its own. Payment happens where the files live, and the site\'s job is to describe the files honestly enough that the click is informed.',
        ],
      },
    ],
    numbersIntro:
      'Every figure below is produced by a command or a dashboard; the note says which. Nothing here is a projection, and the traffic figure that matters is not in this table because there is not enough of it to mean anything yet.',
    numbers: [
      {
        label: 'Infrastructure cost',
        value: '$0.00 / month',
        note: 'Static host free tier, workflow runs inside the free allowance, no paid API tier. A rebuild is a git push.',
      },
      {
        label: 'Automated checks',
        value: `${automatedChecks} / ${automatedChecks}`,
        note: '15 arithmetic, 4 DOM-wiring, 27 pipeline and 11 content-queue checks. npm test runs all of them, plus the deployment guard, before a publish.',
      },
      {
        label: 'Calculators live',
        value: '3',
        note: 'Across 4 guides. Each runs entirely in the browser: no request per calculation, no account.',
      },
      {
        label: 'Paid listings',
        value: '2',
        note: 'One prompt-and-script pack ($5 starter, $14 bundle) and one weekly CSV pack ($9). Checkout on Gumroad.',
      },
      {
        label: 'Ad slots, popups, cookie banners',
        value: '0',
        note: 'No ad network is loaded. Pageviews are counted in aggregate by one analytics tag; it sets no advertising cookie.',
      },
      {
        label: 'Options closed before launch',
        value: '3',
        note: 'A commercial host, an ad network, and a direct payment processor. Each one removed a paid path, not just a feature.',
      },
    ],
    nextTest: [
      'The hypothesis for the next four weeks is narrow: an engineering log makes the pages that already exist easier to find, because every calculator page now links to it and the log links back with a specific claim about how that calculator was checked.',
      'It is measured in Search Console, not asserted: pages indexed, impressions and clicks for the four guide pages over 28 days, compared with the 28 days before the first log entry. If the log changes nothing there, it stays an operations record and the effort moves back to the guides — which is a perfectly acceptable outcome, and cheaper than pretending otherwise.',
      'The log itself fires four events and no more: a view of the log, a click from a log to a calculator, a click to a paid listing with the product name attached, and a view of the free samples. Four is enough to see where a reader leaves. The next entry is Friday, built from two or three days of collected logs rather than written daily.',
    ],
    tools: [
      { label: 'What an LLM feature costs per month', href: '/guides/ai-api-cost-calculator/' },
      { label: 'When a subscription pays for itself', href: '/guides/saas-break-even-calculator/' },
      { label: 'What a payment processor keeps', href: '/guides/payment-fee-calculator/' },
    ],
  },
];

export const logEntryBySlug = (slug: string): LogEntry => {
  const found = logEntries.find((entry) => entry.slug === slug);
  if (!found) throw new Error(`Unknown build log slug: ${slug}`);
  return found;
};

/** Newest first, which is the order the index renders. */
export const latestFirst = (): LogEntry[] => [...logEntries].sort((a, b) => b.day - a.day);

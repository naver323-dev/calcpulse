export interface Guide {
  slug: string;
  /** <title> text, kept under ~60 characters where possible. */
  title: string;
  h1: string;
  description: string;
  /** One-sentence abstract reused by llms.txt and the guide index. */
  summary: string;
  calculator: string;
  /** ISO date of the last substantive review. */
  updated: string;
  /** Reading time in minutes, hand-checked against the body. */
  minutes: number;
  keywords: string[];
  topic: 'AI cost' | 'SaaS & tooling' | 'Small-business finance';
}

export const guides: Guide[] = [
  {
    slug: 'ai-api-cost-calculator',
    title: 'AI API Cost Calculator: Price an LLM Feature Per Month',
    h1: 'What your LLM feature actually costs per month',
    description:
      'Estimate monthly LLM API spend from requests per day, input and output tokens, retry overhead and prompt-cache hit rate. Enter your own provider rates.',
    summary:
      'Turns requests per day, token counts, retry overhead and cache hit rate into a monthly API bill and a per-request unit cost, using the rates you paste in from your provider.',
    calculator: 'LLM API cost calculator',
    updated: '2026-11-17',
    minutes: 7,
    keywords: ['llm api cost calculator', 'openai pricing calculator', 'token cost estimate', 'ai feature unit economics'],
    topic: 'AI cost',
  },
  {
    slug: 'saas-break-even-calculator',
    title: 'SaaS Break-Even Calculator: When a Tool Pays for Itself',
    h1: 'When does this subscription actually pay for itself?',
    description:
      'Work out payback months and 12-month ROI for a paid tool using seats, price, one-off setup cost, hours saved and an honest adoption rate.',
    summary:
      'Combines subscription price, seats and setup cost with time saved at a loaded hourly rate, discounts for real-world adoption, and returns payback months plus 12-month ROI.',
    calculator: 'SaaS break-even and ROI calculator',
    updated: '2026-11-17',
    minutes: 6,
    keywords: ['saas roi calculator', 'break even calculator software', 'software subscription payback', 'tool roi'],
    topic: 'SaaS & tooling',
  },
  {
    slug: 'payment-fee-calculator',
    title: 'Payment Fee Calculator: What Your Processor Keeps Per Month',
    h1: 'What your payment processor keeps every month',
    description:
      'Turn charges, average sale, percentage and fixed fees, refunds and a monthly platform fee into the money the processor keeps and the effective rate you actually pay.',
    summary:
      'Combines percentage and fixed per-charge fees, refunded volume and a flat monthly fee into total fees, net revenue and the effective rate, which is the only figure comparable across processors.',
    calculator: 'Payment fee calculator',
    updated: '2026-11-17',
    minutes: 6,
    keywords: ['payment processing fees', 'stripe fee calculator', 'merchant fee calculator', 'effective rate card fees'],
    topic: 'Small-business finance',
  },
  {
    slug: "fine-tune-vs-prompt-cost",
    title: "Fine-tuning versus prompting cost math",
    h1: "Fine-tuning versus prompt engineering: the unit economics",
    description:
      "Calculate whether fine-tuning a smaller model beats packing context into a larger model each month.",
    summary:
      "Compare the upfront cost of fine-tuning against the recurring token costs of prompt engineering to find the exact threshold where training pays for itself.",
    calculator: "LLM API cost calculator",
    updated: '2026-11-17',
    minutes: 6,
    keywords: ["fine tuning cost", "llm training vs prompting", "token volume math", "model adaptation budget"],
    topic: "AI cost",
  },
  {
    slug: "payment-reserve-cashflow-cost",
    title: "The true cash cost of payment processor reserves",
    h1: "How payment processor reserves drain your operating cash flow",
    description:
      "Calculate the hidden borrowing cost when your payment processor withholds a percentage of your revenue in a reserve account.",
    summary:
      "Payment processor reserves hold back a portion of your revenue to cover chargeback risks, creating a hidden cash flow deficit that requires short-term working capital to bridge.",
    calculator: "Payment fee calculator",
    updated: '2026-11-19',
    minutes: 4,
    keywords: ["payment processor reserve", "merchant account hold", "rolling reserve cash flow", "processing reserve cost"],
    topic: "Small-business finance",
  },
  {
    slug: "llm-reverse-engineering-budget",
    title: "Estimating the cost of LLM‑assisted reverse engineering",
    h1: "How much does an LLM‑driven reverse‑engineering workflow really cost?",
    description:
      "A step‑by‑step guide to calculate the monthly spend of using a language model for reverse engineering code or binaries.",
    summary:
      "Calculate the monthly budget for an LLM‑based reverse‑engineering pipeline using realistic usage inputs.",
    calculator: "LLM API cost calculator",
    updated: '2026-11-20',
    minutes: 4,
    keywords: ["llm reverse engineering cost", "ai code analysis pricing", "machine learning budget calculator"],
    topic: "AI cost",
  },
  {
    slug: 'seller-platform-fee-comparison',
    title: 'Gumroad vs Payhip vs Ko-fi vs Stripe: What You Keep Per Sale',
    h1: 'What you keep on a digital product, platform by platform',
    description:
      'Compare take-home on the same digital product across Gumroad, Payhip, Ko-fi, Stripe and PayPal. Fee per sale, keep rate and monthly net, with every rate editable.',
    summary:
      'Reduces each selling platform to one percentage and one fixed fee per sale, then shows fee per sale, keep rate and monthly net for your price and volume so the cheapest route at your ticket size is visible.',
    calculator: 'Seller fee comparison',
    updated: '2026-11-21',
    minutes: 5,
    keywords: ['gumroad fees calculator', 'gumroad vs payhip', 'ko-fi shop fees', 'digital product platform fees'],
    topic: 'Small-business finance',
  },
  {
    slug: "autonomous-agent-pr-cost",
    title: "What automated coding agents cost per merged pull request",
    h1: "The real cost of automated coding pipelines per merged pull request",
    description:
      "Calculate the true cost of autonomous coding agents by accounting for token loops, CI runner execution, review hours, and failed iterations.",
    summary:
      "Autonomous coding pipelines burn tokens and CI minutes on every iteration loop. Calculate the net cost per merged feature before replacing human tasks.",
    calculator: "SaaS break-even and ROI calculator",
    updated: '2026-11-21',
    minutes: 5,
    keywords: ["coding agent economics", "agentic pipeline token cost", "cost per merged pull request", "automated code generation budget"],
    topic: "SaaS & tooling",
  },
  {
    slug: "ai-summarizer-cost-per-document",
    title: "What an AI Summarizer Costs per 1,000 Documents",
    h1: "What an AI summarizer really costs per thousand documents",
    description:
      "Build the monthly bill for an AI summarizer from document length, summary length, retries and cache hits, then read the cost per finished summary.",
    summary:
      "Turns average document tokens, summary length, retry rate and prompt cache hit share into a monthly API bill and a per-document unit cost you can compare with a review hour.",
    calculator: "LLM API cost calculator",
    updated: '2026-11-22',
    minutes: 4,
    keywords: ["ai summarizer cost", "document summarization api cost", "token cost per document", "summarization unit economics"],
    topic: "AI cost",
  },
  {
    slug: "annual-vs-monthly-tool-cost",
    title: "Annual or Monthly: What Prepaying a Tool Saves",
    h1: "What prepaying a year of a tool actually saves you",
    description:
      "Compare an annual and a monthly seat price using the discount, the cash you tie up and the seats you will drop before the year ends.",
    summary:
      "Turns a monthly list price, an annual discount and a seat count into the real saving from prepaying, after the cash cost and the chance that seats shrink during the term.",
    calculator: "SaaS break-even and ROI calculator",
    updated: '2026-11-23',
    minutes: 4,
    keywords: ["annual vs monthly pricing", "saas annual discount", "prepay software seats", "software subscription cash flow"],
    topic: "SaaS & tooling",
  },
  {
    slug: "small-ticket-card-fee-break-even",
    title: "Small-Ticket Card Fees: Where a Lower Rate Costs More",
    h1: "Where a lower percentage rate costs more on every sale",
    description:
      "Find the average ticket at which a higher percentage with a smaller fixed fee beats a lower percentage with a bigger one.",
    summary:
      "Sets two card processing quotes against each other and finds the average order value where the lower percentage with the higher fixed fee starts to cost more each month.",
    calculator: "Payment fee calculator",
    updated: '2026-11-24',
    minutes: 4,
    keywords: ["card processing fee comparison", "small ticket payment fees", "fixed fee versus percentage", "effective rate calculator"],
    topic: "Small-business finance",
  },
  {
    slug: "batch-api-discount-break-even",
    title: "Batch API Discounts: When Half Price Beats Waiting",
    h1: "What a 50 percent batch discount is worth against a 24 hour wait",
    description:
      "Work out how much of your model traffic can wait a day, then price the 50 percent batch discount against the delay it buys.",
    summary:
      "Reads a monthly token bill as two prices for the same tokens, finds the share of calls that must move to batch before the discount covers the cost of a second path, and works one month end to end.",
    calculator: "LLM API cost calculator",
    updated: '2026-11-25',
    minutes: 5,
    keywords: ["batch api discount", "llm cost per token", "asynchronous inference cost", "api bill calculator"],
    topic: "AI cost",
  },
];

export const guideBySlug = (slug: string): Guide => {
  const found = guides.find((guide) => guide.slug === slug);
  if (!found) throw new Error(`Unknown guide slug: ${slug}`);
  return found;
};

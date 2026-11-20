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
];

export const guideBySlug = (slug: string): Guide => {
  const found = guides.find((guide) => guide.slug === slug);
  if (!found) throw new Error(`Unknown guide slug: ${slug}`);
  return found;
};

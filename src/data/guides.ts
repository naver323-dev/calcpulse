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
];

export const guideBySlug = (slug: string): Guide => {
  const found = guides.find((guide) => guide.slug === slug);
  if (!found) throw new Error(`Unknown guide slug: ${slug}`);
  return found;
};

/**
 * Monetisation slots for P1.
 *
 * Decision (2026-11-17, user): P1 runs at zero cost and carries **no advertising**.
 * Revenue moves through two routes only:
 *
 *   1. affiliate / partner links in guide bodies and the offer slot, and
 *   2. traffic sent to P2 (Gumroad digital products) and P3 (Gumroad CSV packs).
 *
 * Nothing here is a live affiliate programme yet. An offer with an empty `url` is
 * not rendered at all, so the site never ships a dead or unapproved link. Fill in
 * `url` and flip `enabled` only after the programme approves the account.
 */

export interface Offer {
  id: string;
  /** Small label above the title. */
  kicker: string;
  title: string;
  body: string;
  cta: string;
  /** Empty string = not configured yet; the slot is then skipped. */
  url: string;
  /** 'own' = a property the user owns (no commission), 'affiliate' = paid programme. */
  kind: 'own' | 'affiliate';
  enabled: boolean;
}

export const offers: Offer[] = [
  {
    id: 'vault',
    kicker: 'P2 · Digital product',
    title: 'The workflow vault',
    body: 'Ten tested system prompts and ten runnable Python/Apps Script snippets — the paid companion to these guides. Three of them are free to read in full on the vault page; checkout is on Gumroad.',
    cta: 'Read the free samples',
    // Internal funnel: /vault/ carries the free samples and the Gumroad button.
    // The Gumroad URL itself is set once, by PUBLIC_GUMROAD_VAULT_URL at build time,
    // so this offer never has to be edited when the listing goes live.
    url: '/vault/',
    kind: 'own',
    enabled: true,
  },
  {
    id: 'stackverdict',
    kicker: 'Sister site',
    title: 'StackVerdict — independent AI & SaaS reviews',
    body: 'Longer hands-on reviews and pricing breakdowns of the tools that show up in these calculators.',
    cta: 'Read StackVerdict',
    // Confirmed public URL (2026-11-17).
    url: 'https://stackverdict-8jj.pages.dev',
    kind: 'own',
    enabled: true,
  },
  {
    id: 'csv',
    kicker: 'P3 · Open data',
    title: 'Open-data weekly packs',
    body: 'Fourteen public macro and AI-ecosystem series, cleaned weekly with the week-over-week change, a z-score and an outlier flag. Six of them are free to read and download on the datasets page; the full pack is $9 on Gumroad.',
    cta: 'See the free sample',
    // Internal funnel: /datasets/ carries the free sample and, once the listing is
    // live, the Gumroad button. The listing URL is set once by
    // PUBLIC_GUMROAD_DATASET_URL at build time, so this offer never needs editing.
    url: '/datasets/',
    kind: 'own',
    enabled: true,
  },
  {
    id: 'make',
    kicker: 'Partner',
    title: 'Automation platform we use',
    body: 'Affiliate slot reserved for the automation platform that appears most in the workflows these guides describe.',
    cta: 'Visit partner',
    // TODO: fill after the affiliate programme approves the account, then set
    // enabled: true. Kept off so an unapproved partner never appears on a live page.
    url: '',
    kind: 'affiliate',
    enabled: false,
  },
];

/**
 * Offers that should appear on a page. An offer without a URL still renders, as a
 * plain card with no link, so the slot's placement is visible while the product or
 * the programme approval is pending — the site never ships an `href=""`.
 */
export const activeOffers = (): Offer[] => offers.filter((offer) => offer.enabled);

/** The P2 upsell, used where a single call to action is wanted. */
export const vaultOffer = (): Offer | undefined => activeOffers().find((offer) => offer.id === 'vault');

/** True when an affiliate (paid) link is rendered on the page. */
export const hasAffiliate = (list: Offer[]): boolean => list.some((offer) => offer.kind === 'affiliate');

/**
 * Helpers for the free samples shown on /vault/.
 *
 * The sample files under src/data/vault-samples/ are byte-identical copies of files in
 * the product build (see scripts/sync_vault_samples.py, which both writes and checks
 * them). Nothing here rewrites their content: the page shows the same text a buyer
 * receives, which is the point of giving a sample away.
 */

export interface SamplePrompt {
  title: string;
  category: string;
  /** The text a buyer would paste into a model's system message. */
  body: string;
  /** Lines in the body, so the page can say how long it is. */
  lines: number;
}

/** Parse the `key: value` lines at the top of a product Markdown file. */
export function frontMatter(raw: string): Record<string, string> {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return {};
  const fields: Record<string, string> = {};
  for (const line of match[1].split(/\r?\n/)) {
    const separator = line.indexOf(':');
    if (separator === -1) continue;
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim().replace(/^["']|["']$/g, '');
    if (key) fields[key] = value;
  }
  return fields;
}

/** The fenced block introduced by ```text — the prompt itself, not the notes around it. */
export function promptBlock(raw: string): string {
  const match = raw.match(/```text\r?\n([\s\S]*?)\r?\n```/);
  return match ? match[1].trim() : '';
}

export function samplePrompt(raw: string): SamplePrompt {
  const body = promptBlock(raw);
  const meta = frontMatter(raw);
  return {
    title: meta.title ?? 'Sample prompt',
    category: meta.category ?? 'Prompt',
    body,
    lines: body ? body.split('\n').length : 0,
  };
}

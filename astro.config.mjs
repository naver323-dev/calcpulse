// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// The production origin. Override with SITE_URL at build time once the real
// domain exists (Cloudflare Pages project or custom domain). Canonicals,
// sitemap.xml and llms.txt all derive absolute links from this value.
const site = process.env.SITE_URL ?? 'https://calcpulse.pages.dev';

export default defineConfig({
  site,
  trailingSlash: 'ignore',
  build: { format: 'directory' },
  vite: {
    plugins: [tailwindcss()],
  },
});

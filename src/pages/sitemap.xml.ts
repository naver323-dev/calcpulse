import type { APIRoute } from 'astro';
import { guides } from '../data/guides';

export const GET: APIRoute = ({ site }) => {
  const origin = (site ?? new URL('https://calcpulse.pages.dev')).origin;

  const staticPages = [
    { path: '/', lastmod: '2026-11-17', priority: '1.0' },
    { path: '/guides/', lastmod: '2026-11-17', priority: '0.8' },
    { path: '/vault/', lastmod: '2026-11-17', priority: '0.7' },
    { path: '/about/', lastmod: '2026-11-17', priority: '0.3' },
    { path: '/affiliate-disclosure/', lastmod: '2026-11-17', priority: '0.2' },
    { path: '/privacy/', lastmod: '2026-11-17', priority: '0.2' },
  ];

  const guidePages = guides.map((guide) => ({
    path: `/guides/${guide.slug}/`,
    lastmod: guide.updated,
    priority: '0.9',
  }));

  const urls = [...staticPages, ...guidePages]
    .map(
      (page) => `  <url>
    <loc>${origin}${page.path}</loc>
    <lastmod>${page.lastmod}</lastmod>
    <priority>${page.priority}</priority>
  </url>`,
    )
    .join('\n');

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

  return new Response(body, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};

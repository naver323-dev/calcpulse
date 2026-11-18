import type { APIRoute } from 'astro';
import { guides } from '../data/guides';
import { logEntries } from '../data/buildlog';

export const GET: APIRoute = ({ site }) => {
  const origin = (site ?? new URL('https://calcpulse.pages.dev')).origin;

  const staticPages = [
    { path: '/', lastmod: '2026-11-17', priority: '1.0' },
    { path: '/guides/', lastmod: '2026-11-17', priority: '0.8' },
    { path: '/log/', lastmod: '2026-11-18', priority: '0.6' },
    { path: '/vault/', lastmod: '2026-11-17', priority: '0.7' },
    { path: '/datasets/', lastmod: '2026-11-17', priority: '0.7' },
    { path: '/about/', lastmod: '2026-11-17', priority: '0.3' },
    { path: '/affiliate-disclosure/', lastmod: '2026-11-17', priority: '0.2' },
    { path: '/privacy/', lastmod: '2026-11-17', priority: '0.2' },
  ];

  const guidePages = guides.map((guide) => ({
    path: `/guides/${guide.slug}/`,
    lastmod: guide.updated,
    priority: '0.9',
  }));

  // `lastmod` is the entry's real publication date, not the build date: a rebuild
  // that changes nothing on the page must not claim the page changed.
  const logPages = logEntries.map((entry) => ({
    path: `/log/${entry.slug}/`,
    lastmod: entry.updated,
    priority: '0.5',
  }));

  const urls = [...staticPages, ...guidePages, ...logPages]
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

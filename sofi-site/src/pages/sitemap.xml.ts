import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import orte from '../data/orte.json';
import nordlichtOrte from '../data/nordlicht_orte.json';

const SITE = 'https://astroreisen.com';

/* — Redaktionelle Texte per import.meta.glob laden — */

const sofiTexte = import.meta.glob<{ frontmatter: { stand?: string } }>(
  '../texte/sonnenfinsternis/*.md',
  { eager: true },
);

const nordlichtTexte = import.meta.glob<{ frontmatter: { stand?: string } }>(
  '../texte/nordlicht/*.md',
  { eager: true },
);

/* — Hilfsfunktionen — */

const MONATE: Record<string, string> = {
  januar: '01', februar: '02', 'märz': '03', april: '04',
  mai: '05', juni: '06', juli: '07', august: '08',
  september: '09', oktober: '10', november: '11', dezember: '12',
};

function parseStand(stand: string | undefined): string | undefined {
  if (!stand) return undefined;
  const m = stand.match(/^(\w+)\s+(\d{4})$/i);
  if (!m) return undefined;
  const monat = MONATE[m[1].toLowerCase()];
  return monat ? `${m[2]}-${monat}-01` : undefined;
}

function getStandFromGlob(
  glob: Record<string, { frontmatter: { stand?: string } }>,
  dir: string,
  slug: string,
): string | undefined {
  const key = `../texte/${dir}/${slug}.md`;
  const mod = glob[key];
  return parseStand(mod?.frontmatter?.stand);
}

function toW3C(date: Date): string {
  return date.toISOString().split('T')[0];
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;');
}

/* — Sitemap-Endpoint — */

export const GET: APIRoute = async () => {
  const urls: { loc: string; lastmod?: string }[] = [];

  // Statische Seiten — kein lastmod (kein echtes Änderungsdatum)
  const staticPages = [
    '/', '/ueber-mich',
    '/nordlichter', '/nordlichter/karte', '/nordlichter/methodik',
    '/nordlichter/guides', '/nordlichter/orte',
    '/sonnenfinsternis', '/sonnenfinsternis/karte', '/sonnenfinsternis/methodik',
    '/sonnenfinsternis/guides', '/sonnenfinsternis/orte',
  ];
  for (const p of staticPages) {
    urls.push({ loc: `${SITE}${p}` });
  }

  // SoFi-Ortseiten — lastmod nur wenn Redaktionstext vorhanden
  for (const ort of orte as { slug: string }[]) {
    urls.push({
      loc: `${SITE}/sonnenfinsternis/orte/${ort.slug}`,
      lastmod: getStandFromGlob(sofiTexte, 'sonnenfinsternis', ort.slug),
    });
  }

  // Nordlicht-Ortseiten — lastmod nur wenn Redaktionstext vorhanden
  for (const ort of nordlichtOrte as { slug: string }[]) {
    urls.push({
      loc: `${SITE}/nordlichter/orte/${ort.slug}`,
      lastmod: getStandFromGlob(nordlichtTexte, 'nordlicht', ort.slug),
    });
  }

  // Guides — lastmod aus updatedDate oder pubDate
  const guides = await getCollection('guides', (g) => !g.data.draft);
  for (const guide of guides) {
    const section = guide.data.section ?? 'sonnenfinsternis';
    const prefix = section === 'nordlicht' ? '/nordlichter' : '/sonnenfinsternis';
    const date = guide.data.updatedDate ?? guide.data.pubDate;
    urls.push({
      loc: `${SITE}${prefix}/guides/${guide.id}`,
      lastmod: date ? toW3C(date) : undefined,
    });
  }

  // XML zusammenbauen
  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((u) => {
      let entry = `  <url>\n    <loc>${esc(u.loc)}</loc>`;
      if (u.lastmod) entry += `\n    <lastmod>${u.lastmod}</lastmod>`;
      entry += '\n  </url>';
      return entry;
    }),
    '</urlset>',
  ].join('\n');

  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};

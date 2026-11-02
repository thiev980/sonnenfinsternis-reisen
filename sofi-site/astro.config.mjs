import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://astroreisen.com',
  trailingSlash: 'never',
  // Seiten als /pfad.html bauen, damit Cloudflare /pfad ohne Slash ausliefert
  // (passend zu Canonical und Sitemap). Mit 'directory' leitete /pfad per 307
  // auf /pfad/ um – Widerspruch zum Canonical.
  build: { format: 'file' },
});

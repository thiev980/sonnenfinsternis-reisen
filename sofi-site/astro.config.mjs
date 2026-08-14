import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://sonnenfinsternis-reisen.de',
  integrations: [
    sitemap({
      filter: (page) =>
        !page.includes('/impressum') && !page.includes('/datenschutz'),
    }),
  ],
  trailingSlash: 'never',
});

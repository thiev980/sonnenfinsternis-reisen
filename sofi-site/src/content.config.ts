import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const guides = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/guides' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    // Überschrift auf der Seite, falls kürzer/anders als der SEO-Title
    heading: z.string().optional(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    // Kurzfassung ganz oben ("Die kurze Antwort")
    tldr: z.string().optional(),
    faq: z.array(z.object({ f: z.string(), a: z.string() })).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { guides };

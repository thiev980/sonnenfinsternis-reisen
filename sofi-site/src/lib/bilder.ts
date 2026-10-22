// Headerbilder von Wikimedia Commons (Pipeline: sofi-pipeline/scripts/bilder.py, Verfahren: docs/BILDER.md).
// Selbst gehostet, Astro rechnet sie in WebP um. Schlüssel: sofi/<slug>, nordlicht/<slug>, guide/<slug>, seite/<name>.
import type { ImageMetadata } from 'astro';
import daten from '../data/bilder.json';

export interface BildMeta {
  titel: string; datei: string; breite: number; hoehe: number;
  autor: string; lizenz: string; lizenz_url: string | null; seite: string; fokus?: string; alt?: string;
}
export interface Bild { src: ImageMetadata; meta: BildMeta }

const dateien = import.meta.glob<ImageMetadata>('../assets/bilder/**/*.jpg', { eager: true, import: 'default' });
const seiten = (daten as { seiten: Record<string, BildMeta> }).seiten;

/** Headerbild einer Seite, z. B. headerBild('sofi/tarifa'); undefined, solange keins gewählt ist. */
export function headerBild(schluessel: string): Bild | undefined {
  const meta = seiten[schluessel];
  const src = meta && dateien[`../assets/bilder/${meta.datei}`];
  return src ? { src, meta } : undefined;
}

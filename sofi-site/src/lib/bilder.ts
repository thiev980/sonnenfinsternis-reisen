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

/** Standard-Bildausschnitt, wenn ein Bild kein `fokus` hat: etwas unter der Mitte, weil bei Landschaften
 *  sonst der Boden (Horizont, Bäume, Häuser) abgeschnitten wird. Gleicher Wert in scripts/zuschnitt.py. */
export const STANDARD_FOKUS = '50% 62%';

/** fokus («x% y%») → Position für sharp (og:image), das keine Prozente kennt. */
export function sharpPosition(fokus = STANDARD_FOKUS): string {
  const [x, y] = fokus.split(' ').map((v) => parseFloat(v));
  const v = y <= 40 ? 'top' : y >= 60 ? 'bottom' : '';
  const h = x <= 35 ? 'left' : x >= 65 ? 'right' : '';
  return [v, h].filter(Boolean).join(' ') || 'centre';
}

/** Headerbild einer Seite, z. B. headerBild('sofi/tarifa'); undefined, solange keins gewählt ist. */
export function headerBild(schluessel: string): Bild | undefined {
  const meta = seiten[schluessel];
  const src = meta && dateien[`../assets/bilder/${meta.datei}`];
  return src ? { src, meta } : undefined;
}

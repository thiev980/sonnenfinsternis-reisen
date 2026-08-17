/**
 * Zahlenformatierung fuer die Website.
 *
 * Bewusst "de-DE" und nicht "de-CH": die Schweiz schreibt offiziell den
 * Dezimalpunkt (99.99) und Tausender mit Apostroph, die Leserschaft ist aber
 * mehrheitlich deutsch und erwartet das Komma. Ein Wechsel ist ein Einzeiler.
 */
const LOCALE = 'de-DE';

/** Zahl mit hoechstens `stellen` Nachkommastellen: 98.4 -> "98,4", 100 -> "100". */
export function zahl(n, stellen = 2) {
  if (n === null || n === undefined) return '';
  return n.toLocaleString(LOCALE, { maximumFractionDigits: stellen });
}

/** SoFi-Score immer mit zwei Nachkommastellen: 1 -> "1,00", 3.13 -> "3,13". */
export function score(n) {
  if (n === null || n === undefined) return '';
  return n.toLocaleString(LOCALE, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

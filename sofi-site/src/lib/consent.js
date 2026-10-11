// Einwilligungs-Speicher für Dienste von Drittanbietern (derzeit: Stay22).
// Die Wahl liegt ausschliesslich im Browser (localStorage), nie auf dem Server.
// Ändert sich die Wahl, wird auf `document` das Event "consent-change" ausgelöst,
// damit Komponenten sofort reagieren können, ohne dass die Seite neu laden muss.

const KEY = 'astroreisen-consent-v1';

// Fallback, falls localStorage nicht verfügbar ist (z. B. blockiert): Dann gilt
// die Wahl nur bis zum nächsten Seitenwechsel, und das Fenster erscheint erneut.
let speicher = null;

/** @returns {{ stay22: boolean, ts: number } | null} null = noch keine Wahl getroffen */
export function getConsent() {
  try {
    const roh = localStorage.getItem(KEY);
    if (roh) {
      const v = JSON.parse(roh);
      if (v && typeof v.stay22 === 'boolean') return v;
    }
  } catch {
    // ignorieren: Zugriff auf localStorage kann scheitern
  }
  return speicher;
}

export function setConsent(stay22) {
  const wert = { stay22: Boolean(stay22), ts: Date.now() };
  speicher = wert;
  try {
    localStorage.setItem(KEY, JSON.stringify(wert));
  } catch {
    // ignorieren
  }
  document.dispatchEvent(new CustomEvent('consent-change', { detail: wert }));
}

/** @param {(stay22: boolean) => void} fn */
export function onConsentChange(fn) {
  document.addEventListener('consent-change', (e) => fn(e.detail.stay22));
}

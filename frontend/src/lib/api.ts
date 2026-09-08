export class ApiFehler extends Error {
  constructor(public status: number, meldung: string) { super(meldung); }
}

async function anfrage<T>(pfad: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`/api${pfad}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    ...init,
  });
  if (r.status === 401) {
    if (!location.pathname.includes("/login")) location.href = pfad.startsWith("/coach") ? "/coach/login" : "/login";
    throw new ApiFehler(401, "Nicht angemeldet");
  }
  if (!r.ok) {
    let meldung = r.statusText;
    try { meldung = (await r.json()).detail ?? meldung; } catch { /* leer */ }
    throw new ApiFehler(r.status, String(meldung));
  }
  return r.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => anfrage<T>(p),
  post: <T>(p: string, body?: unknown) => anfrage<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T>(p: string, body: unknown) => anfrage<T>(p, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(p: string, body: unknown) => anfrage<T>(p, { method: "PATCH", body: JSON.stringify(body) }),
  del: <T>(p: string) => anfrage<T>(p, { method: "DELETE" }),
};

/** SSE über fetch (POST) — EventSource kann kein POST. */
export async function streamen(
  pfad: string, body: unknown,
  onEvent: (event: string, daten: any) => void,
): Promise<void> {
  const r = await fetch(`/api${pfad}`, {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok || !r.body) {
    let meldung = "Der Buddy ist gerade nicht erreichbar.";
    try { meldung = (await r.json()).detail ?? meldung; } catch { /* leer */ }
    onEvent("fehler", { meldung }); return;
  }
  const leser = r.body.getReader();
  const dec = new TextDecoder();
  let puffer = "";
  while (true) {
    const { value, done } = await leser.read();
    if (done) break;
    puffer += dec.decode(value, { stream: true });
    let idx;
    while ((idx = puffer.indexOf("\n\n")) >= 0) {
      const block = puffer.slice(0, idx); puffer = puffer.slice(idx + 2);
      let event = "message", daten = "";
      for (const zeile of block.split("\n")) {
        if (zeile.startsWith("event:")) event = zeile.slice(6).trim();
        else if (zeile.startsWith("data:")) daten += zeile.slice(5).trim();
      }
      if (daten) { try { onEvent(event, JSON.parse(daten)); } catch { onEvent(event, daten); } }
    }
  }
}

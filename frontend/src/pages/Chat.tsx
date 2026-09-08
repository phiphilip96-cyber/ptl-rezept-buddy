import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, streamen } from "../lib/api";
import { Konversation, Nachricht, Plan } from "../lib/typen";
import { Markdown } from "../lib/markdown";
import { PlanAnsicht } from "../components/Plaene";
import { Kopf } from "../components/Ui";

export default function Chat() {
  const { id } = useParams();
  const nav = useNavigate();
  const [konv, setKonv] = useState<Konversation | null>(null);
  const [nachrichten, setNachrichten] = useState<Nachricht[]>([]);
  const [fragen, setFragen] = useState<string[]>([]);
  const [eingabe, setEingabe] = useState("");
  const [laeuft, setLaeuft] = useState(false);
  const [menue, setMenue] = useState(false);
  const [liste, setListe] = useState<Konversation[]>([]);
  const ende = useRef<HTMLDivElement>(null);

  // Ohne id: letzten Chat öffnen oder neuen anlegen. Ohne Profil: zum Profil.
  useEffect(() => {
    (async () => {
      const prof = await api.get<{ profil: unknown }>("/profil");
      if (!prof.profil) { nav("/profil", { replace: true }); return; }
      const { konversationen } = await api.get<{ konversationen: Konversation[] }>("/konversationen");
      setListe(konversationen);
      if (!id) {
        const k = konversationen[0] ?? (await api.post<Konversation>("/konversationen"));
        nav(`/chat/${k.id}`, { replace: true }); return;
      }
      const k = konversationen.find((x) => x.id === id) ?? null;
      setKonv(k);
      const { nachrichten } = await api.get<{ nachrichten: Nachricht[] }>(`/konversationen/${id}/nachrichten`);
      const mitPlaenen = await Promise.all(nachrichten.map(async (n) =>
        n.plan_ids.length ? { ...n, plaene: await Promise.all(n.plan_ids.map((p) => api.get<Plan>(`/plaene/${p}`))) } : n));
      setNachrichten(mitPlaenen);
      if (!nachrichten.length) setFragen((await api.get<{ fragen: string[] }>("/vorschlagsfragen")).fragen);
    })();
  }, [id]);

  useEffect(() => { ende.current?.scrollIntoView({ block: "end" }); }, [nachrichten, laeuft]);

  async function senden(text: string) {
    if (!text.trim() || laeuft || !id) return;
    setEingabe(""); setFragen([]); setLaeuft(true);
    const t = new Date().toISOString();
    setNachrichten((alt) => [...alt,
      { id: "k" + t, rolle: "kunde", inhalt: text, plan_ids: [], erstellt_am: t },
      { id: "b" + t, rolle: "buddy", inhalt: "", plan_ids: [], erstellt_am: t, laeuft: true, plaene: [] }]);
    const patch = (fn: (n: Nachricht) => Nachricht) =>
      setNachrichten((alt) => alt.map((n) => (n.id === "b" + t ? fn(n) : n)));

    await streamen(`/konversationen/${id}/nachrichten`, { inhalt: text }, (event, d) => {
      if (event === "text") patch((n) => ({ ...n, inhalt: n.inhalt + d }));
      else if (event === "plan_gespeichert") patch((n) => ({ ...n, plaene: [...(n.plaene ?? []), { id: d.plan_id, typ: d.typ, titel: d.titel, favorit: false, erstellt_am: t, daten: d.daten }] }));
      else if (event === "fertig") patch((n) => ({ ...n, id: d.nachricht_id, inhalt: d.inhalt, laeuft: false }));
      else if (event === "fehler") patch((n) => ({ ...n, inhalt: d.meldung, laeuft: false }));
    });
    setLaeuft(false);
    if (konv?.titel === "Neuer Chat") setKonv({ ...konv, titel: text.slice(0, 60) });
  }

  async function neuerChat() {
    const k = await api.post<Konversation>("/konversationen");
    setMenue(false); nav(`/chat/${k.id}`);
  }

  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf
        links={<button onClick={() => setMenue(true)} aria-label="Chats" className="text-wald">Chats</button>}
        titel={<span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-wald" />Rezept-Buddy</span>}
        rechts={<Link to="/profil" className="text-wald">Profil</Link>}
      />

      {menue && (
        <div className="fixed inset-0 z-20 bg-tinte/40" onClick={() => setMenue(false)}>
          <div className="absolute left-0 top-0 bottom-0 w-80 max-w-[85vw] bg-papier p-4 flex flex-col" onClick={(e) => e.stopPropagation()}>
            <button onClick={neuerChat} className="h-12 rounded-full bg-wald text-white font-semibold">Neuer Chat</button>
            <ul className="mt-4 flex-1 overflow-y-auto divide-y divide-linie">
              {liste.map((k) => (
                <li key={k.id}>
                  <Link to={`/chat/${k.id}`} onClick={() => setMenue(false)}
                    className={`block py-3 truncate ${k.id === id ? "font-semibold text-wald" : ""}`}>{k.titel}</Link>
                </li>
              ))}
            </ul>
            <Link to="/plaene" className="block py-3 border-t border-linie font-semibold" onClick={() => setMenue(false)}>Meine Pläne</Link>
          </div>
        </div>
      )}

      <section className="flex-1 px-4 py-4 space-y-4">
        {!nachrichten.length && (
          <div className="pt-6">
            <p className="text-2xl font-bold leading-tight">Was soll auf den Teller?</p>
            <p className="text-grau mt-1">Ich kenne dein Profil und deine Unverträglichkeiten. Frag einfach.</p>
            <div className="mt-5 space-y-2">
              {fragen.map((f) => (
                <button key={f} onClick={() => senden(f)} className="block w-full text-left rounded-2xl bg-white border border-linie px-4 py-3 active:bg-wald-hell">{f}</button>
              ))}
            </div>
          </div>
        )}

        {nachrichten.map((n) => (
          <div key={n.id} className={n.rolle === "kunde" ? "flex justify-end" : ""}>
            {n.rolle === "kunde" ? (
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-wald text-white px-4 py-2.5 whitespace-pre-wrap">{n.inhalt}</div>
            ) : n.rolle === "coach" ? (
              <div className="rounded-2xl bg-wald-hell px-4 py-3 text-sm"><span className="font-semibold">Philip:</span> {n.inhalt}</div>
            ) : (
              <div className="space-y-3">
                {n.inhalt ? <Markdown text={n.inhalt} /> : n.laeuft && <span className="inline-block w-2 h-5 bg-wald animate-pulse rounded-sm" aria-label="Der Buddy schreibt" />}
                {n.plaene?.map((p) => p.daten && (
                  <div key={p.id}>
                    <PlanAnsicht daten={p.daten} />
                    <Link to={`/plaene/${p.id}`} className="inline-block mt-2 text-sm text-wald font-medium">Unter „Meine Pläne" gespeichert</Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={ende} />
      </section>

      <form onSubmit={(e: FormEvent) => { e.preventDefault(); senden(eingabe); }}
        className="sticky bottom-0 bg-papier border-t border-linie px-3 py-2 flex gap-2 items-end" style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}>
        <textarea rows={1} value={eingabe} onChange={(e) => setEingabe(e.target.value)} placeholder="Frag mich etwas …"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); senden(eingabe); } }}
          className="flex-1 max-h-32 min-h-12 rounded-2xl border border-linie bg-white px-4 py-3 resize-none focus:border-wald" />
        <button type="submit" disabled={laeuft || !eingabe.trim()} aria-label="Senden"
          className="w-12 h-12 rounded-full bg-wald text-white font-bold disabled:opacity-40 shrink-0">↑</button>
      </form>
    </main>
  );
}

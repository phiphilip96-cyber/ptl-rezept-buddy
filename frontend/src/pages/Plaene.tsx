import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Einkaufsliste, Plan } from "../lib/typen";
import { TabLeiste } from "../components/TabLeiste";
import { PlanAnsicht } from "../components/Plaene";
import { Knopf, Kopf, Leer } from "../components/Ui";

export function PlaeneListe() {
  const [plaene, setPlaene] = useState<Plan[] | null>(null);
  const nav = useNavigate();
  useEffect(() => { api.get<{ plaene: Plan[] }>("/plaene").then((d) => setPlaene(d.plaene)); }, []);
  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf titel="Meine Pläne" links={<button onClick={() => nav("/chat")} className="text-wald">Chat</button>} />
      <div className="flex-1">
      {plaene && !plaene.length && <Leer titel="Noch nichts gespeichert." text="Frag den Buddy nach einem Wochenplan oder Rezept – alles landet automatisch hier." kind={<Link to="/chat" className="text-wald font-semibold">Zum Chat</Link>} />}
      <ul className="divide-y divide-linie px-4">
        {plaene?.map((p) => (
          <li key={p.id}>
            <Link to={`/plaene/${p.id}`} className="flex items-center gap-3 py-3">
              <span className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${p.typ === "wochenplan" ? "bg-wald text-white" : "bg-wald-hell text-wald"}`}>{p.typ === "wochenplan" ? "Wo" : "Re"}</span>
              <span className="flex-1 min-w-0">
                <span className="block truncate font-medium">{p.titel}</span>
                <span className="block text-xs text-grau">{new Date(p.erstellt_am).toLocaleDateString("de-DE")}</span>
              </span>
              {p.favorit && <span className="text-wald" aria-label="Favorit">★</span>}
            </Link>
          </li>
        ))}
      </ul>
      </div>
      <TabLeiste />
    </main>
  );
}

export function PlanDetail() {
  const { id } = useParams();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [liste, setListe] = useState<{ einkaufsliste: Einkaufsliste; text: string } | null>(null);
  const [listeFehler, setListeFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  const [meldung, setMeldung] = useState<string | null>(null);
  const nav = useNavigate();
  useEffect(() => { api.get<Plan>(`/plaene/${id}`).then(setPlan); }, [id]);

  async function einkaufsliste(neu = false) {
    setLaeuft(true); setListeFehler(null);
    try { setListe(await api.post(`/plaene/${id}/einkaufsliste`, { personen: 1, neu })); }
    catch (err: any) { setListeFehler(err.message || "Hat nicht geklappt."); }
    finally { setLaeuft(false); }
  }
  async function teilen() {
    if (!liste) return;
    if (navigator.share) { try { await navigator.share({ text: liste.text }); return; } catch { /* abgebrochen */ } }
    await navigator.clipboard.writeText(liste.text); setMeldung("Kopiert."); setTimeout(() => setMeldung(null), 2000);
  }
  async function aktivieren() {
    const d = new Date(); d.setDate(d.getDate() + ((8 - d.getDay()) % 7));
    const start = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    await api.put(`/plaene/${id}/aktivieren`, { start_datum: start });
    setMeldung(`Aktiv ab ${start.slice(8)}.${start.slice(5, 7)}. – Mahlzeiten stehen dann unter „Heute“.`);
  }
  async function favorit() {
    if (!plan) return;
    await api.patch(`/plaene/${plan.id}`, { favorit: !plan.favorit });
    setPlan({ ...plan, favorit: !plan.favorit });
  }
  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel={plan?.titel ?? ""} links={<button onClick={() => nav(-1)} className="text-wald">Zurück</button>}
        rechts={plan && <button onClick={favorit} aria-pressed={plan.favorit} aria-label="Favorit" className={`text-2xl ${plan.favorit ? "text-wald" : "text-linie"}`}>★</button>} />
      <div className="px-4 py-4 space-y-4">
        {plan?.daten && <PlanAnsicht daten={plan.daten} />}
        {plan && (
          <div className="flex flex-wrap gap-2">
            {plan.typ === "wochenplan" && <Knopf variante="leise" onClick={aktivieren}>Ab Montag aktiv</Knopf>}
            <Knopf variante="leise" onClick={() => einkaufsliste()} disabled={laeuft}>{laeuft ? "Wird erstellt …" : "Einkaufsliste"}</Knopf>
          </div>
        )}
        {meldung && <p className="text-sm text-wald">{meldung}</p>}
        {listeFehler && <p className="text-sm text-warn">{listeFehler}</p>}
        {liste && (
          <div className="rounded-2xl bg-white border border-linie p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Einkaufsliste</h2>
              <div className="flex gap-3 text-sm"><button onClick={teilen} className="text-wald font-medium">Teilen</button>{plan?.typ === "wochenplan" && <button onClick={() => einkaufsliste(true)} className="text-grau">Neu</button>}</div>
            </div>
            {liste.einkaufsliste.kategorien.map((k) => (
              <div key={k.name} className="mt-3">
                <div className="text-xs text-grau uppercase tracking-wide">{k.name}</div>
                <ul className="mt-1 space-y-0.5">{k.artikel.map((a, i) => <li key={i} className="text-[15px]"><span className="text-grau">{a.menge}</span> {a.name}</li>)}</ul>
              </div>
            ))}
            {liste.einkaufsliste.quelle === "buddy" && <p className="text-xs text-grau mt-3">Mengen vom Buddy geschätzt, auf Packungen gerundet.</p>}
          </div>
        )}
      </div>
    </main>
  );
}

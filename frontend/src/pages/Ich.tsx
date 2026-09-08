import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Checkin, CheckinAntworten, CheckinFrage, Messung, Trend } from "../lib/typen";
import { Knopf, Kopf, Leer } from "../components/Ui";
import { TabLeiste } from "../components/TabLeiste";

/** Einfache Gewichtskurve als SVG: Punkte je Messung, Linie fuer das 7-Tage-Mittel. */
export function GewichtsKurve({ messungen }: { messungen: Messung[] }) {
  const werte = messungen.filter((m) => m.gewicht_kg != null) as (Messung & { gewicht_kg: number })[];
  if (werte.length < 2) return <p className="text-sm text-grau">Trag zwei Mal dein Gewicht ein, dann siehst du hier den Verlauf.</p>;
  const W = 320, H = 120, P = 8;
  const min = Math.min(...werte.map((m) => m.gewicht_kg)) - 0.5, max = Math.max(...werte.map((m) => m.gewicht_kg)) + 0.5;
  const x = (i: number) => P + (i / (werte.length - 1)) * (W - 2 * P);
  const y = (g: number) => H - P - ((g - min) / (max - min)) * (H - 2 * P);
  const mittel = werte.map((_, i) => { const s = werte.slice(Math.max(0, i - 6), i + 1); return s.reduce((a, m) => a + m.gewicht_kg, 0) / s.length; });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-32" role="img" aria-label="Gewichtsverlauf">
      <polyline fill="none" stroke="var(--color-wald)" strokeWidth="2.5" strokeLinejoin="round" points={mittel.map((g, i) => `${x(i)},${y(g)}`).join(" ")} />
      {werte.map((m, i) => <circle key={m.datum} cx={x(i)} cy={y(m.gewicht_kg)} r="3" fill="var(--color-papier)" stroke="var(--color-grau)" strokeWidth="1.5" />)}
      <text x={P} y={H - 1} fontSize="9" className="fill-grau">{werte[0].datum.slice(8)}.{werte[0].datum.slice(5, 7)}.</text>
      <text x={W - P} y={H - 1} fontSize="9" textAnchor="end" className="fill-grau">{werte[werte.length - 1].datum.slice(8)}.{werte[werte.length - 1].datum.slice(5, 7)}.</text>
    </svg>
  );
}

export default function Ich() {
  const [messungen, setMessungen] = useState<Messung[]>([]);
  const [trend, setTrend] = useState<Trend | null>(null);
  const [checkins, setCheckins] = useState<Checkin[]>([]);
  const [woche, setWoche] = useState("");
  const [vorname, setVorname] = useState("");

  useEffect(() => {
    api.get<{ messungen: Messung[]; trend: Trend }>("/messungen?tage=28").then((d) => { setMessungen(d.messungen); setTrend(d.trend); });
    api.get<{ checkins: Checkin[]; aktuelle_woche: string }>("/checkins").then((d) => { setCheckins(d.checkins); setWoche(d.aktuelle_woche); });
    api.get<{ profil: { vorname: string } | null }>("/profil").then((d) => setVorname(d.profil?.vorname ?? ""));
  }, []);
  const dieseWoche = checkins.find((c) => c.woche === woche);

  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf titel={vorname ? `Hi ${vorname}` : "Ich"} rechts={<Link to="/profil" className="text-wald text-sm">Profil</Link>} />
      <section className="flex-1 px-4 py-4 space-y-5">
        <div className="rounded-2xl bg-white border border-linie p-4">
          <div className="flex items-baseline justify-between">
            <h2 className="font-semibold">Gewicht</h2>
            {trend?.differenz_kg != null && <span className={`text-sm font-medium ${trend.differenz_kg < 0 ? "text-wald" : "text-grau"}`}>{trend.differenz_kg > 0 ? "+" : ""}{trend.differenz_kg} kg in 4 Wochen</span>}
          </div>
          <div className="mt-2"><GewichtsKurve messungen={messungen} /></div>
          <p className="text-xs text-grau mt-1">Linie = 7-Tage-Mittel. Tageswerte schwanken, der Trend zählt. Eintragen geht unter „Heute“.</p>
        </div>

        <div className="rounded-2xl bg-white border border-linie p-4">
          <div className="flex items-baseline justify-between">
            <h2 className="font-semibold">Wochen-Check-in</h2>
            <span className="text-xs text-grau">{woche}</span>
          </div>
          {dieseWoche ? (
            <p className="text-sm mt-1">Für diese Woche erledigt. <Link to="/checkin" className="text-wald font-medium">Antworten ändern</Link></p>
          ) : (
            <>
              <p className="text-sm text-grau mt-1">Sechs Fragen, eine Minute. Der Buddy ordnet ein, Philip liest mit.</p>
              <Link to="/checkin" className="inline-flex mt-3 h-11 px-5 items-center rounded-full bg-wald text-white font-semibold">Check-in ausfüllen</Link>
            </>
          )}
        </div>

        {checkins.length > 0 && (
          <div>
            <h2 className="font-semibold mb-2">Bisherige Check-ins</h2>
            <ul className="space-y-3">
              {checkins.map((c) => (
                <li key={c.id} className="rounded-2xl bg-white border border-linie p-4">
                  <div className="text-xs text-grau">{c.woche} · Schlaf {c.antworten.schlaf} · Energie {c.antworten.energie} · Hunger {c.antworten.hunger} · Stress {c.antworten.stress} · Plan {c.antworten.plan_eingehalten} · Training {c.antworten.training_einheiten}×</div>
                  {c.buddy_zusammenfassung && <p className="text-[15px] mt-2">{c.buddy_zusammenfassung}</p>}
                  {c.coach_kommentar && <p className="text-[15px] mt-2 rounded-xl bg-wald-hell p-3"><span className="font-semibold">Philip:</span> {c.coach_kommentar}</p>}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!checkins.length && !messungen.length && <Leer titel="Noch keine Daten." text="Gewicht unter „Heute“ eintragen und den ersten Check-in machen." />}
      </section>
      <TabLeiste />
    </main>
  );
}

export function CheckinSeite() {
  const nav = useNavigate();
  const [fragen, setFragen] = useState<CheckinFrage[]>([]);
  const [a, setA] = useState<CheckinAntworten>({ schlaf: 3, energie: 3, hunger: 3, stress: 3, plan_eingehalten: 3, training_einheiten: 2, freitext: "" });
  const [laeuft, setLaeuft] = useState(false);
  const [ergebnis, setErgebnis] = useState<Checkin | null>(null);

  useEffect(() => {
    api.get<{ fragen: CheckinFrage[]; woche: string }>("/checkins/fragen").then((d) => setFragen(d.fragen));
    api.get<{ checkins: Checkin[]; aktuelle_woche: string }>("/checkins").then((d) => {
      const c = d.checkins.find((x) => x.woche === d.aktuelle_woche); if (c) setA(c.antworten);
    });
  }, []);

  async function senden(e: FormEvent) {
    e.preventDefault(); setLaeuft(true);
    try { setErgebnis((await api.post<{ checkin: Checkin }>("/checkins", { antworten: a })).checkin); }
    finally { setLaeuft(false); }
  }

  if (ergebnis) return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel="Check-in" />
      <div className="px-4 py-6 space-y-4">
        <div className="rounded-2xl bg-wald-hell p-4">
          <p className="font-semibold">Danke, gespeichert.</p>
          <p className="text-[15px] mt-2">{ergebnis.buddy_zusammenfassung || "Der Buddy meldet sich mit seiner Einordnung, sobald er erreichbar ist. Philip sieht deinen Check-in jetzt schon."}</p>
        </div>
        <Knopf className="w-full" onClick={() => nav("/ich")}>Zurück</Knopf>
      </div>
    </main>
  );

  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel="Check-in" links={<button onClick={() => nav("/ich")} className="text-wald">Zurück</button>} />
      <form onSubmit={senden} className="px-4 py-5 space-y-6">
        {fragen.map((f) => (
          <div key={f.feld}>
            <div className="font-medium mb-2">{f.frage}</div>
            <div className={`grid gap-1.5 ${f.skala > 5 ? "grid-cols-8" : "grid-cols-5"}`}>
              {Array.from({ length: f.skala + (f.skala > 5 ? 1 : 0) }, (_, i) => (f.skala > 5 ? i : i + 1)).map((n) => (
                <button type="button" key={n} onClick={() => setA({ ...a, [f.feld]: n })} aria-pressed={a[f.feld] === n}
                  className={`h-11 rounded-xl border font-semibold ${a[f.feld] === n ? "bg-wald border-wald text-white" : "bg-white border-linie"}`}>{n}</button>
              ))}
            </div>
            {f.skala === 5 && <div className="flex justify-between text-xs text-grau mt-1"><span>schlecht</span><span>super</span></div>}
          </div>
        ))}
        <label className="block">
          <span className="block font-medium mb-2">Was willst du Philip noch sagen?</span>
          <textarea rows={3} value={a.freitext} onChange={(e) => setA({ ...a, freitext: e.target.value })} className="w-full rounded-xl border border-linie bg-white p-3 focus:border-wald" placeholder="Optional" />
        </label>
        <Knopf type="submit" className="w-full" disabled={laeuft || !fragen.length}>{laeuft ? "Wird eingeordnet …" : "Absenden"}</Knopf>
        <p className="text-xs text-grau">Deine Antworten gehen an den KI-Dienst für die Einordnung; dein Freitext auch. Philip kann alles lesen.</p>
      </form>
    </main>
  );
}

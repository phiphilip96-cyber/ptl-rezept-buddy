import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Eintrag, Lebensmittel, MAHLZEIT_TEXT, MahlzeitArt, Tag, datumText, heuteIso, tagVerschieben } from "../lib/typen";
import { Eingabe, Fehler, Knopf, Kopf } from "../components/Ui";
import { TabLeiste } from "../components/TabLeiste";

const REIHE: MahlzeitArt[] = ["fruehstueck", "mittag", "snack", "abend"];

function Ring({ wert, ziel }: { wert: number; ziel: number }) {
  const anteil = ziel > 0 ? Math.min(wert / ziel, 1.25) : 0;
  const r = 52, u = 2 * Math.PI * r;
  const ueber = ziel > 0 && wert > ziel * 1.1;
  return (
    <svg viewBox="0 0 128 128" className="w-32 h-32" role="img" aria-label={`${wert} von ${ziel} kcal`}>
      <circle cx="64" cy="64" r={r} fill="none" stroke="var(--color-linie)" strokeWidth="10" />
      <circle cx="64" cy="64" r={r} fill="none" stroke={ueber ? "var(--color-warn)" : "var(--color-wald)"} strokeWidth="10"
        strokeLinecap="round" strokeDasharray={u} strokeDashoffset={u * (1 - Math.min(anteil, 1))} transform="rotate(-90 64 64)" />
      <text x="64" y="60" textAnchor="middle" className="fill-tinte" fontSize="22" fontWeight="700">{wert}</text>
      <text x="64" y="80" textAnchor="middle" className="fill-grau" fontSize="11">von {ziel} kcal</text>
    </svg>
  );
}

export default function Heute() {
  const nav = useNavigate();
  const [datum, setDatum] = useState(heuteIso());
  const [tag, setTag] = useState<Tag | null>(null);
  const [neu, setNeu] = useState<MahlzeitArt | null>(null);
  const [gewicht, setGewicht] = useState("");
  const [gewichtOk, setGewichtOk] = useState<string | null>(null);
  const [aktiv, setAktiv] = useState<{ titel: string; start_datum: string } | null | undefined>(undefined);

  useEffect(() => {
    (async () => {
      const prof = await api.get<{ profil: unknown }>("/profil");
      if (!prof.profil) { nav("/profil", { replace: true }); return; }
      setAktiv((await api.get<{ aktiver_plan: any }>("/tagebuch/aktiver-plan")).aktiver_plan);
    })();
  }, []);
  useEffect(() => { setTag(null); api.get<Tag>(`/tagebuch/${datum}`).then(setTag); }, [datum]);

  async function abhaken(e: Eintrag) {
    const r = await api.patch<{ tag: Tag }>(`/tagebuch/${datum}/eintraege/${e.id}`, { erledigt: !e.erledigt });
    setTag(r.tag);
  }
  async function loeschen(e: Eintrag) {
    const r = await api.del<{ tag: Tag }>(`/tagebuch/${datum}/eintraege/${e.id}`);
    setTag(r.tag);
  }
  async function gewichtSpeichern(ev: FormEvent) {
    ev.preventDefault();
    const g = parseFloat(gewicht.replace(",", "."));
    if (!g) return;
    await api.put(`/messungen/${datum}`, { gewicht_kg: g });
    setGewicht(""); setGewichtOk(`${g.toLocaleString("de-DE")} kg gespeichert.`); setTimeout(() => setGewichtOk(null), 2500);
  }

  const protAnteil = tag && tag.ziel.protein_g ? Math.min(tag.summe.protein_g / tag.ziel.protein_g, 1) : 0;
  const offenKcal = tag ? Math.max(tag.ziel.kcal - tag.summe.kcal, 0) : 0;
  const offenProt = tag ? Math.max(tag.ziel.protein_g - tag.summe.protein_g, 0) : 0;

  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf
        links={<button onClick={() => setDatum(tagVerschieben(datum, -1))} aria-label="Vortag" className="text-wald text-xl">‹</button>}
        titel={datumText(datum)}
        rechts={<button onClick={() => setDatum(tagVerschieben(datum, 1))} aria-label="Folgetag" className="text-wald text-xl">›</button>}
      />
      <section className="flex-1 px-4 py-4 space-y-5">
        {tag && (
          <div className="rounded-2xl bg-white border border-linie p-4 flex items-center gap-4">
            <Ring wert={tag.summe.kcal} ziel={tag.ziel.kcal} />
            <div className="flex-1 min-w-0">
              <div className="text-sm text-grau">Protein</div>
              <div className="text-xl font-bold">{tag.summe.protein_g} <span className="text-sm font-normal text-grau">/ {tag.ziel.protein_g} g</span></div>
              <div className="h-2 rounded-full bg-linie mt-1 overflow-hidden"><div className="h-full bg-wald" style={{ width: `${protAnteil * 100}%` }} /></div>
              <div className="text-xs text-grau mt-2">{offenKcal > 0 || offenProt > 0 ? `Offen: ${offenKcal} kcal · ${offenProt} g Protein` : "Tagesziel erreicht."}</div>
            </div>
          </div>
        )}

        {aktiv === null && (
          <div className="rounded-2xl bg-wald-hell p-4 text-sm">
            <span className="font-semibold">Kein Wochenplan aktiv.</span> Lass dir im Chat einen erstellen und tippe dort auf „Ab Montag aktiv“ – dann stehen deine Mahlzeiten hier schon drin.
            <Link to="/chat" className="block mt-2 font-semibold text-wald">Zum Chat</Link>
          </div>
        )}

        {tag && REIHE.map((m) => {
          const liste = tag.eintraege.filter((e) => e.mahlzeit === m);
          return (
            <div key={m}>
              <div className="flex items-baseline justify-between mb-1">
                <h2 className="font-semibold">{MAHLZEIT_TEXT[m]}</h2>
                <button onClick={() => setNeu(m)} className="text-sm text-wald font-medium">+ Eintrag</button>
              </div>
              {!liste.length && <div className="text-sm text-grau py-1">Nichts gebucht.</div>}
              <ul className="rounded-2xl bg-white border border-linie divide-y divide-linie overflow-hidden">
                {liste.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-3 py-2.5">
                    <button onClick={() => abhaken(e)} aria-pressed={e.erledigt} aria-label={e.erledigt ? "Erledigt" : "Abhaken"}
                      className={`w-7 h-7 shrink-0 rounded-full border-2 flex items-center justify-center text-sm ${e.erledigt ? "bg-wald border-wald text-white" : "border-linie"}`}>{e.erledigt ? "✓" : ""}</button>
                    <div className="flex-1 min-w-0">
                      <div className={`leading-snug ${e.erledigt ? "" : "text-grau"}`}>{e.bezeichnung}</div>
                      <div className="text-xs text-grau">{Math.round(e.kcal)} kcal · {Math.round(e.protein_g)} g P{e.menge_g ? ` · ${e.menge_g} g` : ""}{e.quelle === "plan" ? " · aus Plan" : e.quelle === "buddy" ? " · vom Buddy" : ""}</div>
                    </div>
                    <button onClick={() => loeschen(e)} aria-label="Löschen" className="text-grau px-1">×</button>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}

        <form onSubmit={gewichtSpeichern} className="rounded-2xl bg-white border border-linie p-4">
          <div className="text-sm text-grau mb-2">Gewicht {datum === heuteIso() ? "heute" : "an diesem Tag"}</div>
          <div className="flex gap-2">
            <Eingabe inputMode="decimal" placeholder="z. B. 62,4" value={gewicht} onChange={(e) => setGewicht(e.target.value)} />
            <Knopf type="submit" variante="leise" disabled={!gewicht}>Speichern</Knopf>
          </div>
          {gewichtOk && <p className="text-sm text-wald mt-2">{gewichtOk}</p>}
        </form>

        <Link to="/chat" className="block text-center text-sm text-wald font-medium py-2">Buddy fragen: „Was esse ich noch heute?“</Link>
      </section>

      {neu && tag && <EintragSheet datum={datum} mahlzeit={neu} onFertig={(t) => { setTag(t); setNeu(null); }} onZu={() => setNeu(null)} />}
      <TabLeiste />
    </main>
  );
}

function EintragSheet({ datum, mahlzeit, onFertig, onZu }: { datum: string; mahlzeit: MahlzeitArt; onFertig: (t: Tag) => void; onZu: () => void }) {
  const [modus, setModus] = useState<"suche" | "frei">("suche");
  const [q, setQ] = useState(""); const [treffer, setTreffer] = useState<Lebensmittel[]>([]);
  const [wahl, setWahl] = useState<Lebensmittel | null>(null); const [menge, setMenge] = useState("100");
  const [frei, setFrei] = useState({ bezeichnung: "", kcal: "", protein_g: "" });
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (q.trim().length < 2) { setTreffer([]); return; }
    const t = setTimeout(() => api.get<{ treffer: Lebensmittel[] }>(`/lebensmittel?q=${encodeURIComponent(q.trim())}`).then((d) => setTreffer(d.treffer)).catch(() => setTreffer([])), 250);
    return () => clearTimeout(t);
  }, [q]);

  async function buchen(e: FormEvent) {
    e.preventDefault(); setFehler(null);
    try {
      let body;
      if (modus === "suche") {
        if (!wahl) { setFehler("Bitte ein Lebensmittel wählen."); return; }
        const g = parseFloat(menge.replace(",", ".")) || 0; const f = g / 100;
        body = { mahlzeit, quelle: "bls", ref_id: wahl.bls_code, bezeichnung: `${wahl.name_de} (${g} g)`, menge_g: g,
                 kcal: Math.round(wahl.kcal_100g * f), protein_g: Math.round(wahl.protein_g * f * 10) / 10,
                 fett_g: wahl.fett_g != null ? Math.round(wahl.fett_g * f * 10) / 10 : null, kh_g: wahl.kh_g != null ? Math.round(wahl.kh_g * f * 10) / 10 : null };
      } else {
        body = { mahlzeit, quelle: "frei", bezeichnung: frei.bezeichnung, kcal: parseFloat(frei.kcal.replace(",", ".")) || 0, protein_g: parseFloat(frei.protein_g.replace(",", ".")) || 0 };
      }
      const r = await api.post<{ tag: Tag }>(`/tagebuch/${datum}/eintraege`, body);
      onFertig(r.tag);
    } catch (err: any) { setFehler(err.message || "Hat nicht geklappt."); }
  }
  const g = parseFloat(menge.replace(",", ".")) || 0;

  return (
    <div className="fixed inset-0 z-20 bg-tinte/40 flex items-end" onClick={onZu}>
      <form onSubmit={buchen} onClick={(e) => e.stopPropagation()} className="w-full max-w-md mx-auto bg-papier rounded-t-3xl p-4 space-y-3" style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        <div className="flex items-center justify-between">
          <div className="font-semibold">{MAHLZEIT_TEXT[mahlzeit]} · Eintrag</div>
          <button type="button" onClick={onZu} className="text-grau px-2" aria-label="Schließen">×</button>
        </div>
        <div className="flex gap-2">
          {(["suche", "frei"] as const).map((m) => (
            <button type="button" key={m} onClick={() => setModus(m)} className={`h-9 px-4 rounded-full text-sm font-medium ${modus === m ? "bg-wald text-white" : "bg-white border border-linie"}`}>{m === "suche" ? "Lebensmittel suchen" : "Frei eintragen"}</button>
          ))}
        </div>
        {modus === "suche" ? (
          <>
            <Eingabe autoFocus placeholder="z. B. Haferflocken" value={q} onChange={(e) => { setQ(e.target.value); setWahl(null); }} />
            {!wahl && treffer.length > 0 && (
              <ul className="rounded-2xl bg-white border border-linie divide-y divide-linie max-h-48 overflow-y-auto">
                {treffer.map((t) => (
                  <li key={t.bls_code ?? t.name_de}><button type="button" onClick={() => { setWahl(t); setQ(t.name_de); }} className="w-full text-left px-3 py-2">
                    <span className="block text-[15px]">{t.name_de}</span><span className="block text-xs text-grau">{Math.round(t.kcal_100g)} kcal · {t.protein_g} g P je 100 g</span>
                  </button></li>
                ))}
              </ul>
            )}
            {q.trim().length >= 2 && !treffer.length && !wahl && <p className="text-xs text-grau">Kein Treffer. Die Lebensmittel-Datenbank ist noch nicht geladen oder der Begriff passt nicht – nutze „Frei eintragen“.</p>}
            {wahl && (
              <div className="flex items-center gap-3">
                <Eingabe inputMode="decimal" value={menge} onChange={(e) => setMenge(e.target.value)} aria-label="Menge in Gramm" />
                <span className="text-sm text-grau whitespace-nowrap">g → {Math.round(wahl.kcal_100g * g / 100)} kcal, {Math.round(wahl.protein_g * g / 100)} g P</span>
              </div>
            )}
          </>
        ) : (
          <>
            <Eingabe autoFocus placeholder="Was war es?" value={frei.bezeichnung} onChange={(e) => setFrei({ ...frei, bezeichnung: e.target.value })} required />
            <div className="grid grid-cols-2 gap-2">
              <Eingabe inputMode="decimal" placeholder="kcal" value={frei.kcal} onChange={(e) => setFrei({ ...frei, kcal: e.target.value })} required />
              <Eingabe inputMode="decimal" placeholder="Protein (g)" value={frei.protein_g} onChange={(e) => setFrei({ ...frei, protein_g: e.target.value })} />
            </div>
          </>
        )}
        <Fehler text={fehler} />
        <Knopf type="submit" className="w-full">Buchen</Knopf>
      </form>
    </div>
  );
}

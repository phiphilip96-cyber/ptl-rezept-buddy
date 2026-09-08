import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Ampel, Checkin, Konversation, Messung, Nachricht, Profil, TagKurz, Trend, ZIEL_TEXT } from "../lib/typen";
import { GewichtsKurve } from "./Ich";

const AMPEL_FARBE: Record<Ampel["farbe"], string> = { gruen: "bg-green-500", gelb: "bg-amber-400", rot: "bg-red-500", grau: "bg-linie" };
import { Markdown } from "../lib/markdown";
import { Auswahl, Eingabe, Fehler, Feld, Knopf, Kopf, Leer } from "../components/Ui";

interface KundeZeile { id: string; email: string; vorname: string; aktiv: boolean; ziel: string | null; chats: number; letzte_aktivitaet: string | null; ampel?: Ampel }
interface Uebersicht { ampel: Ampel; bilanz: TagKurz[]; messungen: Messung[]; gewicht: Trend; letzter_checkin: Checkin | null; aktiver_plan: { titel: string; start_datum: string } | null }

export function CoachLogin() {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [fehler, setFehler] = useState<string | null>(null);
  const nav = useNavigate();
  async function login(e: FormEvent) {
    e.preventDefault(); setFehler(null);
    try { await api.post("/auth/coach/login", { email, passwort: pw }); nav("/coach"); }
    catch { setFehler("E-Mail oder Passwort stimmt nicht."); }
  }
  return (
    <main className="min-h-dvh max-w-md mx-auto px-6 pt-20">
      <h1 className="text-3xl font-bold">Coach-Bereich</h1>
      <form onSubmit={login} className="mt-8 space-y-3">
        <Eingabe type="email" placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Eingabe type="password" placeholder="Passwort" value={pw} onChange={(e) => setPw(e.target.value)} required />
        <Fehler text={fehler} />
        <Knopf type="submit" className="w-full">Anmelden</Knopf>
      </form>
    </main>
  );
}

export function CoachKunden() {
  const [kunden, setKunden] = useState<KundeZeile[] | null>(null);
  const [neu, setNeu] = useState(false);
  const [email, setEmail] = useState(""); const [vorname, setVorname] = useState("");
  const [link, setLink] = useState<string | null>(null); const [fehler, setFehler] = useState<string | null>(null);
  const laden = () => api.get<{ kunden: KundeZeile[] }>("/coach/kunden").then((d) => setKunden(d.kunden));
  useEffect(() => { laden(); }, []);

  async function anlegen(e: FormEvent) {
    e.preventDefault(); setFehler(null);
    try {
      const r = await api.post<{ id: string; magic_link: string | null }>("/coach/kunden", { email, vorname });
      setLink(r.magic_link); setEmail(""); setVorname(""); if (!r.magic_link) setNeu(false); laden();
    } catch (err: any) { setFehler(err.message); }
  }

  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel="Kunden" rechts={<Link to="/coach/regeln" className="text-wald text-sm">Regeln</Link>} />
      <div className="px-4 py-4">
        {neu ? (
          <form onSubmit={anlegen} className="rounded-2xl bg-white border border-linie p-4 space-y-3">
            <Feld label="Vorname"><Eingabe value={vorname} onChange={(e) => setVorname(e.target.value)} required /></Feld>
            <Feld label="E-Mail"><Eingabe type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Feld>
            <Fehler text={fehler} />
            {link && <div className="text-xs break-all rounded-xl bg-wald-hell p-3"><span className="font-semibold">Kein Mailversand konfiguriert.</span> Schick diesen Link selbst (30 Min gültig): {link}</div>}
            <div className="flex gap-2">
              <Knopf type="submit" className="flex-1">Anlegen und Link schicken</Knopf>
              <Knopf type="button" variante="leise" onClick={() => { setNeu(false); setLink(null); }}>Abbrechen</Knopf>
            </div>
          </form>
        ) : (
          <Knopf className="w-full" onClick={() => setNeu(true)}>Kunde anlegen</Knopf>
        )}
        {kunden && !kunden.length && <Leer titel="Noch keine Kunden." text="Leg den ersten an – er bekommt sofort seinen Login-Link." />}
        <ul className="mt-4 divide-y divide-linie">
          {kunden?.map((k) => (
            <li key={k.id}>
              <Link to={`/coach/kunden/${k.id}`} className={`flex items-center gap-3 py-3 ${k.aktiv ? "" : "opacity-50"}`}>
                <span className="relative w-10 h-10 rounded-full bg-wald-hell text-wald font-bold flex items-center justify-center">{k.vorname.slice(0, 1)}
                  {k.ampel && <span className={`absolute -right-0.5 -bottom-0.5 w-3.5 h-3.5 rounded-full border-2 border-papier ${AMPEL_FARBE[k.ampel.farbe]}`} title={k.ampel.gruende.join(", ")} />}</span>
                <span className="flex-1 min-w-0">
                  <span className="block font-medium">{k.vorname} <span className="text-grau font-normal text-sm">{k.ziel ? ZIEL_TEXT[k.ziel as keyof typeof ZIEL_TEXT] : "kein Profil"}</span></span>
                  <span className="block text-xs text-grau">{k.ampel?.gruende[0] ?? `${k.chats} Chats`}{k.letzte_aktivitaet ? ` · zuletzt ${new Date(k.letzte_aktivitaet).toLocaleDateString("de-DE")}` : ""}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}

export function CoachKunde() {
  const { id } = useParams();
  const nav = useNavigate();
  const [profil, setProfil] = useState<Profil | null>(null);
  const [konvs, setKonvs] = useState<Konversation[]>([]);
  const [tab, setTab] = useState<"woche" | "chats" | "profil">("woche");
  const [meldung, setMeldung] = useState<string | null>(null);
  const [ue, setUe] = useState<Uebersicht | null>(null);
  const [kommentar, setKommentar] = useState("");
  const ladenUe = () => api.get<Uebersicht>(`/coach/kunden/${id}/uebersicht`).then(setUe);

  async function kommentarSenden(e: FormEvent) {
    e.preventDefault(); if (!ue?.letzter_checkin || !kommentar.trim()) return;
    await api.post(`/coach/checkins/${ue.letzter_checkin.id}/kommentar`, { inhalt: kommentar }); setKommentar(""); ladenUe();
  }

  useEffect(() => {
    ladenUe();
    api.get<{ profil: Profil | null }>(`/coach/kunden/${id}/profil`).then((d) => setProfil(d.profil));
    api.get<{ konversationen: Konversation[] }>(`/coach/kunden/${id}/konversationen`).then((d) => setKonvs(d.konversationen));
  }, [id]);

  async function speichern(e: FormEvent) {
    e.preventDefault(); if (!profil) return;
    const r = await api.put<{ profil: Profil }>(`/coach/kunden/${id}/profil`, profil);
    setProfil(r.profil); setMeldung("Gespeichert."); setTimeout(() => setMeldung(null), 2000);
  }
  async function loeschen() {
    if (!confirm("Kunde inkl. aller Chats und Pläne endgültig löschen?")) return;
    await api.del(`/coach/kunden/${id}`); nav("/coach");
  }
  const set = <K extends keyof Profil>(k: K, v: Profil[K]) => setProfil((p) => (p ? { ...p, [k]: v } : p));

  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel={profil?.vorname ?? "Kunde"} links={<Link to="/coach" className="text-wald">Zurück</Link>} />
      <div className="px-4 pt-3 flex gap-2">
        {(["woche", "chats", "profil"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`h-10 px-4 rounded-full font-medium ${tab === t ? "bg-wald text-white" : "bg-white border border-linie"}`}>{t === "woche" ? "Woche" : t === "chats" ? "Chats" : "Profil & Ziele"}</button>
        ))}
      </div>

      {tab === "woche" && (ue ? (
        <div className="px-4 py-4 space-y-4">
          <div className="rounded-2xl bg-white border border-linie p-4">
            <div className="flex items-center gap-2"><span className={`w-3 h-3 rounded-full ${AMPEL_FARBE[ue.ampel.farbe]}`} /><span className="font-semibold capitalize">{ue.ampel.farbe === "gruen" ? "Grün" : ue.ampel.farbe === "gelb" ? "Gelb" : ue.ampel.farbe === "rot" ? "Rot" : "Keine Daten"}</span></div>
            <ul className="text-sm text-grau mt-1 list-disc pl-5">{ue.ampel.gruende.map((g) => <li key={g}>{g}</li>)}</ul>
            {ue.aktiver_plan && <p className="text-sm mt-2">Aktiver Plan: {ue.aktiver_plan.titel} (seit {ue.aktiver_plan.start_datum})</p>}
          </div>
          <div className="rounded-2xl bg-white border border-linie p-4">
            <h3 className="font-semibold">Bilanz 7 Tage</h3>
            {!ue.bilanz.length && <p className="text-sm text-grau mt-1">Noch nichts getrackt.</p>}
            <ul className="mt-2 space-y-1 text-sm">
              {ue.bilanz.map((t) => (
                <li key={t.datum} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${t.erledigt === 0 ? "bg-linie" : t.im_korridor ? "bg-green-500" : "bg-amber-400"}`} />
                  <span className="w-24 text-grau">{t.datum.slice(8)}.{t.datum.slice(5, 7)}.</span>
                  <span>{t.kcal} / {t.ziel_kcal} kcal · {t.protein_g} / {t.ziel_protein_g} g P</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl bg-white border border-linie p-4">
            <div className="flex items-baseline justify-between"><h3 className="font-semibold">Gewicht</h3>{ue.gewicht.differenz_kg != null && <span className="text-sm text-grau">{ue.gewicht.differenz_kg > 0 ? "+" : ""}{ue.gewicht.differenz_kg} kg / 4 Wo.</span>}</div>
            <div className="mt-2"><GewichtsKurve messungen={ue.messungen} /></div>
          </div>
          <div className="rounded-2xl bg-white border border-linie p-4">
            <h3 className="font-semibold">Letzter Check-in</h3>
            {ue.letzter_checkin ? (
              <>
                <div className="text-xs text-grau mt-1">{ue.letzter_checkin.woche} · Schlaf {ue.letzter_checkin.antworten.schlaf} · Energie {ue.letzter_checkin.antworten.energie} · Hunger {ue.letzter_checkin.antworten.hunger} · Stress {ue.letzter_checkin.antworten.stress} · Plan {ue.letzter_checkin.antworten.plan_eingehalten} · Training {ue.letzter_checkin.antworten.training_einheiten}×</div>
                {ue.letzter_checkin.antworten.freitext && <p className="text-sm mt-2 italic">„{ue.letzter_checkin.antworten.freitext}“</p>}
                {ue.letzter_checkin.buddy_zusammenfassung && <p className="text-sm mt-2"><span className="font-semibold">Buddy:</span> {ue.letzter_checkin.buddy_zusammenfassung}</p>}
                {ue.letzter_checkin.coach_kommentar && <p className="text-sm mt-2 rounded-xl bg-wald-hell p-3"><span className="font-semibold">Du:</span> {ue.letzter_checkin.coach_kommentar}</p>}
                <form onSubmit={kommentarSenden} className="mt-3 flex gap-2">
                  <input value={kommentar} onChange={(e) => setKommentar(e.target.value)} placeholder="Kommentar an den Kunden …" className="flex-1 h-11 rounded-xl border border-linie bg-white px-3 focus:border-wald" />
                  <button type="submit" className="h-11 px-4 rounded-full bg-wald text-white font-semibold">Senden</button>
                </form>
              </>
            ) : <p className="text-sm text-grau mt-1">Noch kein Check-in.</p>}
          </div>
        </div>
      ) : <p className="px-4 py-6 text-sm text-grau">Lade …</p>)}

      {tab === "chats" && (
        <div className="px-4 py-4">
          {!konvs.length && <Leer titel="Noch kein Chat." text="Sobald der Kunde mit dem Buddy schreibt, siehst du es hier." />}
          <ul className="divide-y divide-linie">
            {konvs.map((k) => (
              <li key={k.id}><Link to={`/coach/chats/${k.id}`} className="block py-3">
                <span className="block font-medium truncate">{k.titel}</span>
                <span className="block text-xs text-grau">{new Date(k.letzte_nachricht_am).toLocaleString("de-DE")}</span>
              </Link></li>
            ))}
          </ul>
        </div>
      )}

      {tab === "profil" && (profil ? (
        <form onSubmit={speichern} className="px-4 py-4 space-y-4">
          <div className="rounded-2xl bg-white border border-linie p-4 text-sm space-y-1">
            <div>{ZIEL_TEXT[profil.ziel]} · {profil.gewicht_kg} kg · {profil.groesse_cm} cm · Jg. {profil.geburtsjahr} · {profil.ernaehrungsart}</div>
            <div>Unverträglichkeiten: {profil.unvertraeglichkeiten.join(", ") || "keine"} · Abneigungen: {profil.abneigungen.join(", ") || "keine"}</div>
            <div>{profil.mahlzeiten_pro_tag} Mahlzeiten · max. {profil.kochzeit_max_min} Min · Budget {profil.budget}</div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Feld label="Kalorienziel" hinweis={`Auto: ${profil.kalorienziel_effektiv ?? "–"}`}>
              <Eingabe type="number" inputMode="numeric" placeholder="automatisch" value={profil.kalorienziel ?? ""} onChange={(e) => set("kalorienziel", e.target.value ? +e.target.value : null)} />
            </Feld>
            <Feld label="Protein (g)" hinweis={`Auto: ${profil.proteinziel_effektiv ?? "–"}`}>
              <Eingabe type="number" inputMode="numeric" placeholder="automatisch" value={profil.proteinziel_g ?? ""} onChange={(e) => set("proteinziel_g", e.target.value ? +e.target.value : null)} />
            </Feld>
          </div>
          <Feld label="Ziel">
            <Auswahl value={profil.ziel} onChange={(e) => set("ziel", e.target.value as any)}>
              {Object.entries(ZIEL_TEXT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Auswahl>
          </Feld>
          <Feld label="Notizen für den Buddy" hinweis="Fließen in jeden Chat ein, z. B. Trainingstage, Pre-Workout-Snack.">
            <textarea rows={4} value={profil.notizen_coach} onChange={(e) => set("notizen_coach", e.target.value)} className="w-full rounded-xl border border-linie bg-white p-3 focus:border-wald" />
          </Feld>
          <Knopf type="submit" className="w-full">Speichern</Knopf>
          {meldung && <p className="text-sm text-wald text-center">{meldung}</p>}
          <button type="button" onClick={loeschen} className="w-full text-sm text-warn pt-6">Kunde und alle Daten löschen</button>
        </form>
      ) : <Leer titel="Noch kein Profil." text="Der Kunde hat sein Profil noch nicht ausgefüllt." />)}
    </main>
  );
}

export function CoachChat() {
  const { id } = useParams();
  const nav = useNavigate();
  const [nachrichten, setNachrichten] = useState<(Nachricht & { tokens_in?: number; tokens_out?: number })[]>([]);
  const [notiz, setNotiz] = useState("");
  const laden = () => api.get<{ nachrichten: any[] }>(`/coach/konversationen/${id}/nachrichten`).then((d) => setNachrichten(d.nachrichten));
  useEffect(() => { laden(); const t = setInterval(laden, 5000); return () => clearInterval(t); }, [id]);

  async function senden(e: FormEvent) {
    e.preventDefault(); if (!notiz.trim()) return;
    await api.post(`/coach/konversationen/${id}/notiz`, { inhalt: notiz }); setNotiz(""); laden();
  }
  const tokens = nachrichten.reduce((s, n) => s + (n.tokens_in ?? 0) + (n.tokens_out ?? 0), 0);

  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf titel="Chat mitlesen" links={<button onClick={() => nav(-1)} className="text-wald">Zurück</button>} rechts={<span className="text-xs text-grau">{(tokens / 1000).toFixed(1)}k Tok.</span>} />
      <section className="flex-1 px-4 py-4 space-y-4">
        {nachrichten.map((n) => (
          <div key={n.id} className={n.rolle === "kunde" ? "flex justify-end" : ""}>
            {n.rolle === "kunde" ? <div className="max-w-[85%] rounded-2xl bg-wald text-white px-4 py-2.5 whitespace-pre-wrap">{n.inhalt}</div>
              : n.rolle === "coach" ? <div className="rounded-2xl bg-wald-hell px-4 py-3 text-sm"><span className="font-semibold">Du:</span> {n.inhalt}</div>
              : <div><Markdown text={n.inhalt} />{n.plan_ids.length > 0 && <div className="text-xs text-grau mt-1">{n.plan_ids.length} Plan gespeichert</div>}</div>}
          </div>
        ))}
      </section>
      <form onSubmit={senden} className="sticky bottom-0 bg-papier border-t border-linie px-3 py-2 flex gap-2">
        <input value={notiz} onChange={(e) => setNotiz(e.target.value)} placeholder="Notiz an Buddy und Kunde …" className="flex-1 h-12 rounded-2xl border border-linie bg-white px-4 focus:border-wald" />
        <button type="submit" className="h-12 px-4 rounded-full bg-wald text-white font-semibold">Senden</button>
      </form>
    </main>
  );
}

export function CoachRegeln() {
  const [text, setText] = useState(""); const [meldung, setMeldung] = useState<string | null>(null);
  useEffect(() => { api.get<{ inhalt: string }>("/coach/prompt").then((d) => setText(d.inhalt)); }, []);
  async function speichern() {
    await api.put("/coach/prompt", { inhalt: text }); setMeldung("Gespeichert – gilt ab dem nächsten Chat."); setTimeout(() => setMeldung(null), 3000);
  }
  return (
    <main className="min-h-dvh max-w-md mx-auto flex flex-col">
      <Kopf titel="Buddy-Regeln" links={<Link to="/coach" className="text-wald">Zurück</Link>} />
      <div className="px-4 py-4 flex-1 flex flex-col gap-3">
        <p className="text-sm text-grau">Das ist der Charakter des Buddys. Änderungen wirken sofort, die alte Fassung wird gesichert.</p>
        <textarea value={text} onChange={(e) => setText(e.target.value)} className="flex-1 min-h-[60vh] rounded-xl border border-linie bg-white p-3 text-sm font-mono focus:border-wald" />
        <Knopf onClick={speichern}>Speichern</Knopf>
        {meldung && <p className="text-sm text-wald text-center">{meldung}</p>}
      </div>
    </main>
  );
}

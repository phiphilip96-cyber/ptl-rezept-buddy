import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Profil as ProfilTyp, ZIEL_TEXT } from "../lib/typen";
import { Auswahl, Chips, Eingabe, Fehler, Feld, Knopf, Kopf } from "../components/Ui";

const LEER: ProfilTyp = {
  vorname: "", ziel: "muskelaufbau", gewicht_kg: 70, groesse_cm: 170, geburtsjahr: 1995, geschlecht: "weiblich",
  aktivitaet: "leicht", ernaehrungsart: "alles", unvertraeglichkeiten: [], abneigungen: [],
  kalorienziel: null, proteinziel_g: null, mahlzeiten_pro_tag: 3, kochzeit_max_min: 30, budget: "normal", notizen_coach: "",
};

export default function Profil({ erstesMal = false }: { erstesMal?: boolean }) {
  const [p, setP] = useState<ProfilTyp>(LEER);
  const [vorschlaege, setVorschlaege] = useState<string[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  const [neu, setNeu] = useState(erstesMal);
  const nav = useNavigate();

  useEffect(() => {
    api.get<{ profil: ProfilTyp | null; vorschlaege_unvertraeglichkeiten: string[] }>("/profil").then((d) => {
      setVorschlaege(d.vorschlaege_unvertraeglichkeiten);
      if (d.profil) setP(d.profil); else setNeu(true);
    });
  }, []);

  const set = <K extends keyof ProfilTyp>(k: K, v: ProfilTyp[K]) => setP((alt) => ({ ...alt, [k]: v }));
  const toggle = (feld: "unvertraeglichkeiten" | "abneigungen") => (w: string) =>
    set(feld, p[feld].includes(w) ? p[feld].filter((x) => x !== w) : [...p[feld], w]);

  async function speichern(e: FormEvent) {
    e.preventDefault(); setLaeuft(true); setFehler(null);
    try { await api.put("/profil", p); nav(neu ? "/chat" : "/ich"); }
    catch (err: any) { setFehler(err.message || "Speichern hat nicht geklappt."); }
    finally { setLaeuft(false); }
  }

  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel={neu ? "Dein Profil" : "Profil"} links={!neu && <button onClick={() => nav("/ich")} className="text-wald">Zurück</button>} />
      <form onSubmit={speichern} className="px-4 py-5 space-y-5">
        {neu && <p className="text-grau">Der Buddy braucht das einmal, damit jeder Plan wirklich zu dir passt. Dauert zwei Minuten.</p>}

        <Feld label="Vorname"><Eingabe required value={p.vorname} onChange={(e) => set("vorname", e.target.value)} /></Feld>

        <Feld label="Dein Ziel">
          <div className="grid grid-cols-2 gap-2">
            {(Object.keys(ZIEL_TEXT) as (keyof typeof ZIEL_TEXT)[]).map((z) => (
              <button type="button" key={z} onClick={() => set("ziel", z)} aria-pressed={p.ziel === z}
                className={`h-12 rounded-xl border font-medium ${p.ziel === z ? "bg-wald text-white border-wald" : "bg-white border-linie"}`}>
                {ZIEL_TEXT[z]}
              </button>
            ))}
          </div>
        </Feld>

        <div className="grid grid-cols-3 gap-3">
          <Feld label="Gewicht (kg)"><Eingabe type="number" inputMode="decimal" step="0.5" min={31} max={299} required value={p.gewicht_kg} onChange={(e) => set("gewicht_kg", +e.target.value)} /></Feld>
          <Feld label="Größe (cm)"><Eingabe type="number" inputMode="numeric" min={121} max={229} required value={p.groesse_cm} onChange={(e) => set("groesse_cm", +e.target.value)} /></Feld>
          <Feld label="Geburtsjahr"><Eingabe type="number" inputMode="numeric" min={1921} max={2019} required value={p.geburtsjahr} onChange={(e) => set("geburtsjahr", +e.target.value)} /></Feld>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Feld label="Geschlecht">
            <Auswahl value={p.geschlecht} onChange={(e) => set("geschlecht", e.target.value as any)}>
              <option value="weiblich">weiblich</option><option value="maennlich">männlich</option><option value="divers">divers</option>
            </Auswahl>
          </Feld>
          <Feld label="Alltag">
            <Auswahl value={p.aktivitaet} onChange={(e) => set("aktivitaet", e.target.value as any)}>
              <option value="sitzend">meist sitzend</option><option value="leicht">leicht aktiv</option>
              <option value="mittel">mittel aktiv</option><option value="hoch">sehr aktiv</option>
            </Auswahl>
          </Feld>
        </div>

        <Feld label="Ernährungsart">
          <Auswahl value={p.ernaehrungsart} onChange={(e) => set("ernaehrungsart", e.target.value as any)}>
            <option value="alles">Ich esse alles</option><option value="vegetarisch">Vegetarisch</option>
            <option value="vegan">Vegan</option><option value="pescetarisch">Pescetarisch</option>
          </Auswahl>
        </Feld>

        <Feld label="Unverträglichkeiten" hinweis="Die hält der Buddy ohne Ausnahme ein.">
          <Chips werte={vorschlaege} aktiv={p.unvertraeglichkeiten} onToggle={toggle("unvertraeglichkeiten")} frei onFrei={toggle("unvertraeglichkeiten")} />
        </Feld>

        <Feld label="Magst du nicht" hinweis="Enter drücken zum Hinzufügen, z. B. Pilze, Koriander.">
          <Chips werte={[]} aktiv={p.abneigungen} onToggle={toggle("abneigungen")} frei onFrei={toggle("abneigungen")} />
        </Feld>

        <div className="grid grid-cols-3 gap-3">
          <Feld label="Mahlzeiten/Tag">
            <Auswahl value={p.mahlzeiten_pro_tag} onChange={(e) => set("mahlzeiten_pro_tag", +e.target.value)}>
              {[3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </Auswahl>
          </Feld>
          <Feld label="Max. Kochzeit">
            <Auswahl value={p.kochzeit_max_min} onChange={(e) => set("kochzeit_max_min", +e.target.value)}>
              {[15, 20, 30, 45, 60].map((n) => <option key={n} value={n}>{n} Min</option>)}
            </Auswahl>
          </Feld>
          <Feld label="Budget">
            <Auswahl value={p.budget} onChange={(e) => set("budget", e.target.value as any)}>
              <option value="guenstig">günstig</option><option value="normal">normal</option><option value="egal">egal</option>
            </Auswahl>
          </Feld>
        </div>

        {p.kalorienziel_effektiv && (
          <div className="rounded-2xl bg-wald-hell p-4 text-sm">
            <span className="font-semibold">Dein Tagesziel:</span> ca. {p.kalorienziel_effektiv} kcal und {p.proteinziel_effektiv} g Protein.
            {p.kalorienziel ? " Von Philip festgelegt." : " Automatisch berechnet – Philip kann es anpassen."}
          </div>
        )}

        <Fehler text={fehler} />
        <Knopf type="submit" className="w-full" disabled={laeuft}>{neu ? "Speichern und loslegen" : "Speichern"}</Knopf>
        <p className="text-xs text-grau">Deine Profildaten werden zur Erstellung deiner Pläne an einen KI-Dienst übermittelt. Philip kann deine Chats mitlesen.</p>
      </form>
    </main>
  );
}

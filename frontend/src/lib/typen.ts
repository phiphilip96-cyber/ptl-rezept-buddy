export type Ziel = "muskelaufbau" | "fettabbau" | "gewicht_halten" | "leistung";

export interface Profil {
  vorname: string; ziel: Ziel; gewicht_kg: number; groesse_cm: number; geburtsjahr: number;
  geschlecht: "weiblich" | "maennlich" | "divers"; aktivitaet: "sitzend" | "leicht" | "mittel" | "hoch";
  ernaehrungsart: "alles" | "vegetarisch" | "vegan" | "pescetarisch";
  unvertraeglichkeiten: string[]; abneigungen: string[];
  kalorienziel: number | null; proteinziel_g: number | null;
  mahlzeiten_pro_tag: number; kochzeit_max_min: number; budget: "guenstig" | "normal" | "egal";
  notizen_coach: string;
  kalorienziel_effektiv?: number; proteinziel_effektiv?: number;
}

export interface Mahlzeit { name: string; gericht: string; kcal?: number; protein_g?: number }
export interface Wochenplan { typ: "wochenplan"; titel?: string; tage: { tag: string; mahlzeiten: Mahlzeit[] }[] }
export interface Rezept {
  typ: "rezept"; titel?: string; portionen?: number; zeit_min?: number;
  zutaten: { menge?: string; name: string }[]; schritte: string[];
  kcal_pro_portion?: number; protein_g_pro_portion?: number;
}
export type PlanDaten = Wochenplan | Rezept;

export interface Plan { id: string; typ: "wochenplan" | "rezept"; titel: string; favorit: boolean; erstellt_am: string; daten?: PlanDaten }
export interface Nachricht { id: string; rolle: "kunde" | "buddy" | "coach"; inhalt: string; plan_ids: string[]; erstellt_am: string; plaene?: Plan[]; laeuft?: boolean }
export interface Konversation { id: string; titel: string; erstellt_am: string; letzte_nachricht_am: string }

export const ZIEL_TEXT: Record<Ziel, string> = {
  muskelaufbau: "Muskelaufbau", fettabbau: "Fettabbau", gewicht_halten: "Gewicht halten", leistung: "Leistung",
};

// ── v2-Module ──
export type MahlzeitArt = "fruehstueck" | "mittag" | "abend" | "snack";
export const MAHLZEIT_TEXT: Record<MahlzeitArt, string> = { fruehstueck: "Frühstück", mittag: "Mittagessen", snack: "Snack", abend: "Abendessen" };
export interface Eintrag {
  id: string; mahlzeit: MahlzeitArt; quelle: "plan" | "rezept" | "bls" | "frei" | "buddy"; bezeichnung: string;
  kcal: number; protein_g: number; fett_g?: number | null; kh_g?: number | null; menge_g?: number | null; erledigt: boolean;
}
export interface Tag { datum: string; eintraege: Eintrag[]; summe: { kcal: number; protein_g: number; fett_g: number; kh_g: number }; ziel: { kcal: number; protein_g: number }; notiz: string }
export interface TagKurz { datum: string; kcal: number; protein_g: number; erledigt: number; ziel_kcal: number; ziel_protein_g: number; im_korridor: boolean }
export interface Lebensmittel { name_de: string; kcal_100g: number; protein_g: number; fett_g?: number; kh_g?: number; bls_code?: string }
export interface Messung { datum: string; gewicht_kg: number | null; umfaenge: Record<string, number> }
export interface Trend { aktuell: number | null; mittel_ende: number | null; mittel_anfang: number | null; differenz_kg: number | null }
export interface CheckinAntworten { schlaf: number; energie: number; hunger: number; stress: number; plan_eingehalten: number; training_einheiten: number; freitext: string }
export interface Checkin { id: string; woche: string; antworten: CheckinAntworten; buddy_zusammenfassung: string; coach_kommentar: string | null; erstellt_am: string }
export interface CheckinFrage { feld: keyof CheckinAntworten; frage: string; skala: number }
export interface Ampel { farbe: "gruen" | "gelb" | "rot" | "grau"; gruende: string[]; treffer: number; gezaehlt: number; checkin_ok: boolean; inaktiv_tage: number | null; gewicht_trend_kg: number | null }
export interface Einkaufsliste { kategorien: { name: string; artikel: { menge: string; name: string }[] }[]; quelle: string }

export function heuteIso(): string {
  const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
export function tagVerschieben(iso: string, tage: number): string {
  const [j, m, t] = iso.split("-").map(Number); const d = new Date(j, m - 1, t + tage);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
export function datumText(iso: string): string {
  const h = heuteIso();
  if (iso === h) return "Heute";
  if (iso === tagVerschieben(h, -1)) return "Gestern";
  if (iso === tagVerschieben(h, 1)) return "Morgen";
  const [j, m, t] = iso.split("-").map(Number);
  return new Date(j, m - 1, t).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });
}

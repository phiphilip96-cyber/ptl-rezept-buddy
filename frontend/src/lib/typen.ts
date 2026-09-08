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

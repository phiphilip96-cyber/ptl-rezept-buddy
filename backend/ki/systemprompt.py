from datetime import date
from pathlib import Path
from config import einstellungen
from models.profil import ProfilEingabe, ziele_auffuellen

ZIEL_TEXT = {"muskelaufbau": "Muskelaufbau", "fettabbau": "Fettabbau",
             "gewicht_halten": "Gewicht halten", "leistung": "Leistung"}
BUDGET_TEXT = {"guenstig": "günstig", "normal": "normal", "egal": "egal"}
AKT_TEXT = {"sitzend": "sitzend", "leicht": "leicht aktiv", "mittel": "mittel aktiv", "hoch": "sehr aktiv"}


def prompt_pfad(pfad: str | None = None) -> Path:
    p = Path(pfad or einstellungen.PROMPT_DATEI)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


def regeln_laden(pfad: str | None = None) -> str:
    return prompt_pfad(pfad).read_text(encoding="utf-8")


def profilblock(p: ProfilEingabe, heute: date | None = None) -> str:
    heute = heute or date.today()
    kcal, protein = ziele_auffuellen(p, heute.year)
    alter = heute.year - p.geburtsjahr
    unv = ", ".join(p.unvertraeglichkeiten) if p.unvertraeglichkeiten else "keine"
    abn = ", ".join(p.abneigungen) if p.abneigungen else "keine"
    zeilen = [
        "KUNDENPROFIL",
        f"Vorname: {p.vorname} · Ziel: {ZIEL_TEXT[p.ziel]} · Gewicht: {p.gewicht_kg:g} kg · Größe: {p.groesse_cm} cm · Alter: {alter}",
        f"Ernährungsart: {p.ernaehrungsart} · Aktivität: {AKT_TEXT[p.aktivitaet]}",
        f"Unverträglichkeiten (ABSOLUT): {unv} · Abneigungen: {abn}",
        f"Tagesziel: ca. {kcal} kcal, {protein} g Protein · {p.mahlzeiten_pro_tag} Mahlzeiten · max. {p.kochzeit_max_min} Min Kochzeit · Budget {BUDGET_TEXT[p.budget]}",
    ]
    if p.notizen_coach.strip():
        zeilen.append(f"Coach-Notizen: {p.notizen_coach.strip()}")
    zeilen.append(f"Heutiges Datum: {heute.strftime('%d.%m.%Y')}")
    return "\n".join(zeilen)


def systemprompt_bauen(p: ProfilEingabe, coach_notizen: list[str] | None = None,
                       regeln: str | None = None, heute: date | None = None) -> str:
    teile = [regeln if regeln is not None else regeln_laden(), profilblock(p, heute)]
    if coach_notizen:
        teile.append("AKTUELLE NOTIZEN VOM COACH (haben Vorrang):\n- " + "\n- ".join(coach_notizen))
    return "\n\n".join(teile)

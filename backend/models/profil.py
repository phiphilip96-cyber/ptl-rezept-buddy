from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Ziel = Literal["muskelaufbau", "fettabbau", "gewicht_halten", "leistung"]
Geschlecht = Literal["weiblich", "maennlich", "divers"]
Aktivitaet = Literal["sitzend", "leicht", "mittel", "hoch"]
Ernaehrungsart = Literal["alles", "vegetarisch", "vegan", "pescetarisch"]
Budget = Literal["guenstig", "normal", "egal"]

UNVERTRAEGLICHKEITEN_VORSCHLAEGE = [
    "gluten", "laktose", "nüsse", "soja", "ei", "fisch", "schalentiere", "histamin",
]


class ProfilEingabe(BaseModel):
    vorname: str = Field(min_length=1, max_length=40)
    ziel: Ziel
    gewicht_kg: float = Field(gt=30, lt=300)
    groesse_cm: int = Field(gt=120, lt=230)
    geburtsjahr: int = Field(gt=1920, lt=2020)
    geschlecht: Geschlecht
    aktivitaet: Aktivitaet = "leicht"
    ernaehrungsart: Ernaehrungsart = "alles"
    unvertraeglichkeiten: list[str] = []
    abneigungen: list[str] = []
    kalorienziel: int | None = None
    proteinziel_g: int | None = None
    mahlzeiten_pro_tag: int = Field(default=3, ge=3, le=5)
    kochzeit_max_min: int = Field(default=30, ge=10, le=120)
    budget: Budget = "normal"
    notizen_coach: str = ""


class Profil(ProfilEingabe):
    kunde_id: str
    aktualisiert_am: datetime


AKTIVITAETS_FAKTOR = {"sitzend": 1.2, "leicht": 1.375, "mittel": 1.55, "hoch": 1.725}
ZIEL_OFFSET = {"muskelaufbau": 250, "fettabbau": -400, "gewicht_halten": 0, "leistung": 150}
PROTEIN_G_PRO_KG = {"muskelaufbau": 2.0, "fettabbau": 2.0, "gewicht_halten": 1.6, "leistung": 1.6}


def kalorienziel_berechnen(p: ProfilEingabe, jahr: int) -> int:
    """Mifflin-St Jeor × Aktivität ± Ziel-Offset. Fallback, wenn der Coach nichts gesetzt hat."""
    alter = jahr - p.geburtsjahr
    grund = 10 * p.gewicht_kg + 6.25 * p.groesse_cm - 5 * alter
    grund += 5 if p.geschlecht == "maennlich" else -161
    gesamt = grund * AKTIVITAETS_FAKTOR[p.aktivitaet] + ZIEL_OFFSET[p.ziel]
    return int(round(gesamt / 50.0) * 50)


def proteinziel_berechnen(p: ProfilEingabe) -> int:
    return int(round(p.gewicht_kg * PROTEIN_G_PRO_KG[p.ziel]))


def ziele_auffuellen(p: ProfilEingabe, jahr: int) -> tuple[int, int]:
    kcal = p.kalorienziel or kalorienziel_berechnen(p, jahr)
    protein = p.proteinziel_g or proteinziel_berechnen(p)
    return kcal, protein

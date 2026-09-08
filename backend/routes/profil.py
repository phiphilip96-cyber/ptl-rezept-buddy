from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from auth import aktueller_kunde
from db import db
from models.profil import ProfilEingabe, UNVERTRAEGLICHKEITEN_VORSCHLAEGE, ziele_auffuellen

router = APIRouter(tags=["profil"])


def profil_ausgabe(doc: dict | None) -> dict | None:
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    doc["kunde_id"] = str(doc["kunde_id"])
    p = ProfilEingabe(**{k: v for k, v in doc.items() if k in ProfilEingabe.model_fields})
    kcal, protein = ziele_auffuellen(p, datetime.now().year)
    doc["kalorienziel_effektiv"], doc["proteinziel_effektiv"] = kcal, protein
    return doc


@router.get("/profil")
async def profil_lesen(kunde=Depends(aktueller_kunde)):
    doc = await db().profile.find_one({"kunde_id": kunde["_id"]})
    return {"profil": profil_ausgabe(doc), "vorschlaege_unvertraeglichkeiten": UNVERTRAEGLICHKEITEN_VORSCHLAEGE}


@router.put("/profil")
async def profil_schreiben(eingabe: ProfilEingabe, kunde=Depends(aktueller_kunde)):
    daten = eingabe.model_dump()
    # Kalorien-/Proteinziel und Coach-Notizen setzt nur der Coach
    alt = await db().profile.find_one({"kunde_id": kunde["_id"]}) or {}
    for feld in ("kalorienziel", "proteinziel_g", "notizen_coach"):
        daten[feld] = alt.get(feld, daten[feld] if feld == "notizen_coach" else None)
    daten["kunde_id"] = kunde["_id"]
    daten["aktualisiert_am"] = datetime.now(timezone.utc)
    await db().profile.update_one({"kunde_id": kunde["_id"]}, {"$set": daten}, upsert=True)
    await db().kunden.update_one({"_id": kunde["_id"]}, {"$set": {"vorname": eingabe.vorname}})
    return {"profil": profil_ausgabe(await db().profile.find_one({"kunde_id": kunde["_id"]}))}


VORSCHLAGSFRAGEN = {
    "muskelaufbau": ["Bitte erstelle einen Ernährungsplan für nächste Woche",
                     "Was ist ein proteinreiches Frühstück für mich?",
                     "Was esse ich vor und nach dem Training?",
                     "Gib mir ein schnelles Abendessen mit viel Protein"],
    "fettabbau": ["Bitte erstelle einen Ernährungsplan für nächste Woche",
                  "Was ist ein sättigendes Abendessen unter 500 kcal?",
                  "Welche Snacks passen zu meinem Ziel?",
                  "Was esse ich, wenn ich unterwegs bin?"],
    "gewicht_halten": ["Bitte erstelle einen Ernährungsplan für nächste Woche",
                       "Gib mir drei einfache Mittagessen fürs Büro",
                       "Was wäre ein gutes Frühstück?",
                       "Wie plane ich ein Wochenende mit Essen gehen?"],
    "leistung": ["Bitte erstelle einen Ernährungsplan für nächste Woche",
                 "Was esse ich am Tag vor dem Wettkampf?",
                 "Wie sieht ein guter Pre-Workout-Snack aus?",
                 "Gib mir ein kohlenhydratreiches Abendessen"],
}


@router.get("/vorschlagsfragen")
async def vorschlagsfragen(kunde=Depends(aktueller_kunde)):
    doc = await db().profile.find_one({"kunde_id": kunde["_id"]})
    ziel = (doc or {}).get("ziel", "gewicht_halten")
    return {"fragen": VORSCHLAGSFRAGEN.get(ziel, VORSCHLAGSFRAGEN["gewicht_halten"])}

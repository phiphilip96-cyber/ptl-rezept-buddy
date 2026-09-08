from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import aktueller_kunde
from db import db
from ki import einkauf
from zeit import datum_parsen, heute, naechster_montag

router = APIRouter(prefix="/plaene", tags=["plaene"])


def plan_ausgabe(p: dict, mit_daten: bool = True) -> dict:
    out = {"id": str(p["_id"]), "typ": p["typ"], "titel": p["titel"], "favorit": p.get("favorit", False),
           "erstellt_am": p["erstellt_am"].isoformat()}
    if mit_daten:
        out["daten"] = p["daten"]
    return out


class FavoritEingabe(BaseModel):
    favorit: bool


class AktivierenEingabe(BaseModel):
    start_datum: str | None = None  # Standard: naechster Montag (heute, wenn Montag)


class EinkaufslisteEingabe(BaseModel):
    personen: int = 1
    neu: bool = False


@router.get("")
async def plaene_liste(kunde=Depends(aktueller_kunde)):
    cursor = db().plaene.find({"kunde_id": kunde["_id"]}).sort([("favorit", -1), ("erstellt_am", -1)])
    return {"plaene": [plan_ausgabe(p, mit_daten=False) async for p in cursor]}


@router.get("/{plan_id}")
async def plan_lesen(plan_id: str, kunde=Depends(aktueller_kunde)):
    p = await db().plaene.find_one({"_id": ObjectId(plan_id), "kunde_id": kunde["_id"]})
    if not p:
        raise HTTPException(404, "Plan nicht gefunden")
    return plan_ausgabe(p)


@router.patch("/{plan_id}")
async def plan_favorit(plan_id: str, eingabe: FavoritEingabe, kunde=Depends(aktueller_kunde)):
    res = await db().plaene.update_one({"_id": ObjectId(plan_id), "kunde_id": kunde["_id"]}, {"$set": {"favorit": eingabe.favorit}})
    if res.matched_count == 0:
        raise HTTPException(404, "Plan nicht gefunden")
    return {"ok": True}


@router.put("/{plan_id}/aktivieren")
async def plan_aktivieren(plan_id: str, eingabe: AktivierenEingabe, kunde=Depends(aktueller_kunde)):
    """M1: Dieser Wochenplan belegt ab start_datum die Tage im Tagebuch vor."""
    p = await db().plaene.find_one({"_id": ObjectId(plan_id), "kunde_id": kunde["_id"]})
    if not p or p["typ"] != "wochenplan":
        raise HTTPException(404, "Wochenplan nicht gefunden")
    start = eingabe.start_datum or naechster_montag(heute()).isoformat()
    try:
        datum_parsen(start)
    except ValueError:
        raise HTTPException(400, "start_datum als YYYY-MM-DD")
    await db().kunden.update_one({"_id": kunde["_id"]}, {"$set": {"aktiver_plan": {"plan_id": p["_id"], "start_datum": start}}})
    # Tage ab Start, die schon leer angelegt wurden, neu vorbelegen lassen
    await db().tagebuch.delete_many({"kunde_id": kunde["_id"], "datum": {"$gte": start}, "eintraege": []})
    return {"ok": True, "aktiver_plan": {"plan_id": plan_id, "start_datum": start}}


@router.post("/{plan_id}/einkaufsliste")
async def einkaufsliste(plan_id: str, eingabe: EinkaufslisteEingabe, kunde=Depends(aktueller_kunde)):
    """M2: Einkaufsliste zum Plan; fuer Wochenplaene einmal vom Buddy erzeugt und am Plan gecacht."""
    p = await db().plaene.find_one({"_id": ObjectId(plan_id), "kunde_id": kunde["_id"]})
    if not p:
        raise HTTPException(404, "Plan nicht gefunden")
    liste = None if eingabe.neu else p.get("einkaufsliste")
    if not liste:
        if p["typ"] == "rezept":
            liste = einkauf.aus_rezept(p["daten"])
        else:
            try:
                liste = await einkauf.aus_wochenplan(p["daten"], max(1, min(eingabe.personen, 8)))
            except Exception:  # noqa: BLE001
                raise HTTPException(503, "Die Einkaufsliste konnte gerade nicht erstellt werden – bitte gleich nochmal.")
        await db().plaene.update_one({"_id": p["_id"]}, {"$set": {"einkaufsliste": liste}})
    return {"einkaufsliste": liste, "text": einkauf.als_text(liste, f"Einkaufsliste – {p['titel']}")}

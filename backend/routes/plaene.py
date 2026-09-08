from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import aktueller_kunde
from db import db

router = APIRouter(prefix="/plaene", tags=["plaene"])


def plan_ausgabe(p: dict, mit_daten: bool = True) -> dict:
    out = {"id": str(p["_id"]), "typ": p["typ"], "titel": p["titel"], "favorit": p.get("favorit", False),
           "erstellt_am": p["erstellt_am"].isoformat()}
    if mit_daten:
        out["daten"] = p["daten"]
    return out


class FavoritEingabe(BaseModel):
    favorit: bool


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

"""M1 — Tracking + Tagesbilanz.

Ein Dokument je Kunde und Tag (Collection `tagebuch`). Der aktive Wochenplan
(kunden.aktiver_plan) belegt einen Tag beim ersten Oeffnen mit seinen Mahlzeiten
vor (quelle=plan, erledigt=false); gezaehlt wird nur, was abgehakt ist.
Die Funktionen unten sind die einzige Schreibstelle — Buddy-Werkzeuge und
Routen rufen sie, kein Modul greift direkt in die Collection.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from auth import aktueller_kunde
from db import db
from models.profil import ProfilEingabe, ziele_auffuellen
from zeit import WOCHENTAGE, datum_parsen, heute

router = APIRouter(prefix="/tagebuch", tags=["tagebuch"])

Mahlzeit = Literal["fruehstueck", "mittag", "abend", "snack"]
Quelle = Literal["plan", "rezept", "bls", "frei", "buddy"]
MAHLZEIT_NAME = {"fruehstueck": "Frühstück", "mittag": "Mittagessen", "abend": "Abendessen", "snack": "Snack"}
MAHLZEIT_REIHE = ["fruehstueck", "mittag", "snack", "abend"]
KORRIDOR = 0.10


def mahlzeit_aus_name(name: str) -> str:
    n = (name or "").lower()
    if "früh" in n or "frueh" in n or "breakfast" in n:
        return "fruehstueck"
    if "mittag" in n or "lunch" in n:
        return "mittag"
    if "abend" in n or "dinner" in n:
        return "abend"
    return "snack"


class EintragEingabe(BaseModel):
    mahlzeit: Mahlzeit
    bezeichnung: str = Field(min_length=1, max_length=200)
    kcal: float = Field(ge=0, le=5000)
    protein_g: float = Field(default=0, ge=0, le=500)
    fett_g: float | None = Field(default=None, ge=0, le=500)
    kh_g: float | None = Field(default=None, ge=0, le=1000)
    menge_g: float | None = Field(default=None, gt=0, le=5000)
    quelle: Quelle = "frei"
    ref_id: str | None = None
    erledigt: bool = True


class EintragAenderung(BaseModel):
    erledigt: bool | None = None
    menge_g: float | None = Field(default=None, gt=0, le=5000)
    kcal: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=500)
    bezeichnung: str | None = Field(default=None, min_length=1, max_length=200)


async def ziel_fuer(kunde_id: ObjectId) -> tuple[int, int]:
    doc = await db().profile.find_one({"kunde_id": kunde_id})
    if not doc:
        return 0, 0
    p = ProfilEingabe(**{f: doc[f] for f in ProfilEingabe.model_fields if f in doc})
    return ziele_auffuellen(p, heute().year)


def summe(eintraege: list[dict]) -> dict:
    s = {"kcal": 0.0, "protein_g": 0.0, "fett_g": 0.0, "kh_g": 0.0}
    for e in eintraege:
        if not e.get("erledigt"):
            continue
        for k in s:
            s[k] += float(e.get(k) or 0)
    return {k: round(v) for k, v in s.items()}


async def _vorbelegung_aus_plan(kunde_id: ObjectId, datum: str) -> list[dict]:
    kunde = await db().kunden.find_one({"_id": kunde_id}, {"aktiver_plan": 1})
    aktiv = (kunde or {}).get("aktiver_plan")
    if not aktiv or datum < aktiv["start_datum"]:
        return []
    plan = await db().plaene.find_one({"_id": aktiv["plan_id"], "kunde_id": kunde_id})
    if not plan or plan.get("typ") != "wochenplan":
        return []
    tage = plan["daten"].get("tage") or []
    wochentag = WOCHENTAGE[datum_parsen(datum).weekday()]
    tag = next((t for t in tage if str(t.get("tag", "")).lower().startswith(wochentag.lower()[:2])), None)
    if tag is None:
        offset = (datum_parsen(datum) - datum_parsen(aktiv["start_datum"])).days % max(len(tage), 1)
        tag = tage[offset] if tage else None
    if not tag:
        return []
    jetzt = datetime.now(timezone.utc)
    return [{
        "id": uuid4().hex[:12], "mahlzeit": mahlzeit_aus_name(m.get("name", "")), "quelle": "plan",
        "ref_id": str(plan["_id"]), "bezeichnung": str(m.get("gericht", ""))[:200],
        "kcal": float(m.get("kcal") or 0), "protein_g": float(m.get("protein_g") or 0),
        "erledigt": False, "erstellt_am": jetzt,
    } for m in tag.get("mahlzeiten", [])]


async def tag_laden(kunde_id: ObjectId, datum: str) -> dict:
    """Tag lesen; existiert er nicht, aus dem aktiven Plan vorbelegen (auch leer anlegen)."""
    datum_parsen(datum)  # validiert
    doc = await db().tagebuch.find_one({"kunde_id": kunde_id, "datum": datum})
    if doc is None:
        doc = {"kunde_id": kunde_id, "datum": datum, "eintraege": await _vorbelegung_aus_plan(kunde_id, datum),
               "notiz": "", "aktualisiert_am": datetime.now(timezone.utc)}
        await db().tagebuch.insert_one(doc)
    return doc


async def _speichern(doc: dict) -> None:
    doc["aktualisiert_am"] = datetime.now(timezone.utc)
    await db().tagebuch.update_one({"kunde_id": doc["kunde_id"], "datum": doc["datum"]},
                                   {"$set": {"eintraege": doc["eintraege"], "aktualisiert_am": doc["aktualisiert_am"]}})


async def eintrag_hinzufuegen(kunde_id: ObjectId, datum: str, e: EintragEingabe) -> dict:
    doc = await tag_laden(kunde_id, datum)
    neu = e.model_dump() | {"id": uuid4().hex[:12], "erstellt_am": datetime.now(timezone.utc)}
    doc["eintraege"].append(neu)
    await _speichern(doc)
    return neu


async def eintrag_aendern(kunde_id: ObjectId, datum: str, eid: str, a: EintragAenderung) -> dict:
    doc = await tag_laden(kunde_id, datum)
    for e in doc["eintraege"]:
        if e["id"] == eid:
            for k, v in a.model_dump(exclude_none=True).items():
                e[k] = v
            await _speichern(doc)
            return e
    raise HTTPException(404, "Eintrag nicht gefunden")


async def eintrag_loeschen(kunde_id: ObjectId, datum: str, eid: str) -> None:
    doc = await tag_laden(kunde_id, datum)
    vorher = len(doc["eintraege"])
    doc["eintraege"] = [e for e in doc["eintraege"] if e["id"] != eid]
    if len(doc["eintraege"]) == vorher:
        raise HTTPException(404, "Eintrag nicht gefunden")
    await _speichern(doc)


def _eintrag_ausgabe(e: dict) -> dict:
    out = dict(e)
    out["erstellt_am"] = e["erstellt_am"].isoformat() if isinstance(e.get("erstellt_am"), datetime) else e.get("erstellt_am")
    return out


async def tag_ausgabe(kunde_id: ObjectId, doc: dict) -> dict:
    kcal_ziel, protein_ziel = await ziel_fuer(kunde_id)
    eintraege = sorted(doc["eintraege"], key=lambda e: MAHLZEIT_REIHE.index(e.get("mahlzeit", "snack")))
    return {"datum": doc["datum"], "eintraege": [_eintrag_ausgabe(e) for e in eintraege],
            "summe": summe(doc["eintraege"]), "ziel": {"kcal": kcal_ziel, "protein_g": protein_ziel},
            "notiz": doc.get("notiz", "")}


def im_korridor(kcal: float, ziel: int) -> bool:
    return ziel > 0 and abs(kcal - ziel) <= ziel * KORRIDOR


async def uebersicht(kunde_id: ObjectId, von: str, bis: str) -> list[dict]:
    kcal_ziel, protein_ziel = await ziel_fuer(kunde_id)
    cursor = db().tagebuch.find({"kunde_id": kunde_id, "datum": {"$gte": von, "$lte": bis}}).sort("datum", 1)
    out = []
    async for doc in cursor:
        s = summe(doc["eintraege"])
        erledigt = sum(1 for e in doc["eintraege"] if e.get("erledigt"))
        out.append({"datum": doc["datum"], "kcal": s["kcal"], "protein_g": s["protein_g"], "erledigt": erledigt,
                    "ziel_kcal": kcal_ziel, "ziel_protein_g": protein_ziel,
                    "im_korridor": erledigt > 0 and im_korridor(s["kcal"], kcal_ziel)})
    return out


async def trefferquote(kunde_id: ObjectId, bis=None, tage: int = 7) -> tuple[int, int]:
    """(Tage im Korridor, Tage mit Eintraegen) fuer die letzten `tage` Tage vor `bis` (exklusive heute)."""
    bis = bis or heute()
    von = bis - timedelta(days=tage)
    rows = await uebersicht(kunde_id, von.isoformat(), (bis - timedelta(days=1)).isoformat())
    mit = [r for r in rows if r["erledigt"] > 0]
    return sum(1 for r in mit if r["im_korridor"]), len(mit)


async def bilanz_text(kunde_id: ObjectId, tag=None) -> str:
    """Kurzer Block fuer den Systemprompt: heute gegessen/offen, Trefferquote, aktiver Plan."""
    tag = tag or heute()
    doc = await db().tagebuch.find_one({"kunde_id": kunde_id, "datum": tag.isoformat()})
    kcal_ziel, protein_ziel = await ziel_fuer(kunde_id)
    zeilen = ["TAGEBUCH"]
    if doc:
        s = summe(doc["eintraege"])
        offen = [e["bezeichnung"] for e in doc["eintraege"] if not e.get("erledigt")]
        zeilen.append(f"Heute gebucht: {s['kcal']} kcal, {s['protein_g']} g Protein · offen bis Ziel: "
                      f"{max(kcal_ziel - s['kcal'], 0)} kcal, {max(protein_ziel - s['protein_g'], 0)} g Protein")
        if offen:
            zeilen.append("Noch nicht abgehakt: " + "; ".join(offen[:4]))
    else:
        zeilen.append("Heute noch nichts gebucht.")
    treffer, gezaehlt = await trefferquote(kunde_id, tag)
    if gezaehlt:
        zeilen.append(f"Letzte 7 Tage: {treffer} von {gezaehlt} getrackten Tagen im ±10-%-Korridor.")
    kunde = await db().kunden.find_one({"_id": kunde_id}, {"aktiver_plan": 1})
    aktiv = (kunde or {}).get("aktiver_plan")
    if aktiv:
        plan = await db().plaene.find_one({"_id": aktiv["plan_id"]}, {"titel": 1})
        if plan:
            zeilen.append(f"Aktiver Wochenplan: „{plan['titel']}“ seit {aktiv['start_datum']}.")
    return "\n".join(zeilen)


# ───────────── Routen ─────────────

@router.get("")
async def wochen_uebersicht(von: str = Query(...), bis: str = Query(...), kunde=Depends(aktueller_kunde)):
    datum_parsen(von); datum_parsen(bis)
    return {"tage": await uebersicht(kunde["_id"], von, bis)}


@router.get("/aktiver-plan")
async def aktiver_plan(kunde=Depends(aktueller_kunde)):
    """Steht VOR /{datum}, sonst wuerde der Pfad als Datum gelesen."""
    k = await db().kunden.find_one({"_id": kunde["_id"]}, {"aktiver_plan": 1})
    a = (k or {}).get("aktiver_plan")
    if not a:
        return {"aktiver_plan": None}
    p = await db().plaene.find_one({"_id": a["plan_id"]}, {"titel": 1})
    return {"aktiver_plan": {"plan_id": str(a["plan_id"]), "start_datum": a["start_datum"], "titel": p["titel"] if p else ""}}


@router.get("/{datum}")
async def tag_lesen(datum: str, kunde=Depends(aktueller_kunde)):
    try:
        doc = await tag_laden(kunde["_id"], datum)
    except ValueError:
        raise HTTPException(400, "Datum als YYYY-MM-DD")
    return await tag_ausgabe(kunde["_id"], doc)


@router.post("/{datum}/eintraege")
async def eintrag_anlegen(datum: str, eingabe: EintragEingabe, kunde=Depends(aktueller_kunde)):
    neu = await eintrag_hinzufuegen(kunde["_id"], datum, eingabe)
    return {"eintrag": _eintrag_ausgabe(neu), "tag": await tag_ausgabe(kunde["_id"], await tag_laden(kunde["_id"], datum))}


@router.patch("/{datum}/eintraege/{eid}")
async def eintrag_patch(datum: str, eid: str, eingabe: EintragAenderung, kunde=Depends(aktueller_kunde)):
    await eintrag_aendern(kunde["_id"], datum, eid, eingabe)
    return {"tag": await tag_ausgabe(kunde["_id"], await tag_laden(kunde["_id"], datum))}


@router.delete("/{datum}/eintraege/{eid}")
async def eintrag_entfernen(datum: str, eid: str, kunde=Depends(aktueller_kunde)):
    await eintrag_loeschen(kunde["_id"], datum, eid)
    return {"tag": await tag_ausgabe(kunde["_id"], await tag_laden(kunde["_id"], datum))}

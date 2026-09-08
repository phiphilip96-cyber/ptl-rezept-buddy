"""M3 — Check-ins + Koerperdaten.

messungen: ein Dokument je Kunde und Tag (Gewicht, Umfaenge). checkins: eines
je Kunde und ISO-Woche mit sechs Antworten, einer 3-Satz-Einordnung vom Buddy
und einem optionalen Coach-Kommentar. Fotos sind bewusst NICHT dabei (v2 §M3
verlangt verschluesselte Ablage, das kommt als eigener Schritt).
"""
import logging
from datetime import datetime, timedelta, timezone
from statistics import mean
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from auth import aktueller_kunde
from db import db
from ki import kurz
from zeit import datum_parsen, heute, iso_woche

log = logging.getLogger(__name__)
router = APIRouter(tags=["messungen"])

CHECKIN_FRAGEN = [
    {"feld": "schlaf", "frage": "Wie hast du geschlafen?", "skala": 5},
    {"feld": "energie", "frage": "Wie war deine Energie?", "skala": 5},
    {"feld": "hunger", "frage": "Wie stark war der Hunger?", "skala": 5},
    {"feld": "stress", "frage": "Wie viel Stress hattest du?", "skala": 5},
    {"feld": "plan_eingehalten", "frage": "Wie gut hast du deinen Plan eingehalten?", "skala": 5},
    {"feld": "training_einheiten", "frage": "Wie oft hast du trainiert?", "skala": 7},
]


class Umfaenge(BaseModel):
    taille: float | None = Field(default=None, gt=30, lt=250)
    huefte: float | None = Field(default=None, gt=30, lt=250)
    brust: float | None = Field(default=None, gt=30, lt=250)
    oberarm: float | None = Field(default=None, gt=10, lt=100)
    oberschenkel: float | None = Field(default=None, gt=20, lt=150)


class MessungEingabe(BaseModel):
    gewicht_kg: float | None = Field(default=None, gt=30, lt=300)
    umfaenge: Umfaenge | None = None


class CheckinAntworten(BaseModel):
    schlaf: int = Field(ge=1, le=5)
    energie: int = Field(ge=1, le=5)
    hunger: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    plan_eingehalten: int = Field(ge=1, le=5)
    training_einheiten: int = Field(ge=0, le=14)
    freitext: str = Field(default="", max_length=1000)


class CheckinEingabe(BaseModel):
    antworten: CheckinAntworten
    woche: str | None = None


async def messung_speichern(kunde_id: ObjectId, datum: str, m: MessungEingabe) -> dict:
    datum_parsen(datum)
    daten = {k: v for k, v in m.model_dump(exclude_none=True).items()}
    if "umfaenge" in daten:
        daten["umfaenge"] = {k: v for k, v in daten["umfaenge"].items() if v is not None}
    if not daten:
        raise HTTPException(400, "Nichts zu speichern")
    daten["aktualisiert_am"] = datetime.now(timezone.utc)
    await db().messungen.update_one({"kunde_id": kunde_id, "datum": datum},
                                    {"$set": daten, "$setOnInsert": {"erstellt_am": datetime.now(timezone.utc)}}, upsert=True)
    return await db().messungen.find_one({"kunde_id": kunde_id, "datum": datum})


def _m_ausgabe(m: dict) -> dict:
    return {"datum": m["datum"], "gewicht_kg": m.get("gewicht_kg"), "umfaenge": m.get("umfaenge") or {}}


async def messungen_laden(kunde_id: ObjectId, tage: int = 28, bis=None) -> list[dict]:
    bis = bis or heute()
    von = (bis - timedelta(days=tage)).isoformat()
    cursor = db().messungen.find({"kunde_id": kunde_id, "datum": {"$gte": von, "$lte": bis.isoformat()}}).sort("datum", 1)
    return [_m_ausgabe(m) async for m in cursor]


def gewichtstrend(messungen: list[dict]) -> dict:
    """7-Tage-Mittel am Ende vs. am Anfang des Zeitraums; None, wenn zu wenig Daten."""
    gew = [(m["datum"], m["gewicht_kg"]) for m in messungen if m.get("gewicht_kg")]
    if len(gew) < 2:
        return {"aktuell": gew[-1][1] if gew else None, "mittel_ende": None, "mittel_anfang": None, "differenz_kg": None}
    ende = mean(v for _, v in gew[-7:])
    anfang = mean(v for _, v in gew[:7])
    return {"aktuell": gew[-1][1], "mittel_ende": round(ende, 1), "mittel_anfang": round(anfang, 1),
            "differenz_kg": round(ende - anfang, 1)}


def _checkin_ausgabe(c: dict) -> dict:
    return {"id": str(c["_id"]), "woche": c["woche"], "antworten": c["antworten"],
            "buddy_zusammenfassung": c.get("buddy_zusammenfassung", ""), "coach_kommentar": c.get("coach_kommentar"),
            "erstellt_am": c["erstellt_am"].isoformat()}


async def letzter_checkin(kunde_id: ObjectId) -> dict | None:
    c = await db().checkins.find_one({"kunde_id": kunde_id}, sort=[("woche", -1)])
    return _checkin_ausgabe(c) if c else None


async def _einordnung(kunde_id: ObjectId, antworten: CheckinAntworten) -> str:
    """3 Saetze vom Buddy. Scheitert lautlos (leerer Text), der Check-in bleibt gespeichert."""
    try:
        profil = await db().profile.find_one({"kunde_id": kunde_id}) or {}
        trend = gewichtstrend(await messungen_laden(kunde_id, 28))
        system = ("Du bist der Rezept-Buddy der Personal Training Lounge. Ordne den Wochen-Check-in eines Kunden "
                  "in genau drei kurzen Saetzen ein: Was lief gut, worauf achten, ein konkreter Tipp fuer naechste Woche. "
                  "Du-Form, freundlich, kein medizinischer Rat. Aenderungen am Kalorienziel schlaegst du hoechstens vor "
                  "und verweist auf Philip — du aenderst nichts selbst.")
        text = (f"Ziel: {profil.get('ziel', '?')} · Vorname: {profil.get('vorname', '')}\n"
                f"Antworten (1 = schlecht, 5 = super): Schlaf {antworten.schlaf}, Energie {antworten.energie}, "
                f"Hunger {antworten.hunger}, Stress {antworten.stress}, Plan eingehalten {antworten.plan_eingehalten}, "
                f"Training {antworten.training_einheiten}x\n"
                f"Gewichtstrend 4 Wochen: {trend['differenz_kg']} kg\n"
                f"Freitext: {antworten.freitext or '-'}")
        return await kurz.kurz_antwort(system, text, max_tokens=300)
    except Exception:  # noqa: BLE001
        log.exception("Check-in-Einordnung fehlgeschlagen")
        return ""


async def checkin_speichern(kunde_id: ObjectId, e: CheckinEingabe) -> dict:
    woche = e.woche or iso_woche(heute())
    zusammenfassung = await _einordnung(kunde_id, e.antworten)
    jetzt = datetime.now(timezone.utc)
    await db().checkins.update_one(
        {"kunde_id": kunde_id, "woche": woche},
        {"$set": {"antworten": e.antworten.model_dump(), "buddy_zusammenfassung": zusammenfassung, "aktualisiert_am": jetzt},
         "$setOnInsert": {"erstellt_am": jetzt}}, upsert=True)
    return _checkin_ausgabe(await db().checkins.find_one({"kunde_id": kunde_id, "woche": woche}))


async def koerper_text(kunde_id: ObjectId) -> str:
    """Block fuer den Systemprompt: Gewichtstrend, letzter Check-in, offener Coach-Kommentar."""
    zeilen = ["KOERPERDATEN"]
    trend = gewichtstrend(await messungen_laden(kunde_id, 28))
    if trend["aktuell"]:
        z = f"Gewicht aktuell {trend['aktuell']:g} kg"
        if trend["differenz_kg"] is not None:
            z += f", Trend 4 Wochen {trend['differenz_kg']:+.1f} kg (7-Tage-Mittel)"
        zeilen.append(z + ".")
    else:
        zeilen.append("Noch kein Gewicht erfasst.")
    c = await letzter_checkin(kunde_id)
    if c:
        a = c["antworten"]
        zeilen.append(f"Letzter Check-in {c['woche']}: Schlaf {a['schlaf']}/5, Energie {a['energie']}/5, Hunger {a['hunger']}/5, "
                      f"Stress {a['stress']}/5, Plan {a['plan_eingehalten']}/5, Training {a['training_einheiten']}x.")
        if a.get("freitext"):
            zeilen.append(f"Kunde schrieb: {a['freitext'][:300]}")
        if c.get("coach_kommentar"):
            zeilen.append(f"Coach-Kommentar dazu: {c['coach_kommentar'][:300]}")
    return "\n".join(zeilen)


# ───────────── Routen (Kunde) ─────────────

@router.put("/messungen/{datum}")
async def messung_put(datum: str, eingabe: MessungEingabe, kunde=Depends(aktueller_kunde)):
    try:
        m = await messung_speichern(kunde["_id"], datum, eingabe)
    except ValueError:
        raise HTTPException(400, "Datum als YYYY-MM-DD")
    return {"messung": _m_ausgabe(m)}


@router.get("/messungen")
async def messungen_get(tage: int = Query(default=28, ge=7, le=365), kunde=Depends(aktueller_kunde)):
    ms = await messungen_laden(kunde["_id"], tage)
    return {"messungen": ms, "trend": gewichtstrend(ms)}


@router.get("/checkins/fragen")
async def checkin_fragen(kunde=Depends(aktueller_kunde)):
    return {"fragen": CHECKIN_FRAGEN, "woche": iso_woche(heute())}


@router.get("/checkins")
async def checkins_get(kunde=Depends(aktueller_kunde)):
    cursor = db().checkins.find({"kunde_id": kunde["_id"]}).sort("woche", -1).limit(26)
    return {"checkins": [_checkin_ausgabe(c) async for c in cursor], "aktuelle_woche": iso_woche(heute())}


@router.post("/checkins")
async def checkin_post(eingabe: CheckinEingabe, kunde=Depends(aktueller_kunde)):
    return {"checkin": await checkin_speichern(kunde["_id"], eingabe)}

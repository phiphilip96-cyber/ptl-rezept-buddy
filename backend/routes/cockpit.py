"""M5-light — Ampel je Kunde fuer den Coach.

gruen: >= 5 von 7 getrackten Tagen im Korridor UND Check-in diese/letzte Woche
gelb:  3-4 Tage im Korridor ODER Check-in ueberfaellig
rot:   < 3 Tage im Korridor (bei >= 3 getrackten Tagen) ODER 5 Tage inaktiv
       ODER Gewicht 2 Wochen gegen das Ziel
grau:  noch keine Daten
"""
from datetime import timedelta
from bson import ObjectId
from db import db
from routes.messungen import gewichtstrend, letzter_checkin, messungen_laden
from routes.tagebuch import trefferquote, uebersicht
from zeit import heute, iso_woche


async def letzte_aktivitaet(kunde_id: ObjectId):
    kandidaten = []
    k = await db().konversationen.find_one({"kunde_id": kunde_id}, sort=[("letzte_nachricht_am", -1)])
    if k:
        kandidaten.append(k["letzte_nachricht_am"])
    t = await db().tagebuch.find_one({"kunde_id": kunde_id}, sort=[("aktualisiert_am", -1)])
    if t:
        kandidaten.append(t["aktualisiert_am"])
    m = await db().messungen.find_one({"kunde_id": kunde_id}, sort=[("aktualisiert_am", -1)])
    if m:
        kandidaten.append(m["aktualisiert_am"])
    return max(kandidaten) if kandidaten else None


async def ampel(kunde_id: ObjectId, ziel: str | None = None, tag=None) -> dict:
    tag = tag or heute()
    treffer, gezaehlt = await trefferquote(kunde_id, tag)
    checkin = await letzter_checkin(kunde_id)
    diese, letzte = iso_woche(tag), iso_woche(tag - timedelta(days=7))
    checkin_ok = bool(checkin and checkin["woche"] in (diese, letzte))
    aktiv = await letzte_aktivitaet(kunde_id)
    inaktiv_tage = (tag - aktiv.date()).days if aktiv else None
    trend = gewichtstrend(await messungen_laden(kunde_id, 14, tag))
    gegen_ziel = False
    if trend["differenz_kg"] is not None and ziel:
        gegen_ziel = (ziel == "fettabbau" and trend["differenz_kg"] > 0.5) or (ziel == "muskelaufbau" and trend["differenz_kg"] < -0.5)

    gruende = []
    if gezaehlt == 0 and not checkin and inaktiv_tage is None:
        return {"farbe": "grau", "gruende": ["noch keine Daten"], "treffer": 0, "gezaehlt": 0, "checkin_ok": False,
                "inaktiv_tage": None, "gewicht_trend_kg": None}
    farbe = "gruen"
    if inaktiv_tage is not None and inaktiv_tage >= 5:
        farbe = "rot"; gruende.append(f"{inaktiv_tage} Tage inaktiv")
    if gegen_ziel:
        farbe = "rot"; gruende.append(f"Gewicht {trend['differenz_kg']:+.1f} kg gegen das Ziel")
    if gezaehlt < 3:
        if farbe != "rot":
            farbe = "gelb"
        gruende.append(f"erst {gezaehlt} von 7 Tagen getrackt")
    elif treffer < 3:
        farbe = "rot"; gruende.append(f"nur {treffer} von {gezaehlt} Tagen im Korridor")
    elif treffer < 5 and farbe != "rot":
        farbe = "gelb"; gruende.append(f"{treffer} von {gezaehlt} Tagen im Korridor")
    if not checkin_ok and farbe != "rot":
        farbe = "gelb"; gruende.append("Check-in überfällig")
    if farbe == "gruen":
        gruende.append(f"{treffer} von {gezaehlt} Tagen im Korridor, Check-in da")
    return {"farbe": farbe, "gruende": gruende, "treffer": treffer, "gezaehlt": gezaehlt, "checkin_ok": checkin_ok,
            "inaktiv_tage": inaktiv_tage, "gewicht_trend_kg": trend["differenz_kg"]}


async def kunden_uebersicht(kunde_id: ObjectId, ziel: str | None = None) -> dict:
    tag = heute()
    von = (tag - timedelta(days=6)).isoformat()
    ms = await messungen_laden(kunde_id, 28, tag)
    kunde = await db().kunden.find_one({"_id": kunde_id}, {"aktiver_plan": 1})
    aktiv = (kunde or {}).get("aktiver_plan")
    plan = await db().plaene.find_one({"_id": aktiv["plan_id"]}, {"titel": 1}) if aktiv else None
    return {
        "ampel": await ampel(kunde_id, ziel, tag),
        "bilanz": await uebersicht(kunde_id, von, tag.isoformat()),
        "messungen": ms, "gewicht": gewichtstrend(ms),
        "letzter_checkin": await letzter_checkin(kunde_id),
        "aktiver_plan": {"titel": plan["titel"], "start_datum": aktiv["start_datum"]} if plan else None,
    }

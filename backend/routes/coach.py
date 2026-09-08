from datetime import datetime, timezone
from pathlib import Path
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from auth import aktueller_coach, magic_link_erstellen, mail_senden
from db import db
from ki.systemprompt import prompt_pfad, regeln_laden
from models.chat import NotizEingabe
from models.profil import ProfilEingabe
from routes.chat import konversation_ausgabe, nachricht_ausgabe
from routes.profil import profil_ausgabe

router = APIRouter(prefix="/coach", tags=["coach"])


class KundeAnlegen(BaseModel):
    email: EmailStr
    vorname: str = Field(min_length=1, max_length=40)


class PromptEingabe(BaseModel):
    inhalt: str = Field(min_length=50)


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(404, "Nicht gefunden")


@router.get("/kunden")
async def kunden_liste(coach=Depends(aktueller_coach)):
    kunden = await db().kunden.find().sort("erstellt_am", -1).to_list(length=1000)
    out = []
    for k in kunden:
        letzte = await db().konversationen.find_one({"kunde_id": k["_id"]}, sort=[("letzte_nachricht_am", -1)])
        anzahl = await db().konversationen.count_documents({"kunde_id": k["_id"]})
        profil = await db().profile.find_one({"kunde_id": k["_id"]}, {"ziel": 1})
        out.append({"id": str(k["_id"]), "email": k["email"], "vorname": k.get("vorname", ""), "aktiv": k.get("aktiv", True),
                    "ziel": (profil or {}).get("ziel"), "chats": anzahl,
                    "letzte_aktivitaet": letzte["letzte_nachricht_am"].isoformat() if letzte else None})
    return {"kunden": out}


@router.post("/kunden")
async def kunde_anlegen(eingabe: KundeAnlegen, coach=Depends(aktueller_coach)):
    email = eingabe.email.lower()
    if await db().kunden.find_one({"email": email}):
        raise HTTPException(409, "Kunde existiert bereits")
    res = await db().kunden.insert_one({"email": email, "vorname": eingabe.vorname, "aktiv": True,
                                        "erstellt_am": datetime.now(timezone.utc)})
    link = await magic_link_erstellen(res.inserted_id)
    gesendet = mail_senden(email, "Willkommen beim PTL Rezept-Buddy",
                           f"Hi {eingabe.vorname},\n\nPhilip hat dich für den Rezept-Buddy freigeschaltet. Hier ist dein Login-Link (30 Minuten gültig):\n{link}\n\nDein PTL-Team")
    return {"id": str(res.inserted_id), "magic_link": None if gesendet else link}


@router.patch("/kunden/{kunde_id}/aktiv")
async def kunde_aktiv(kunde_id: str, aktiv: bool, coach=Depends(aktueller_coach)):
    await db().kunden.update_one({"_id": _oid(kunde_id)}, {"$set": {"aktiv": aktiv}})
    return {"ok": True}


@router.delete("/kunden/{kunde_id}")
async def kunde_loeschen(kunde_id: str, coach=Depends(aktueller_coach)):
    """DSGVO: Hard-Delete inkl. Profil, Chats, Pläne."""
    kid = _oid(kunde_id)
    konvs = [k["_id"] async for k in db().konversationen.find({"kunde_id": kid}, {"_id": 1})]
    await db().nachrichten.delete_many({"konversation_id": {"$in": konvs}})
    await db().konversationen.delete_many({"kunde_id": kid})
    await db().plaene.delete_many({"kunde_id": kid})
    await db().profile.delete_many({"kunde_id": kid})
    await db().magic_links.delete_many({"kunde_id": kid})
    await db().kunden.delete_one({"_id": kid})
    return {"ok": True}


@router.get("/kunden/{kunde_id}/profil")
async def profil_lesen(kunde_id: str, coach=Depends(aktueller_coach)):
    return {"profil": profil_ausgabe(await db().profile.find_one({"kunde_id": _oid(kunde_id)}))}


@router.put("/kunden/{kunde_id}/profil")
async def profil_schreiben(kunde_id: str, eingabe: ProfilEingabe, coach=Depends(aktueller_coach)):
    kid = _oid(kunde_id)
    daten = eingabe.model_dump() | {"kunde_id": kid, "aktualisiert_am": datetime.now(timezone.utc)}
    await db().profile.update_one({"kunde_id": kid}, {"$set": daten}, upsert=True)
    await db().kunden.update_one({"_id": kid}, {"$set": {"vorname": eingabe.vorname}})
    return {"profil": profil_ausgabe(await db().profile.find_one({"kunde_id": kid}))}


@router.get("/kunden/{kunde_id}/konversationen")
async def konversationen(kunde_id: str, coach=Depends(aktueller_coach)):
    cursor = db().konversationen.find({"kunde_id": _oid(kunde_id)}).sort("letzte_nachricht_am", -1)
    return {"konversationen": [konversation_ausgabe(k) async for k in cursor]}


@router.get("/konversationen/{konv_id}/nachrichten")
async def nachrichten(konv_id: str, coach=Depends(aktueller_coach)):
    cursor = db().nachrichten.find({"konversation_id": _oid(konv_id)}).sort("erstellt_am", 1)
    out = []
    async for n in cursor:
        d = nachricht_ausgabe(n)
        d["tokens_in"], d["tokens_out"] = n.get("tokens_in", 0), n.get("tokens_out", 0)
        d["tool_aufrufe"] = n.get("tool_aufrufe", [])
        out.append(d)
    return {"nachrichten": out}


@router.post("/konversationen/{konv_id}/notiz")
async def notiz(konv_id: str, eingabe: NotizEingabe, coach=Depends(aktueller_coach)):
    kid = _oid(konv_id)
    if not await db().konversationen.find_one({"_id": kid}):
        raise HTTPException(404, "Chat nicht gefunden")
    jetzt = datetime.now(timezone.utc)
    res = await db().nachrichten.insert_one({"konversation_id": kid, "rolle": "coach", "inhalt": eingabe.inhalt, "erstellt_am": jetzt})
    await db().konversationen.update_one({"_id": kid}, {"$set": {"letzte_nachricht_am": jetzt}})
    return {"id": str(res.inserted_id)}


@router.get("/prompt")
async def prompt_lesen(coach=Depends(aktueller_coach)):
    return {"inhalt": regeln_laden()}


@router.put("/prompt")
async def prompt_schreiben(eingabe: PromptEingabe, coach=Depends(aktueller_coach)):
    pfad = prompt_pfad()
    verlauf = pfad.parent / "verlauf"
    verlauf.mkdir(exist_ok=True)
    if pfad.exists():
        (verlauf / f"{datetime.now().strftime('%Y%m%d-%H%M')}.md").write_text(pfad.read_text(encoding="utf-8"), encoding="utf-8")
    pfad.write_text(eingabe.inhalt, encoding="utf-8")
    return {"ok": True}


@router.get("/kosten")
async def kosten(coach=Depends(aktueller_coach)):
    """Tokens je Monat (letzte 6 Monate). Preis je Mio. Tokens in ENV setzen, sobald bekannt."""
    pipeline = [
        {"$match": {"rolle": "buddy"}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$erstellt_am"}},
                    "tokens_in": {"$sum": "$tokens_in"}, "tokens_out": {"$sum": "$tokens_out"}, "antworten": {"$sum": 1}}},
        {"$sort": {"_id": -1}}, {"$limit": 6},
    ]
    return {"monate": [dict(m, monat=m.pop("_id")) async for m in db().nachrichten.aggregate(pipeline)]}

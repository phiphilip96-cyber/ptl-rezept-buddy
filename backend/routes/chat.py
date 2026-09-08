import json
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from auth import aktueller_kunde
from db import db
from ki import agent as ki_agent
from ki.parser import plaene_extrahieren, titel_ableiten
from ki.systemprompt import systemprompt_bauen
from ki.kontext import kontext_bauen
from ki.werkzeuge import SCHREIBENDE, TOOL_DEFS, werkzeuge_fuer
from models.chat import KonversationEingabe, NachrichtEingabe
from models.profil import ProfilEingabe

log = logging.getLogger(__name__)
router = APIRouter(prefix="/konversationen", tags=["chat"])
VERLAUF_MAX = 20


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(404, "Nicht gefunden")


def nachricht_ausgabe(n: dict) -> dict:
    return {"id": str(n["_id"]), "rolle": n["rolle"], "inhalt": n["inhalt"],
            "plan_ids": [str(p) for p in n.get("plan_ids", [])], "erstellt_am": n["erstellt_am"].isoformat()}


def konversation_ausgabe(k: dict) -> dict:
    return {"id": str(k["_id"]), "titel": k["titel"], "erstellt_am": k["erstellt_am"].isoformat(),
            "letzte_nachricht_am": k["letzte_nachricht_am"].isoformat()}


@router.get("")
async def konversationen_liste(kunde=Depends(aktueller_kunde)):
    cursor = db().konversationen.find({"kunde_id": kunde["_id"]}).sort("letzte_nachricht_am", -1)
    return {"konversationen": [konversation_ausgabe(k) async for k in cursor]}


@router.post("")
async def konversation_anlegen(eingabe: KonversationEingabe, kunde=Depends(aktueller_kunde)):
    jetzt = datetime.now(timezone.utc)
    doc = {"kunde_id": kunde["_id"], "titel": eingabe.titel, "erstellt_am": jetzt, "letzte_nachricht_am": jetzt}
    res = await db().konversationen.insert_one(doc)
    doc["_id"] = res.inserted_id
    return konversation_ausgabe(doc)


async def _konversation_holen(konv_id: str, kunde_id: ObjectId) -> dict:
    k = await db().konversationen.find_one({"_id": _oid(konv_id), "kunde_id": kunde_id})
    if not k:
        raise HTTPException(404, "Chat nicht gefunden")
    return k


@router.get("/{konv_id}/nachrichten")
async def nachrichten_liste(konv_id: str, kunde=Depends(aktueller_kunde)):
    k = await _konversation_holen(konv_id, kunde["_id"])
    cursor = db().nachrichten.find({"konversation_id": k["_id"]}).sort([("erstellt_am", 1), ("_id", 1)])
    return {"nachrichten": [nachricht_ausgabe(n) async for n in cursor]}


async def verlauf_fuer_api(konv_id: ObjectId) -> tuple[list[dict], list[str]]:
    """Letzte Nachrichten als Anthropic-messages; Coach-Notizen werden als user-Nachricht mit Präfix übergeben
    und zusätzlich (die letzten drei) separat für den Systemprompt zurückgegeben."""
    cursor = db().nachrichten.find({"konversation_id": konv_id}).sort([("erstellt_am", -1), ("_id", -1)]).limit(VERLAUF_MAX)
    docs = list(reversed(await cursor.to_list(length=VERLAUF_MAX)))
    messages: list[dict] = []
    coach_notizen: list[str] = []
    for n in docs:
        if n["rolle"] == "buddy":
            rolle, inhalt = "assistant", n.get("inhalt_roh") or n["inhalt"]
        elif n["rolle"] == "coach":
            rolle, inhalt = "user", f"[Notiz vom Coach] {n['inhalt']}"
            coach_notizen.append(n["inhalt"])
        else:
            rolle, inhalt = "user", n["inhalt"]
        if messages and messages[-1]["role"] == rolle:
            messages[-1]["content"] += "\n\n" + inhalt
        else:
            messages.append({"role": rolle, "content": inhalt})
    if messages and messages[0]["role"] == "assistant":
        messages = messages[1:]
    return messages, coach_notizen[-3:]


def _sse(event: str, daten) -> str:
    return f"event: {event}\ndata: {json.dumps(daten, ensure_ascii=False)}\n\n"


@router.post("/{konv_id}/nachrichten")
async def nachricht_senden(konv_id: str, eingabe: NachrichtEingabe, kunde=Depends(aktueller_kunde)):
    k = await _konversation_holen(konv_id, kunde["_id"])
    profil_doc = await db().profile.find_one({"kunde_id": kunde["_id"]})
    if not profil_doc:
        raise HTTPException(400, "Bitte zuerst dein Profil ausfüllen")
    profil = ProfilEingabe(**{f: profil_doc[f] for f in ProfilEingabe.model_fields if f in profil_doc})

    jetzt = datetime.now(timezone.utc)
    await db().nachrichten.insert_one({"konversation_id": k["_id"], "rolle": "kunde", "inhalt": eingabe.inhalt, "erstellt_am": jetzt})
    if k["titel"] == "Neuer Chat":
        await db().konversationen.update_one({"_id": k["_id"]}, {"$set": {"titel": eingabe.inhalt[:60]}})

    messages, coach_notizen = await verlauf_fuer_api(k["_id"])
    try:
        kontext = await kontext_bauen(kunde["_id"])
    except Exception:  # noqa: BLE001 — Kontext ist Zugabe, der Chat muss auch ohne laufen
        log.exception("Kontextblock fehlgeschlagen")
        kontext = None
    system = systemprompt_bauen(profil, coach_notizen, kontext=kontext)
    werkzeuge = werkzeuge_fuer(kunde["_id"])

    async def stream():
        try:
            async for art, daten in ki_agent.buddy_antworten(system, messages, werkzeuge=werkzeuge, werkzeug_defs=TOOL_DEFS):
                if art == "text":
                    yield _sse("text", daten)
                    continue
                ergebnis = daten  # AgentErgebnis
                text_sauber, plaene = plaene_extrahieren(ergebnis.text)
                plan_ids = []
                for plan in plaene:
                    res = await db().plaene.insert_one({
                        "kunde_id": kunde["_id"], "konversation_id": k["_id"], "typ": plan["typ"],
                        "titel": titel_ableiten(plan), "daten": plan, "favorit": False,
                        "erstellt_am": datetime.now(timezone.utc)})
                    plan_ids.append(res.inserted_id)
                    yield _sse("plan_gespeichert", {"plan_id": str(res.inserted_id), "typ": plan["typ"], "titel": titel_ableiten(plan), "daten": plan})
                res = await db().nachrichten.insert_one({
                    "konversation_id": k["_id"], "rolle": "buddy", "inhalt": text_sauber, "inhalt_roh": ergebnis.text,
                    "plan_ids": plan_ids, "tool_aufrufe": ergebnis.tool_aufrufe,
                    "tokens_in": ergebnis.tokens_in, "tokens_out": ergebnis.tokens_out,
                    "erstellt_am": datetime.now(timezone.utc)})
                await db().konversationen.update_one({"_id": k["_id"]}, {"$set": {"letzte_nachricht_am": datetime.now(timezone.utc)}})
                geschrieben = sorted({a["werkzeug"] for a in ergebnis.tool_aufrufe if a.get("werkzeug") in SCHREIBENDE})
                if geschrieben:
                    yield _sse("aktion", {"werkzeuge": geschrieben})
                yield _sse("fertig", {"nachricht_id": str(res.inserted_id), "inhalt": text_sauber, "plan_ids": [str(p) for p in plan_ids]})
        except Exception as e:  # noqa: BLE001
            log.exception("Buddy-Fehler")
            yield _sse("fehler", {"meldung": "Der Buddy ist gerade nicht erreichbar – bitte in einer Minute nochmal."})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

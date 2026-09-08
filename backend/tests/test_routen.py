import json
from datetime import datetime, timezone
import pytest
from bson import ObjectId
from tests.conftest import PROFIL_LENA
from ki import agent as ki_agent
from ki.agent import AgentErgebnis


async def test_profil_anlegen_und_lesen(client, kunde, mockdb):
    r = await client.put("/api/profil", json=PROFIL_LENA)
    assert r.status_code == 200, r.text
    p = r.json()["profil"]
    assert p["kalorienziel_effektiv"] == 2250 and p["kalorienziel"] is None
    r = await client.get("/api/vorschlagsfragen")
    assert "nächste Woche" in r.json()["fragen"][0]


async def test_kunde_kann_kalorienziel_nicht_selbst_setzen(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA | {"kalorienziel": 1200})
    doc = await mockdb.profile.find_one({"kunde_id": kunde})
    assert doc["kalorienziel"] is None


async def test_chat_ohne_profil_abgelehnt(client, kunde):
    k = (await client.post("/api/konversationen", json={})).json()
    r = await client.post(f"/api/konversationen/{k['id']}/nachrichten", json={"inhalt": "Hi"})
    assert r.status_code == 400


async def _buddy_fake(system, verlauf, **kw):
    assert "KUNDENPROFIL" in system and "gluten" in system
    text = 'Gerne!\n```json\n{"typ":"wochenplan","titel":"Plan","tage":[{"tag":"Montag","mahlzeiten":[]}]}\n```'
    for teil in ("Ger", "ne!"):
        yield ("text", teil)
    e = AgentErgebnis(); e.text = text; e.tokens_in, e.tokens_out = 100, 50
    yield ("fertig", e)


async def test_chat_streamt_und_speichert_plan(client, kunde, mockdb, monkeypatch):
    monkeypatch.setattr(ki_agent, "buddy_antworten", _buddy_fake)
    await client.put("/api/profil", json=PROFIL_LENA)
    k = (await client.post("/api/konversationen", json={})).json()
    r = await client.post(f"/api/konversationen/{k['id']}/nachrichten", json={"inhalt": "Bitte erstelle einen Ernährungsplan"})
    assert r.status_code == 200
    body = r.text
    assert "event: text" in body and "event: plan_gespeichert" in body and "event: fertig" in body
    plaene = (await client.get("/api/plaene")).json()["plaene"]
    assert len(plaene) == 1 and plaene[0]["typ"] == "wochenplan"
    nachrichten = (await client.get(f"/api/konversationen/{k['id']}/nachrichten")).json()["nachrichten"]
    assert [n["rolle"] for n in nachrichten] == ["kunde", "buddy"]
    assert "```json" not in nachrichten[1]["inhalt"]
    konv = (await client.get("/api/konversationen")).json()["konversationen"][0]
    assert konv["titel"].startswith("Bitte erstelle")


async def test_coach_notiz_landet_im_systemprompt(client, kunde, mockdb, monkeypatch):
    gesehen = {}

    async def fake(system, verlauf, **kw):
        gesehen["system"], gesehen["verlauf"] = system, verlauf
        e = AgentErgebnis(); e.text = "ok"
        yield ("fertig", e)

    monkeypatch.setattr(ki_agent, "buddy_antworten", fake)
    await client.put("/api/profil", json=PROFIL_LENA)
    k = (await client.post("/api/konversationen", json={})).json()
    await mockdb.nachrichten.insert_one({"konversation_id": ObjectId(k["id"]), "rolle": "coach",
                                         "inhalt": "Bitte mehr Fisch", "erstellt_am": datetime.now(timezone.utc)})
    await client.post(f"/api/konversationen/{k['id']}/nachrichten", json={"inhalt": "Was esse ich heute?"})
    assert "Bitte mehr Fisch" in gesehen["system"]
    assert gesehen["verlauf"][0]["content"].startswith("[Notiz vom Coach]")
    assert gesehen["verlauf"][-1]["role"] == "user"


async def test_coach_flow(client, coach, mockdb):
    r = await client.post("/api/coach/kunden", json={"email": "Neu@Test.de", "vorname": "Neu"})
    assert r.status_code == 200 and r.json()["magic_link"].startswith("http")
    kid = r.json()["id"]
    assert (await client.post("/api/coach/kunden", json={"email": "neu@test.de", "vorname": "Neu"})).status_code == 409
    r = await client.put(f"/api/coach/kunden/{kid}/profil", json=PROFIL_LENA | {"kalorienziel": 1900})
    assert r.json()["profil"]["kalorienziel_effektiv"] == 1900
    liste = (await client.get("/api/coach/kunden")).json()["kunden"]
    assert liste[0]["email"] == "neu@test.de" and liste[0]["ziel"] == "muskelaufbau"
    r = await client.get("/api/coach/prompt")
    assert "Rezept-Buddy" in r.json()["inhalt"]
    assert (await client.delete(f"/api/coach/kunden/{kid}")).status_code == 200
    assert await mockdb.kunden.find_one({"_id": ObjectId(kid)}) is None


async def test_kunde_darf_nicht_in_coach_bereich(client, kunde):
    assert (await client.get("/api/coach/kunden")).status_code == 403


async def test_magic_link_einloesen(client, mockdb):
    kid = ObjectId()
    await mockdb.kunden.insert_one({"_id": kid, "email": "x@y.de", "vorname": "X", "aktiv": True, "erstellt_am": datetime.now(timezone.utc)})
    await client.post("/api/auth/magic-link", json={"email": "x@y.de"})
    link = await mockdb.magic_links.find_one({"kunde_id": kid})
    r = await client.get(f"/api/auth/einloesen?token={link['token']}", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].endswith("/profil")
    assert "ptl_session" in r.headers.get("set-cookie", "")
    # Zweites Einlösen scheitert
    r = await client.get(f"/api/auth/einloesen?token={link['token']}", follow_redirects=False)
    assert "fehler=link" in r.headers["location"]

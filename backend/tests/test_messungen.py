"""M3: Gewicht, Trend, Check-in mit gemockter Buddy-Einordnung, Coach-Kommentar, Ampel."""
from datetime import date, timedelta
from bson import ObjectId
from tests.conftest import PROFIL_LENA
from ki import kurz
from routes import cockpit
from routes.messungen import gewichtstrend

ANTWORTEN = {"schlaf": 4, "energie": 3, "hunger": 2, "stress": 3, "plan_eingehalten": 4, "training_einheiten": 3, "freitext": "War gut"}


async def test_gewicht_speichern_und_trend(client, kunde, mockdb):
    heute = date.today()
    for i, g in enumerate([60.0, 59.8, 59.9, 59.5, 59.4, 59.6, 59.2, 59.0]):
        r = await client.put(f"/api/messungen/{(heute - timedelta(days=7 - i)).isoformat()}", json={"gewicht_kg": g})
        assert r.status_code == 200
    r = await client.get("/api/messungen", params={"tage": 28})
    d = r.json()
    assert len(d["messungen"]) == 8 and d["trend"]["aktuell"] == 59.0
    assert d["trend"]["differenz_kg"] < 0
    # Zweites Speichern am selben Tag ueberschreibt, legt kein zweites Dokument an
    await client.put(f"/api/messungen/{heute.isoformat()}", json={"gewicht_kg": 58.8, "umfaenge": {"taille": 70}})
    d = (await client.get("/api/messungen")).json()
    assert len(d["messungen"]) == 8 and d["messungen"][-1]["gewicht_kg"] == 58.8 and d["messungen"][-1]["umfaenge"]["taille"] == 70
    assert (await client.put(f"/api/messungen/{heute.isoformat()}", json={})).status_code == 400


def test_trend_mit_wenig_daten():
    assert gewichtstrend([])["aktuell"] is None
    assert gewichtstrend([{"datum": "2026-09-01", "gewicht_kg": 70}])["differenz_kg"] is None


async def test_checkin_mit_buddy_einordnung(client, kunde, mockdb, monkeypatch):
    gesehen = {}

    async def fake(system, text, max_tokens=600, client=None):
        gesehen["text"] = text
        return "Gut geschlafen. Hunger niedrig, passt zum Ziel. Nächste Woche: Protein morgens."

    monkeypatch.setattr(kurz, "kurz_antwort", fake)
    await client.put("/api/profil", json=PROFIL_LENA)
    r = await client.get("/api/checkins/fragen")
    assert len(r.json()["fragen"]) == 6
    r = await client.post("/api/checkins", json={"antworten": ANTWORTEN, "woche": "2026-W37"})
    assert r.status_code == 200
    c = r.json()["checkin"]
    assert c["woche"] == "2026-W37" and c["buddy_zusammenfassung"].startswith("Gut geschlafen")
    assert "Schlaf 4" in gesehen["text"] and "War gut" in gesehen["text"]
    # Nochmal dieselbe Woche -> aktualisiert, kein Duplikat
    await client.post("/api/checkins", json={"antworten": ANTWORTEN | {"schlaf": 5}, "woche": "2026-W37"})
    liste = (await client.get("/api/checkins")).json()["checkins"]
    assert len(liste) == 1 and liste[0]["antworten"]["schlaf"] == 5


async def test_checkin_ohne_ki_bleibt_gespeichert(client, kunde, mockdb, monkeypatch):
    async def kaputt(*a, **k):
        raise RuntimeError("kein API-Key")
    monkeypatch.setattr(kurz, "kurz_antwort", kaputt)
    r = await client.post("/api/checkins", json={"antworten": ANTWORTEN})
    assert r.status_code == 200 and r.json()["checkin"]["buddy_zusammenfassung"] == ""


async def test_coach_kommentar_und_uebersicht(client, kunde, mockdb, monkeypatch):
    async def fake(*a, **k):
        return "ok"
    monkeypatch.setattr(kurz, "kurz_antwort", fake)
    await client.put("/api/profil", json=PROFIL_LENA)
    c = (await client.post("/api/checkins", json={"antworten": ANTWORTEN})).json()["checkin"]
    # Coach-Sitzung
    from auth import COOKIE, jwt_erstellen, pw
    cid = ObjectId()
    await mockdb.coaches.insert_one({"_id": cid, "email": "c@t.de", "name": "P", "passwort_hash": pw.hash("x")})
    client.cookies.set(COOKIE, jwt_erstellen(str(cid), "coach"))
    r = await client.post(f"/api/coach/checkins/{c['id']}/kommentar", json={"inhalt": "Stark, weiter so."})
    assert r.status_code == 200
    u = (await client.get(f"/api/coach/kunden/{kunde}/uebersicht")).json()
    assert u["letzter_checkin"]["coach_kommentar"] == "Stark, weiter so."
    assert u["ampel"]["farbe"] in ("gruen", "gelb", "rot")
    liste = (await client.get("/api/coach/kunden")).json()["kunden"]
    assert liste[0]["ampel"]["farbe"] == u["ampel"]["farbe"]


async def test_ampel_stufen(client, kunde, mockdb, monkeypatch):
    async def fake(*a, **k):
        return "ok"
    monkeypatch.setattr(kurz, "kurz_antwort", fake)
    heute = date.today()
    await client.put("/api/profil", json=PROFIL_LENA)
    assert (await cockpit.ampel(kunde, "muskelaufbau", heute))["farbe"] == "grau"
    # 6 Tage im Korridor + Check-in diese Woche -> gruen
    for i in range(1, 7):
        await client.post(f"/api/tagebuch/{(heute - timedelta(days=i)).isoformat()}/eintraege",
                          json={"mahlzeit": "mittag", "bezeichnung": "Tag", "kcal": 2250, "protein_g": 110})
    await client.post("/api/checkins", json={"antworten": ANTWORTEN})
    a = await cockpit.ampel(kunde, "muskelaufbau", heute)
    assert a["farbe"] == "gruen", a
    # Gewicht 2 Wochen gegen das Ziel (Muskelaufbau, aber -1 kg) -> rot
    for i, g in enumerate([60, 60, 60, 60, 60, 60, 60, 59, 59, 59, 59, 59, 59, 59]):
        await client.put(f"/api/messungen/{(heute - timedelta(days=13 - i)).isoformat()}", json={"gewicht_kg": g})
    a = await cockpit.ampel(kunde, "muskelaufbau", heute)
    assert a["farbe"] == "rot" and any("gegen das Ziel" in g for g in a["gruende"])

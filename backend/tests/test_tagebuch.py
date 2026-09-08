"""M1: Tagebuch — Vorbelegung aus aktivem Plan, Abhaken, Summe, Uebersicht, Trefferquote."""
from datetime import date, timedelta
from bson import ObjectId
from tests.conftest import PROFIL_LENA
from routes import tagebuch
from zeit import WOCHENTAGE

PLAN = {"typ": "wochenplan", "titel": "Testplan", "tage": [
    {"tag": t, "mahlzeiten": [
        {"name": "Frühstück", "gericht": f"Porridge {t}", "kcal": 500, "protein_g": 30},
        {"name": "Mittagessen", "gericht": f"Bowl {t}", "kcal": 700, "protein_g": 45},
        {"name": "Abendessen", "gericht": f"Lachs {t}", "kcal": 650, "protein_g": 40}]} for t in WOCHENTAGE]}


async def _plan_anlegen(mockdb, kunde):
    from datetime import datetime, timezone
    res = await mockdb.plaene.insert_one({"kunde_id": kunde, "typ": "wochenplan", "titel": "Testplan", "daten": PLAN,
                                          "favorit": False, "erstellt_am": datetime.now(timezone.utc)})
    return str(res.inserted_id)


async def test_leerer_tag_ohne_plan(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    r = await client.get("/api/tagebuch/2026-09-07")
    assert r.status_code == 200
    d = r.json()
    assert d["eintraege"] == [] and d["summe"]["kcal"] == 0 and d["ziel"]["kcal"] == 2250


async def test_datum_ungueltig(client, kunde, mockdb):
    assert (await client.get("/api/tagebuch/heute")).status_code == 400


async def test_plan_aktivieren_belegt_tage_vor(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    pid = await _plan_anlegen(mockdb, kunde)
    r = await client.put(f"/api/plaene/{pid}/aktivieren", json={"start_datum": "2026-09-07"})  # ein Montag
    assert r.status_code == 200
    r = await client.get("/api/tagebuch/aktiver-plan")
    assert r.json()["aktiver_plan"]["titel"] == "Testplan"
    # Mittwoch -> Mittwochs-Gerichte, nichts abgehakt, Summe 0
    d = (await client.get("/api/tagebuch/2026-09-09")).json()
    assert [e["bezeichnung"] for e in d["eintraege"]] == ["Porridge Mittwoch", "Bowl Mittwoch", "Lachs Mittwoch"]
    assert all(not e["erledigt"] for e in d["eintraege"]) and d["summe"]["kcal"] == 0
    # Vor dem Start bleibt der Tag leer
    assert (await client.get("/api/tagebuch/2026-09-06")).json()["eintraege"] == []


async def test_abhaken_und_summe(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    pid = await _plan_anlegen(mockdb, kunde)
    await client.put(f"/api/plaene/{pid}/aktivieren", json={"start_datum": "2026-09-07"})
    d = (await client.get("/api/tagebuch/2026-09-08")).json()
    eid = d["eintraege"][0]["id"]
    d = (await client.patch(f"/api/tagebuch/2026-09-08/eintraege/{eid}", json={"erledigt": True})).json()["tag"]
    assert d["summe"] == {"kcal": 500, "protein_g": 30, "fett_g": 0, "kh_g": 0}
    r = await client.post("/api/tagebuch/2026-09-08/eintraege", json={"mahlzeit": "snack", "bezeichnung": "Apfel", "kcal": 80, "protein_g": 0.5})
    assert r.status_code == 200 and r.json()["tag"]["summe"]["kcal"] == 580
    neu = r.json()["eintrag"]["id"]
    d = (await client.delete(f"/api/tagebuch/2026-09-08/eintraege/{neu}")).json()["tag"]
    assert d["summe"]["kcal"] == 500
    assert (await client.delete(f"/api/tagebuch/2026-09-08/eintraege/gibtsnicht")).status_code == 404


async def test_uebersicht_und_trefferquote(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)  # Ziel 2250 -> Korridor 2025..2475
    heute = date(2026, 9, 10)
    for i, kcal in enumerate([2200, 2300, 1500, 2400, 900]):  # 3 im Korridor, 2 daneben
        tag = (heute - timedelta(days=i + 1)).isoformat()
        await client.post(f"/api/tagebuch/{tag}/eintraege", json={"mahlzeit": "mittag", "bezeichnung": "Tag", "kcal": kcal, "protein_g": 100})
    r = await client.get("/api/tagebuch", params={"von": "2026-09-01", "bis": "2026-09-10"})
    tage = r.json()["tage"]
    assert len(tage) == 5 and sum(1 for t in tage if t["im_korridor"]) == 3
    treffer, gezaehlt = await tagebuch.trefferquote(kunde, heute)
    assert (treffer, gezaehlt) == (3, 5)
    text = await tagebuch.bilanz_text(kunde, heute)
    assert "3 von 5" in text and "Heute noch nichts gebucht" in text


async def test_bilanz_text_heute(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    heute = date(2026, 9, 10)
    await client.post("/api/tagebuch/2026-09-10/eintraege", json={"mahlzeit": "fruehstueck", "bezeichnung": "Porridge", "kcal": 500, "protein_g": 30})
    await client.post("/api/tagebuch/2026-09-10/eintraege", json={"mahlzeit": "abend", "bezeichnung": "Lachs", "kcal": 650, "protein_g": 40, "erledigt": False})
    text = await tagebuch.bilanz_text(kunde, heute)
    assert "500 kcal, 30 g Protein" in text and "1750 kcal" in text and "Lachs" in text


def test_mahlzeit_aus_name():
    assert tagebuch.mahlzeit_aus_name("Frühstück") == "fruehstueck"
    assert tagebuch.mahlzeit_aus_name("Mittagessen") == "mittag"
    assert tagebuch.mahlzeit_aus_name("Abendessen") == "abend"
    assert tagebuch.mahlzeit_aus_name("Snack 2") == "snack"

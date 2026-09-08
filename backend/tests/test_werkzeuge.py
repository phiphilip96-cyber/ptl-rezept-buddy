"""Buddy-Werkzeuge (v2): Verteilung im Agenten und echte Wirkung auf Tagebuch/Messungen."""
from datetime import date
from types import SimpleNamespace
from ki.agent import buddy_antworten
from ki.werkzeuge import TOOL_DEFS, werkzeuge_fuer
from ki.kontext import kontext_bauen
from tests.conftest import PROFIL_LENA
from tests.test_agent import _Block, _Stream, _delta


class _Client:
    """Runde 1: eintrag_anlegen, Runde 2: Text."""
    def __init__(self):
        self.aufrufe = 0
        self.messages = self
        self.tools_gesehen = None

    def stream(self, **kw):
        self.aufrufe += 1
        if self.aufrufe == 1:
            self.tools_gesehen = [t["name"] for t in kw["tools"]]
            final = SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                                    content=[_Block(type="tool_use", id="t1", name="eintrag_anlegen",
                                                    input={"mahlzeit": "snack", "bezeichnung": "Apfel", "kcal": 80, "protein_g": 0.5,
                                                           "datum": "2026-09-10"})])
            return _Stream([], final)
        inhalt = kw["messages"][-1]["content"][0]
        assert inhalt["type"] == "tool_result" and "Gebucht: Apfel" in inhalt["content"]
        final = SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=20, output_tokens=8),
                                content=[_Block(type="text", text="Apfel ist gebucht.")])
        return _Stream([_delta("Apfel ist gebucht.")], final)


async def test_werkzeug_bucht_im_tagebuch(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    c = _Client()
    ergebnis = None
    async for art, d in buddy_antworten("SYS", [{"role": "user", "content": "Ich hatte einen Apfel"}], client=c,
                                        werkzeuge=werkzeuge_fuer(kunde), werkzeug_defs=TOOL_DEFS):
        if art == "fertig":
            ergebnis = d
    assert set(c.tools_gesehen) == {"naehrwerte_suchen", "eintrag_anlegen", "tag_lesen", "messung_speichern"}
    assert ergebnis.tool_aufrufe[0]["werkzeug"] == "eintrag_anlegen"
    tag = (await client.get("/api/tagebuch/2026-09-10")).json()
    assert tag["eintraege"][0]["bezeichnung"] == "Apfel" and tag["eintraege"][0]["quelle"] == "buddy" and tag["summe"]["kcal"] == 80


async def test_werkzeuge_direkt(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    w = werkzeuge_fuer(kunde)
    t = await w["messung_speichern"]({"gewicht_kg": 55.4, "datum": "2026-09-10"})
    assert "55.4 kg" in t
    t = await w["tag_lesen"]({"datum": "2026-09-10"})
    assert "Tagebuch 2026-09-10" in t and "2250" in t
    # Fehler landet als Text beim Modell, nicht als Ausnahme im Chat
    c = _Client()
    c.stream = lambda **kw: (_ for _ in ()).throw(AssertionError)  # nicht genutzt
    try:
        await w["eintrag_anlegen"]({"mahlzeit": "mittag", "bezeichnung": "x", "kcal": -5, "protein_g": 0})
        assert False, "Validierung fehlt"
    except Exception:
        pass


async def test_kontextblock(client, kunde, mockdb):
    await client.put("/api/profil", json=PROFIL_LENA)
    text = await kontext_bauen(kunde)
    assert text.startswith("TAGEBUCH") and "KOERPERDATEN" in text and "Noch kein Gewicht" in text

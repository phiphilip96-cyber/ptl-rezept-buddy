"""Schreib-Werkzeuge des Buddys (v2). Jedes Werkzeug ruft die Modulfunktion,
nie die Collection direkt. Die Rueckgabe ist der Text, den das Modell sieht."""
from typing import Awaitable, Callable
from bson import ObjectId
from routes import messungen as m_modul
from routes import tagebuch as t_modul
from zeit import datum_parsen, heute

TOOL_DEFS = [
    {
        "name": "eintrag_anlegen",
        "description": "Bucht etwas Gegessenes ins Tagebuch des Kunden (z. B. 'Ich hatte gerade eine Pizza'). "
                       "kcal und Protein kommen aus naehrwerte_suchen × Menge; fehlt die Menge, frag EINMAL nach.",
        "input_schema": {"type": "object", "properties": {
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard heute"},
            "mahlzeit": {"type": "string", "enum": ["fruehstueck", "mittag", "abend", "snack"]},
            "bezeichnung": {"type": "string"},
            "menge_g": {"type": "number"},
            "kcal": {"type": "number"},
            "protein_g": {"type": "number"},
        }, "required": ["mahlzeit", "bezeichnung", "kcal", "protein_g"]},
    },
    {
        "name": "tag_lesen",
        "description": "Liest das Tagebuch eines Tages: gebuchte und offene Mahlzeiten, Summe und Ziel.",
        "input_schema": {"type": "object", "properties": {"datum": {"type": "string", "description": "YYYY-MM-DD, Standard heute"}}},
    },
    {
        "name": "messung_speichern",
        "description": "Speichert das Koerpergewicht des Kunden fuer einen Tag ('wiege heute 55,4').",
        "input_schema": {"type": "object", "properties": {
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard heute"},
            "gewicht_kg": {"type": "number"}}, "required": ["gewicht_kg"]},
    },
]
SCHREIBENDE = {"eintrag_anlegen", "messung_speichern"}


def _datum(eingabe: dict) -> str:
    d = str(eingabe.get("datum") or "").strip()
    if d:
        datum_parsen(d)
        return d
    return heute().isoformat()


def werkzeuge_fuer(kunde_id: ObjectId) -> dict[str, Callable[[dict], Awaitable[str]]]:
    async def eintrag_anlegen(e: dict) -> str:
        eingabe = t_modul.EintragEingabe(
            mahlzeit=e.get("mahlzeit", "snack"), bezeichnung=str(e.get("bezeichnung", ""))[:200],
            kcal=float(e.get("kcal") or 0), protein_g=float(e.get("protein_g") or 0),
            menge_g=(float(e["menge_g"]) if e.get("menge_g") else None), quelle="buddy", erledigt=True)
        datum = _datum(e)
        await t_modul.eintrag_hinzufuegen(kunde_id, datum, eingabe)
        doc = await t_modul.tag_laden(kunde_id, datum)
        s = t_modul.summe(doc["eintraege"])
        ziel_kcal, ziel_p = await t_modul.ziel_fuer(kunde_id)
        return (f"Gebucht: {eingabe.bezeichnung} ({eingabe.kcal:.0f} kcal, {eingabe.protein_g:.0f} g Protein). "
                f"Tagesstand {datum}: {s['kcal']} von {ziel_kcal} kcal, {s['protein_g']} von {ziel_p} g Protein.")

    async def tag_lesen(e: dict) -> str:
        datum = _datum(e)
        doc = await t_modul.tag_laden(kunde_id, datum)
        aus = await t_modul.tag_ausgabe(kunde_id, doc)
        zeilen = [f"Tagebuch {datum}: {aus['summe']['kcal']} von {aus['ziel']['kcal']} kcal, "
                  f"{aus['summe']['protein_g']} von {aus['ziel']['protein_g']} g Protein."]
        for x in aus["eintraege"]:
            zeilen.append(f"- [{'x' if x['erledigt'] else ' '}] {t_modul.MAHLZEIT_NAME[x['mahlzeit']]}: {x['bezeichnung']} "
                          f"({x['kcal']:.0f} kcal, {x['protein_g']:.0f} g P)")
        return "\n".join(zeilen)

    async def messung_speichern(e: dict) -> str:
        datum = _datum(e)
        m = m_modul.MessungEingabe(gewicht_kg=float(e["gewicht_kg"]))
        await m_modul.messung_speichern(kunde_id, datum, m)
        trend = m_modul.gewichtstrend(await m_modul.messungen_laden(kunde_id, 28))
        t = f" Trend 4 Wochen: {trend['differenz_kg']:+.1f} kg." if trend["differenz_kg"] is not None else ""
        return f"Gespeichert: {m.gewicht_kg:g} kg am {datum}.{t}"

    return {"eintrag_anlegen": eintrag_anlegen, "tag_lesen": tag_lesen, "messung_speichern": messung_speichern}

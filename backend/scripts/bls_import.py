"""BLS 4.0 (CSV) → Collection lebensmittel.
Aufruf:  python scripts/bls_import.py data/bls4.csv
Erwartete Spalten (Namen werden tolerant gesucht, Groß/Klein egal):
  Code / BLS-Code, Name / Lebensmittelname, Energie kcal, Protein g, Fett g, Kohlenhydrate g, Ballaststoffe g, Kategorie/Gruppe
Alle Nährwerte je 100 g. Trennzeichen wird automatisch erkannt (; oder ,), Dezimalkomma wird verstanden."""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import db, indexe_anlegen  # noqa: E402

SPALTEN = {
    "bls_code": ["bls_code", "code", "bls-code", "blscode", "sbls"],
    "name_de": ["name_de", "name", "lebensmittel", "lebensmittelname", "bezeichnung"],
    "kcal_100g": ["kcal", "energie_kcal", "energie (kcal)", "energie kcal", "enerckal", "brennwert kcal"],
    "protein_g": ["protein", "eiweiß", "eiweiss", "protein_g", "ezw"],
    "fett_g": ["fett", "fett_g", "zf"],
    "kh_g": ["kohlenhydrate", "kohlenhydrate_g", "kh", "zk"],
    "ballaststoffe_g": ["ballaststoffe", "ballaststoffe_g", "zb"],
    "kategorie": ["kategorie", "gruppe", "lebensmittelgruppe", "hauptgruppe"],
}


def spalte_finden(kopf: list[str], kandidaten: list[str]) -> str | None:
    norm = {k.strip().lower(): k for k in kopf}
    for kand in kandidaten:
        if kand in norm:
            return norm[kand]
    for k_norm, k_orig in norm.items():
        if any(kand in k_norm for kand in kandidaten):
            return k_orig
    return None


def zahl(wert: str | None) -> float | None:
    if wert is None or str(wert).strip() == "":
        return None
    try:
        return float(str(wert).replace(",", ".").strip())
    except ValueError:
        return None


def zeilen_lesen(pfad: Path):
    with pfad.open(encoding="utf-8-sig", newline="") as f:
        probe = f.read(4096)
        f.seek(0)
        trenner = ";" if probe.count(";") > probe.count(",") else ","
        leser = csv.DictReader(f, delimiter=trenner)
        kopf = leser.fieldnames or []
        zuordnung = {ziel: spalte_finden(kopf, kands) for ziel, kands in SPALTEN.items()}
        fehlend = [z for z in ("bls_code", "name_de", "kcal_100g", "protein_g") if not zuordnung[z]]
        if fehlend:
            raise SystemExit(f"Pflichtspalten nicht gefunden: {fehlend}. Vorhanden: {kopf}")
        for zeile in leser:
            code = (zeile.get(zuordnung["bls_code"]) or "").strip()
            name = (zeile.get(zuordnung["name_de"]) or "").strip()
            if not code or not name:
                continue
            yield {
                "bls_code": code,
                "name_de": name,
                "kcal_100g": zahl(zeile.get(zuordnung["kcal_100g"])) or 0.0,
                "protein_g": zahl(zeile.get(zuordnung["protein_g"])) or 0.0,
                "fett_g": zahl(zeile.get(zuordnung["fett_g"])) if zuordnung["fett_g"] else None,
                "kh_g": zahl(zeile.get(zuordnung["kh_g"])) if zuordnung["kh_g"] else None,
                "ballaststoffe_g": zahl(zeile.get(zuordnung["ballaststoffe_g"])) if zuordnung["ballaststoffe_g"] else None,
                "kategorie": (zeile.get(zuordnung["kategorie"]) or "").strip() if zuordnung["kategorie"] else "",
            }


async def importieren(pfad: Path) -> int:
    await indexe_anlegen()
    coll = db().lebensmittel
    n = 0
    stapel = []
    for doc in zeilen_lesen(pfad):
        stapel.append(doc)
        if len(stapel) >= 500:
            await _schreiben(coll, stapel); n += len(stapel); stapel = []
    if stapel:
        await _schreiben(coll, stapel); n += len(stapel)
    return n


async def _schreiben(coll, docs):
    from pymongo import UpdateOne
    await coll.bulk_write([UpdateOne({"bls_code": d["bls_code"]}, {"$set": d}, upsert=True) for d in docs])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Pfad zur BLS-CSV angeben")
    anzahl = asyncio.run(importieren(Path(sys.argv[1])))
    print(f"{anzahl} Lebensmittel importiert/aktualisiert")

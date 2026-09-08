"""M2-Teil — Einkaufsliste aus einem Plan.

Rezepte haben strukturierte Zutaten, die Liste entsteht direkt daraus. Ein
Wochenplan nennt je Gericht nur die Hauptzutaten als Text — die Mengen fuer
sieben Tage schaetzt der Buddy in einem einzelnen Aufruf und liefert JSON.
Das Ergebnis wird am Plan gecacht (plaene.einkaufsliste)."""
import json
import re
from ki import kurz

KATEGORIEN = ["Obst & Gemüse", "Eiweiß (Fleisch, Fisch, Eier, Tofu)", "Milchprodukte", "Getreide & Hülsenfrüchte",
              "Vorrat & Gewürze", "Sonstiges"]

SYSTEM = ("Du erstellst Einkaufslisten fuer Wochenplaene der Personal Training Lounge. Antworte NUR mit JSON, "
          "ohne Erklaerung, Schema: {\"kategorien\":[{\"name\":\"...\",\"artikel\":[{\"menge\":\"900 g\",\"name\":\"Hähnchenbrust\"}]}]}. "
          "Kategorien genau: " + ", ".join(KATEGORIEN) + ". Mengen fuer die ganze Woche und die angegebene Personenzahl "
          "addieren und auf Packungsgroessen runden. Gewuerze und Grundvorrat (Öl, Salz) nur nennen, wenn ungewoehnlich.")


def aus_rezept(rezept: dict) -> dict:
    artikel = [{"menge": str(z.get("menge") or ""), "name": str(z.get("name") or "")} for z in rezept.get("zutaten", [])]
    return {"kategorien": [{"name": "Zutaten", "artikel": artikel}], "quelle": "rezept"}


def _json_aus_text(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    daten = json.loads(m.group(0) if m else text)
    kategorien = []
    for k in daten.get("kategorien", []):
        artikel = [{"menge": str(a.get("menge") or ""), "name": str(a.get("name") or "")} for a in k.get("artikel", []) if a.get("name")]
        if artikel:
            kategorien.append({"name": str(k.get("name") or "Sonstiges"), "artikel": artikel})
    if not kategorien:
        raise ValueError("leere Einkaufsliste")
    return {"kategorien": kategorien, "quelle": "buddy"}


async def aus_wochenplan(plan: dict, personen: int = 1) -> dict:
    zeilen = []
    for t in plan.get("tage", []):
        for m in t.get("mahlzeiten", []):
            zeilen.append(f"{t.get('tag', '')} · {m.get('name', '')}: {m.get('gericht', '')}")
    text = f"Personen: {personen}\n" + "\n".join(zeilen)
    return _json_aus_text(await kurz.kurz_antwort(SYSTEM, text, max_tokens=1500))


def als_text(liste: dict, titel: str = "Einkaufsliste") -> str:
    teile = [titel]
    for k in liste.get("kategorien", []):
        teile.append("")
        teile.append(k["name"].upper())
        for a in k["artikel"]:
            teile.append(f"☐ {a['menge']} {a['name']}".replace("☐  ", "☐ "))
    return "\n".join(teile)

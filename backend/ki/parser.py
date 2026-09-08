import json
import logging
import re

log = logging.getLogger(__name__)
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
ERLAUBTE_TYPEN = {"wochenplan", "rezept"}


def plaene_extrahieren(text: str) -> tuple[str, list[dict]]:
    """Schneidet JSON-Blöcke mit typ ∈ {wochenplan, rezept} aus dem Buddy-Text.
    Gibt (bereinigter Text, Liste Pläne) zurück. Ungültiges JSON → bleibt weg, Warnung ins Log."""
    plaene: list[dict] = []

    def ersetzen(m: re.Match) -> str:
        try:
            daten = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            log.warning("Ungültiger JSON-Block vom Buddy: %s", e)
            return ""
        if not isinstance(daten, dict) or daten.get("typ") not in ERLAUBTE_TYPEN:
            return m.group(0)
        if not _plausibel(daten):
            log.warning("JSON-Block unvollständig: %s", daten.get("typ"))
            return ""
        plaene.append(daten)
        return ""

    text_neu = JSON_BLOCK.sub(ersetzen, text)
    text_neu = re.sub(r"\n{3,}", "\n\n", text_neu).strip()
    return text_neu, plaene


def _plausibel(d: dict) -> bool:
    if d["typ"] == "wochenplan":
        tage = d.get("tage")
        return isinstance(tage, list) and len(tage) >= 1 and all(
            isinstance(t, dict) and isinstance(t.get("mahlzeiten"), list) for t in tage)
    if d["typ"] == "rezept":
        return isinstance(d.get("zutaten"), list) and isinstance(d.get("schritte"), list)
    return False


def titel_ableiten(plan: dict) -> str:
    return str(plan.get("titel") or ("Wochenplan" if plan["typ"] == "wochenplan" else "Rezept"))[:120]

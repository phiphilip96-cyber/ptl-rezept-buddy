"""Anthropic-Aufruf mit Streaming und Tool naehrwerte_suchen (BLS)."""
import logging
from typing import AsyncIterator
import anthropic
from config import einstellungen
from db import db

log = logging.getLogger(__name__)

TOOL_NAEHRWERTE = {
    "name": "naehrwerte_suchen",
    "description": "Sucht ein Lebensmittel im Bundeslebensmittelschlüssel und liefert kcal, Protein, Fett, Kohlenhydrate je 100 g. Nutze es für Nährwertangaben statt zu schätzen.",
    "input_schema": {
        "type": "object",
        "properties": {"begriff": {"type": "string", "description": "Lebensmittelname auf Deutsch, z. B. 'Haferflocken'"}},
        "required": ["begriff"],
    },
}


async def lebensmittel_suchen(begriff: str, limit: int = 3) -> list[dict]:
    coll = db().lebensmittel
    cursor = coll.find({"$text": {"$search": begriff}}, {"_id": 0, "score": {"$meta": "textScore"}}) \
                 .sort([("score", {"$meta": "textScore"})]).limit(limit)
    treffer = await cursor.to_list(length=limit)
    if not treffer:  # Fallback: Teilstring
        cursor = coll.find({"name_de": {"$regex": begriff, "$options": "i"}}, {"_id": 0}).limit(limit)
        treffer = await cursor.to_list(length=limit)
    for t in treffer:
        t.pop("score", None)
    return treffer


def _tool_text(treffer: list[dict]) -> str:
    if not treffer:
        return "Kein Treffer im BLS. Nährwerte als 'ca.' angeben."
    return "\n".join(
        f"{t['name_de']}: {t['kcal_100g']:.0f} kcal, {t['protein_g']:.1f} g Protein, "
        f"{(t.get('fett_g') or 0):.1f} g Fett, {(t.get('kh_g') or 0):.1f} g KH je 100 g"
        for t in treffer)


class AgentErgebnis:
    def __init__(self):
        self.text = ""
        self.tool_aufrufe: list[dict] = []
        self.tokens_in = 0
        self.tokens_out = 0


async def buddy_antworten(system: str, verlauf: list[dict], client: anthropic.AsyncAnthropic | None = None,
                          such_fn=lebensmittel_suchen) -> AsyncIterator[tuple[str, str | AgentErgebnis]]:
    """Yielded ('text', chunk) während des Streamings und am Ende ('fertig', AgentErgebnis).
    Führt bis zu MAX_TOOL_AUFRUFE Tool-Runden aus."""
    client = client or anthropic.AsyncAnthropic(api_key=einstellungen.ANTHROPIC_API_KEY)
    ergebnis = AgentErgebnis()
    messages = list(verlauf)
    runden = 0

    while True:
        tools = [TOOL_NAEHRWERTE] if runden < einstellungen.MAX_TOOL_AUFRUFE else []
        async with client.messages.stream(
            model=einstellungen.ANTHROPIC_MODEL, max_tokens=4000, temperature=0.7,
            system=system, messages=messages, tools=tools,
        ) as stream:
            async for ereignis in stream:
                if ereignis.type == "content_block_delta" and getattr(ereignis.delta, "type", "") == "text_delta":
                    ergebnis.text += ereignis.delta.text
                    yield ("text", ereignis.delta.text)
            antwort = await stream.get_final_message()

        ergebnis.tokens_in += antwort.usage.input_tokens
        ergebnis.tokens_out += antwort.usage.output_tokens

        tool_bloecke = [b for b in antwort.content if b.type == "tool_use"]
        if antwort.stop_reason != "tool_use" or not tool_bloecke:
            break

        messages.append({"role": "assistant", "content": [b.model_dump() for b in antwort.content]})
        ergebnisse = []
        for block in tool_bloecke:
            begriff = str(block.input.get("begriff", ""))
            treffer = await such_fn(begriff)
            ergebnis.tool_aufrufe.append({"begriff": begriff, "treffer": treffer})
            ergebnisse.append({"type": "tool_result", "tool_use_id": block.id, "content": _tool_text(treffer)})
        messages.append({"role": "user", "content": ergebnisse})
        runden += 1

    yield ("fertig", ergebnis)

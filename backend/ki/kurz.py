"""Einzelner, nicht gestreamter Claude-Aufruf fuer kleine Aufgaben
(Check-in-Einordnung, Einkaufsliste). Kein Tool, kein Verlauf."""
import anthropic
from config import einstellungen


async def kurz_antwort(system: str, text: str, max_tokens: int = 600,
                       client: anthropic.AsyncAnthropic | None = None) -> str:
    client = client or anthropic.AsyncAnthropic(api_key=einstellungen.ANTHROPIC_API_KEY)
    antwort = await client.messages.create(
        model=einstellungen.ANTHROPIC_MODEL, max_tokens=max_tokens, temperature=0.4,
        system=system, messages=[{"role": "user", "content": text}])
    return "".join(getattr(b, "text", "") for b in antwort.content).strip()

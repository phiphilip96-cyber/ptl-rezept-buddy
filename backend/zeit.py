"""Datumshilfen: Kunden leben in Europe/Berlin, gespeichert wird als YYYY-MM-DD."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def heute() -> date:
    return datetime.now(BERLIN).date()


def datum_parsen(s: str) -> date:
    return date.fromisoformat(s)


def iso_woche(d: date) -> str:
    j, w, _ = d.isocalendar()
    return f"{j}-W{w:02d}"


def naechster_montag(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7)

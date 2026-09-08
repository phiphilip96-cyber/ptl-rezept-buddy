from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import einstellungen

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(einstellungen.MONGO_URL)
        _db = _client[einstellungen.MONGO_DB]
    return _db


def db_setzen(datenbank):
    """Für Tests: eine andere (Mock-)Datenbank einsetzen."""
    global _db
    _db = datenbank


async def indexe_anlegen():
    d = db()
    await d.kunden.create_index("email", unique=True)
    await d.coaches.create_index("email", unique=True)
    await d.profile.create_index("kunde_id", unique=True)
    await d.konversationen.create_index([("kunde_id", 1), ("letzte_nachricht_am", -1)])
    await d.nachrichten.create_index([("konversation_id", 1), ("erstellt_am", 1)])
    await d.plaene.create_index([("kunde_id", 1), ("erstellt_am", -1)])
    await d.lebensmittel.create_index([("name_de", "text")])
    await d.lebensmittel.create_index("bls_code", unique=True)
    await d.magic_links.create_index("laeuft_ab", expireAfterSeconds=0)
    # v2-Module: ein Dokument je Kunde und Tag bzw. Woche — Idempotenz ueber den Index
    await d.tagebuch.create_index([("kunde_id", 1), ("datum", 1)], unique=True)
    await d.messungen.create_index([("kunde_id", 1), ("datum", 1)], unique=True)
    await d.checkins.create_index([("kunde_id", 1), ("woche", 1)], unique=True)

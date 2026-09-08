"""Tests laufen ohne echte MongoDB (mongomock über Motor-Wrapper) und ohne echte Anthropic-API."""
import asyncio
from datetime import datetime, timezone
import pytest
import mongomock
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import db as dbmodul
from auth import jwt_erstellen, COOKIE, pw


class _AsyncCursor:
    def __init__(self, cursor):
        self._c = cursor

    def sort(self, *a, **k):
        self._c = self._c.sort(*a, **k); return self

    def limit(self, n):
        self._c = self._c.limit(n); return self

    async def to_list(self, length=None):
        return list(self._c)

    def __aiter__(self):
        self._it = iter(list(self._c)); return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _AsyncCollection:
    def __init__(self, coll):
        self._c = coll

    def find(self, *a, **k):
        return _AsyncCursor(self._c.find(*a, **k))

    def aggregate(self, *a, **k):
        return _AsyncCursor(self._c.aggregate(*a, **k))

    def __getattr__(self, name):
        attr = getattr(self._c, name)
        if callable(attr):
            async def wrapper(*a, **k):
                return attr(*a, **k)
            return wrapper
        return attr


class _AsyncDB:
    def __init__(self):
        self._db = mongomock.MongoClient()["test"]

    def __getattr__(self, name):
        return _AsyncCollection(self._db[name])


@pytest.fixture
def mockdb():
    d = _AsyncDB()
    dbmodul.db_setzen(d)
    yield d
    dbmodul.db_setzen(None)


@pytest.fixture
async def client(mockdb, monkeypatch):
    import main
    monkeypatch.setattr(main, "indexe_anlegen", _noop)
    monkeypatch.setattr(main, "coach_seed", _noop)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        yield c


async def _noop():
    return None


@pytest.fixture
async def kunde(mockdb, client):
    kid = ObjectId()
    await mockdb.kunden.insert_one({"_id": kid, "email": "lena@test.de", "vorname": "Lena", "aktiv": True,
                                    "erstellt_am": datetime.now(timezone.utc)})
    client.cookies.set(COOKIE, jwt_erstellen(str(kid), "kunde"))
    return kid


@pytest.fixture
async def coach(mockdb, client):
    cid = ObjectId()
    await mockdb.coaches.insert_one({"_id": cid, "email": "coach@test.de", "name": "Philip", "passwort_hash": pw.hash("geheim")})
    client.cookies.set(COOKIE, jwt_erstellen(str(cid), "coach"))
    return cid


PROFIL_LENA = {"vorname": "Lena", "ziel": "muskelaufbau", "gewicht_kg": 56, "groesse_cm": 165, "geburtsjahr": 1997,
               "geschlecht": "weiblich", "aktivitaet": "mittel", "ernaehrungsart": "alles",
               "unvertraeglichkeiten": ["gluten"], "abneigungen": ["Pilze"]}

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import pw
from config import einstellungen
from db import db, indexe_anlegen
from routes import auth, bls, chat, coach, plaene, profil

logging.basicConfig(level=logging.INFO)


async def coach_seed():
    """COACH_EMAIL/COACH_PASSWORT aus der Umgebung sind die Wahrheit: Beim Start
    wird der Hash immer nachgezogen, damit ein in Coolify geaendertes Passwort
    nach dem Neustart gilt (vorher galt nur der allererste Wert)."""
    if einstellungen.COACH_EMAIL and einstellungen.COACH_PASSWORT:
        email = einstellungen.COACH_EMAIL.lower()
        vorhanden = await db().coaches.find_one({"email": email})
        if not vorhanden:
            await db().coaches.insert_one({"email": email, "name": "Philip", "passwort_hash": pw.hash(einstellungen.COACH_PASSWORT)})
            logging.info("Coach-Account angelegt: %s", email)
        elif not pw.verify(einstellungen.COACH_PASSWORT, vorhanden["passwort_hash"]):
            await db().coaches.update_one({"_id": vorhanden["_id"]}, {"$set": {"passwort_hash": pw.hash(einstellungen.COACH_PASSWORT)}})
            logging.info("Coach-Passwort aus der Umgebung aktualisiert: %s", email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await indexe_anlegen()
    await coach_seed()
    yield


app = FastAPI(title="PTL Rezept-Buddy", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[einstellungen.APP_URL], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, profil, chat, plaene, bls, coach):
    app.include_router(r.router, prefix="/api")


@app.get("/api/gesund")
async def gesund():
    return {"ok": True}

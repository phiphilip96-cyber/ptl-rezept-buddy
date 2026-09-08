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
    if einstellungen.COACH_EMAIL and einstellungen.COACH_PASSWORT:
        email = einstellungen.COACH_EMAIL.lower()
        if not await db().coaches.find_one({"email": email}):
            await db().coaches.insert_one({"email": email, "name": "Philip", "passwort_hash": pw.hash(einstellungen.COACH_PASSWORT)})
            logging.info("Coach-Account angelegt: %s", email)


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

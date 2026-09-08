import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from bson import ObjectId
from fastapi import Cookie, Depends, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import einstellungen
from db import db

pw = CryptContext(schemes=["bcrypt"], deprecated="auto")
COOKIE = "ptl_session"


def jwt_erstellen(subjekt: str, rolle: str) -> str:
    laeuft_ab = datetime.now(timezone.utc) + timedelta(hours=einstellungen.JWT_GUELTIG_STUNDEN)
    return jwt.encode({"sub": subjekt, "rolle": rolle, "exp": laeuft_ab}, einstellungen.JWT_SECRET, algorithm="HS256")


def jwt_lesen(token: str) -> dict:
    try:
        return jwt.decode(token, einstellungen.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Nicht angemeldet")


async def aktueller_kunde(ptl_session: str | None = Cookie(default=None)) -> dict:
    if not ptl_session:
        raise HTTPException(401, "Nicht angemeldet")
    daten = jwt_lesen(ptl_session)
    if daten.get("rolle") != "kunde":
        raise HTTPException(403, "Nur für Kunden")
    kunde = await db().kunden.find_one({"_id": ObjectId(daten["sub"]), "aktiv": True})
    if not kunde:
        raise HTTPException(401, "Kunde nicht gefunden")
    return kunde


async def aktueller_coach(ptl_session: str | None = Cookie(default=None)) -> dict:
    if not ptl_session:
        raise HTTPException(401, "Nicht angemeldet")
    daten = jwt_lesen(ptl_session)
    if daten.get("rolle") != "coach":
        raise HTTPException(403, "Nur für Coaches")
    coach = await db().coaches.find_one({"_id": ObjectId(daten["sub"])})
    if not coach:
        raise HTTPException(401, "Coach nicht gefunden")
    return coach


async def magic_link_erstellen(kunde_id: ObjectId) -> str:
    token = secrets.token_urlsafe(32)
    await db().magic_links.insert_one({
        "token": token, "kunde_id": kunde_id,
        "laeuft_ab": datetime.now(timezone.utc) + timedelta(minutes=30),
    })
    return f"{einstellungen.APP_URL}/api/auth/einloesen?token={token}"


def mail_senden(an: str, betreff: str, text: str) -> bool:
    if not einstellungen.MAIL_HOST:
        print(f"[MAIL-DUMMY] an {an}: {betreff}\n{text}")
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = einstellungen.MAIL_FROM, an, betreff
    msg.set_content(text)
    with smtplib.SMTP(einstellungen.MAIL_HOST, einstellungen.MAIL_PORT) as s:
        s.starttls()
        if einstellungen.MAIL_USER:
            s.login(einstellungen.MAIL_USER, einstellungen.MAIL_PASS)
        s.send_message(msg)
    return True

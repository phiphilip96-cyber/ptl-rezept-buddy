from datetime import datetime, timezone
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from auth import COOKIE, jwt_erstellen, magic_link_erstellen, mail_senden, pw
from config import einstellungen
from db import db

router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkEingabe(BaseModel):
    email: EmailStr


class CoachLogin(BaseModel):
    email: EmailStr
    passwort: str


@router.post("/magic-link")
async def magic_link(eingabe: MagicLinkEingabe):
    kunde = await db().kunden.find_one({"email": eingabe.email.lower(), "aktiv": True})
    if kunde:
        link = await magic_link_erstellen(kunde["_id"])
        mail_senden(kunde["email"], "Dein Login für den PTL Rezept-Buddy",
                    f"Hi {kunde.get('vorname', '')},\n\nhier ist dein Login-Link (30 Minuten gültig):\n{link}\n\nDein PTL-Team")
    return {"ok": True}  # immer 200, damit E-Mails nicht ausgespäht werden können


@router.get("/einloesen")
async def einloesen(token: str):
    eintrag = await db().magic_links.find_one_and_delete({"token": token})
    if not eintrag or eintrag["laeuft_ab"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return RedirectResponse(f"{einstellungen.APP_URL}/login?fehler=link")
    jwt_token = jwt_erstellen(str(eintrag["kunde_id"]), "kunde")
    profil = await db().profile.find_one({"kunde_id": eintrag["kunde_id"]})
    antwort = RedirectResponse(f"{einstellungen.APP_URL}/{'chat' if profil else 'profil'}")
    antwort.set_cookie(COOKIE, jwt_token, httponly=True, samesite="lax", max_age=einstellungen.JWT_GUELTIG_STUNDEN * 3600)
    return antwort


@router.post("/coach/login")
async def coach_login(eingabe: CoachLogin, response: Response):
    coach = await db().coaches.find_one({"email": eingabe.email.lower()})
    if not coach or not pw.verify(eingabe.passwort, coach["passwort_hash"]):
        return Response(status_code=401, content="Login fehlgeschlagen")
    response.set_cookie(COOKIE, jwt_erstellen(str(coach["_id"]), "coach"), httponly=True, samesite="lax",
                        max_age=einstellungen.JWT_GUELTIG_STUNDEN * 3600)
    return {"ok": True, "name": coach.get("name", "")}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}

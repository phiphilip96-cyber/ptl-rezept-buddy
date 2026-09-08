from fastapi import APIRouter, Depends, Query
from auth import aktueller_kunde
from ki.agent import lebensmittel_suchen

router = APIRouter(tags=["bls"])


@router.get("/lebensmittel")
async def lebensmittel(q: str = Query(min_length=2), kunde=Depends(aktueller_kunde)):
    return {"treffer": await lebensmittel_suchen(q, limit=10)}

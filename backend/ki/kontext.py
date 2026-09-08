"""Kontextbloecke der Module fuer den Systemprompt (v2: jedes Modul liefert seinen Block)."""
from bson import ObjectId
from routes.messungen import koerper_text
from routes.tagebuch import bilanz_text


async def kontext_bauen(kunde_id: ObjectId) -> str:
    return "\n\n".join([await bilanz_text(kunde_id), await koerper_text(kunde_id)])

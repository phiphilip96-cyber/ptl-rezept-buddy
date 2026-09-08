from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Rolle = Literal["kunde", "buddy", "coach"]


class NachrichtEingabe(BaseModel):
    inhalt: str = Field(min_length=1, max_length=4000)


class KonversationEingabe(BaseModel):
    titel: str = "Neuer Chat"


class NotizEingabe(BaseModel):
    inhalt: str = Field(min_length=1, max_length=2000)

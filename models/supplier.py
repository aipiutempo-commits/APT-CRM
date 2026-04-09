from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TipoFornitore(str, Enum):
    elettrico = "Elettrico"
    software = "Software"
    altro = "Altro"


class FornitoreBase(BaseModel):
    ragione_sociale: str
    tipo: Optional[TipoFornitore] = TipoFornitore.altro
    referente: Optional[str] = ""
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    note: Optional[str] = ""


class FornitoreCreate(FornitoreBase):
    pass


class FornitoreUpdate(BaseModel):
    ragione_sociale: Optional[str] = None
    tipo: Optional[TipoFornitore] = None
    referente: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    note: Optional[str] = None


class Fornitore(FornitoreBase):
    id: str
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

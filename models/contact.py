from pydantic import BaseModel
from typing import Optional


class ContattoBase(BaseModel):
    cliente_id: Optional[str] = ""
    cliente_nome: Optional[str] = ""
    fornitore_id: Optional[str] = ""
    fornitore_nome: Optional[str] = ""
    nome: str
    cognome: Optional[str] = ""
    ruolo: Optional[str] = ""
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    note: Optional[str] = ""


class ContattoCreate(ContattoBase):
    pass


class ContattoUpdate(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    fornitore_nome: Optional[str] = None
    nome: Optional[str] = None
    cognome: Optional[str] = None
    ruolo: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    note: Optional[str] = None


class Contatto(ContattoBase):
    id: str
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

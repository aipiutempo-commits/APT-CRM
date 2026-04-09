from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    ragione_sociale: str
    referente: Optional[str] = ""
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    note: Optional[str] = ""


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    ragione_sociale: Optional[str] = None
    referente: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    note: Optional[str] = None


class Cliente(ClienteBase):
    id: str
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

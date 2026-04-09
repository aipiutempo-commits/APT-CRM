from pydantic import BaseModel
from typing import Optional
from enum import Enum


class StatoProgetto(str, Enum):
    attivo = "Attivo"
    sospeso = "Sospeso"
    chiuso = "Chiuso"


class ProgettoBase(BaseModel):
    nome: str
    cliente_id: Optional[str] = ""
    cliente_nome: Optional[str] = ""
    stato: Optional[StatoProgetto] = StatoProgetto.attivo
    data_inizio: Optional[str] = ""
    data_fine_prevista: Optional[str] = ""
    note: Optional[str] = ""


class ProgettoCreate(ProgettoBase):
    pass


class ProgettoUpdate(BaseModel):
    nome: Optional[str] = None
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    stato: Optional[StatoProgetto] = None
    data_inizio: Optional[str] = None
    data_fine_prevista: Optional[str] = None
    note: Optional[str] = None


class Progetto(ProgettoBase):
    id: str
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TipoOfferta(str, Enum):
    elettrico = "Elettrico"
    software = "Software"


class StatoOfferta(str, Enum):
    da_inviare = "Da Inviare"
    inviata = "Inviata"
    ricevuta = "Ricevuta"
    in_valutazione = "In Valutazione"
    aggiudicata = "Aggiudicata"
    rifiutata = "Rifiutata"


class PrioritaOfferta(str, Enum):
    bassa = "Bassa"
    media = "Media"
    alta = "Alta"


class OffertaBase(BaseModel):
    progetto_id: Optional[str] = ""
    progetto_nome: Optional[str] = ""
    tipo: Optional[TipoOfferta] = TipoOfferta.elettrico
    fornitore_id: Optional[str] = ""
    fornitore_nome: Optional[str] = ""
    descrizione: Optional[str] = ""
    data_invio_richiesta: Optional[str] = ""
    scadenza_attesa: Optional[str] = ""
    stato: Optional[StatoOfferta] = StatoOfferta.da_inviare
    data_ricezione: Optional[str] = ""
    importo: Optional[str] = ""
    priorita: Optional[PrioritaOfferta] = PrioritaOfferta.media
    num_solleciti: Optional[str] = "0"
    note: Optional[str] = ""


class OffertaCreate(OffertaBase):
    pass


class OffertaUpdate(BaseModel):
    progetto_id: Optional[str] = None
    progetto_nome: Optional[str] = None
    tipo: Optional[TipoOfferta] = None
    fornitore_id: Optional[str] = None
    fornitore_nome: Optional[str] = None
    descrizione: Optional[str] = None
    data_invio_richiesta: Optional[str] = None
    scadenza_attesa: Optional[str] = None
    stato: Optional[StatoOfferta] = None
    data_ricezione: Optional[str] = None
    importo: Optional[str] = None
    priorita: Optional[PrioritaOfferta] = None
    num_solleciti: Optional[str] = None
    note: Optional[str] = None


class Offerta(OffertaBase):
    id: str
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

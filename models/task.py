from pydantic import BaseModel
from typing import Optional
from enum import Enum


class StatoTask(str, Enum):
    da_fare = "Da fare"
    in_corso = "In corso"
    fatto = "Fatto"


class PrioritaTask(str, Enum):
    bassa = "Bassa"
    media = "Media"
    alta = "Alta"


class AttivitaBase(BaseModel):
    titolo: str
    progetto_id: Optional[str] = ""
    progetto_nome: Optional[str] = ""
    assegnato_a: Optional[str] = ""
    scadenza: Optional[str] = ""
    stato: Optional[StatoTask] = StatoTask.da_fare
    priorita: Optional[PrioritaTask] = PrioritaTask.media
    note: Optional[str] = ""


class AttivitaCreate(AttivitaBase):
    pass


class AttivitaUpdate(BaseModel):
    titolo: Optional[str] = None
    progetto_id: Optional[str] = None
    progetto_nome: Optional[str] = None
    assegnato_a: Optional[str] = None
    scadenza: Optional[str] = None
    stato: Optional[StatoTask] = None
    priorita: Optional[PrioritaTask] = None
    note: Optional[str] = None


class Attivita(AttivitaBase):
    id: str
    calendar_event_id: Optional[str] = ""
    google_task_id: Optional[str] = ""
    data_creazione: Optional[str] = ""

    class Config:
        from_attributes = True

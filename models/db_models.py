"""
Modelli SQLAlchemy ORM – tutti le entità del CRM su PostgreSQL.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, TIMESTAMP, func
from services.database import Base


def _id():
    return str(uuid.uuid4())[:8].upper()


class Utente(Base):
    __tablename__ = "utenti"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    totp_secret = Column(String(64), nullable=True, default=None)
    email = Column(String(255), default="")
    ruolo = Column(String(20), nullable=False, default="utente")
    attivo = Column(Boolean, nullable=False, default=True)
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Cliente(Base):
    __tablename__ = "clienti"
    id = Column(String(20), primary_key=True, default=_id)
    ragione_sociale = Column(String(255), nullable=False)
    referente = Column(String(255), default="")
    email = Column(String(255), default="")
    telefono = Column(String(50), default="")
    note = Column(Text, default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Contatto(Base):
    __tablename__ = "contatti"
    id = Column(String(20), primary_key=True, default=_id)
    cliente_id = Column(String(20), nullable=True, default="")
    cliente_nome = Column(String(255), default="")
    nome = Column(String(100), nullable=False)
    cognome = Column(String(100), nullable=False, default="")
    ruolo = Column(String(150), default="")
    email = Column(String(255), default="")
    telefono = Column(String(50), default="")
    note = Column(Text, default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Fornitore(Base):
    __tablename__ = "fornitori"
    id = Column(String(20), primary_key=True, default=_id)
    ragione_sociale = Column(String(255), nullable=False)
    tipo = Column(String(20), default="Altro")
    referente = Column(String(255), default="")
    email = Column(String(255), default="")
    telefono = Column(String(50), default="")
    note = Column(Text, default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Progetto(Base):
    __tablename__ = "progetti"
    id = Column(String(20), primary_key=True, default=_id)
    nome = Column(String(255), nullable=False)
    cliente_id = Column(String(20), default="")
    cliente_nome = Column(String(255), default="")
    stato = Column(String(20), default="Attivo")
    data_inizio = Column(String(20), default="")
    data_fine_prevista = Column(String(20), default="")
    note = Column(Text, default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Offerta(Base):
    __tablename__ = "offerte"
    id = Column(String(20), primary_key=True, default=_id)
    progetto_id = Column(String(20), default="")
    progetto_nome = Column(String(255), default="")
    tipo = Column(String(20), default="Elettrico")
    fornitore_id = Column(String(20), default="")
    fornitore_nome = Column(String(255), default="")
    descrizione = Column(Text, default="")
    data_invio_richiesta = Column(String(20), default="")
    scadenza_attesa = Column(String(20), default="")
    stato = Column(String(30), default="Da Inviare")
    data_ricezione = Column(String(20), default="")
    importo = Column(String(20), default="")
    priorita = Column(String(10), default="Media")
    num_solleciti = Column(Integer, default=0)
    note = Column(Text, default="")
    calendar_event_id = Column(String(255), default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class Attivita(Base):
    __tablename__ = "attivita"
    id = Column(String(20), primary_key=True, default=_id)
    titolo = Column(String(255), nullable=False)
    progetto_id = Column(String(20), default="")
    progetto_nome = Column(String(255), default="")
    assegnato_a = Column(String(150), default="")
    scadenza = Column(String(20), default="")
    stato = Column(String(20), default="Da fare")
    priorita = Column(String(10), default="Media")
    note = Column(Text, default="")
    data_inizio = Column(String(20), default="")
    data_fine = Column(String(20), default="")
    calendar_event_id = Column(String(255), default="")
    google_task_id = Column(String(255), default="")
    data_creazione = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


class LogEntry(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    azione = Column(String(50), nullable=False)
    entita = Column(String(50), default="")
    id_entita = Column(String(20), default="")
    utente = Column(String(50), default="")
    dettagli = Column(Text, default="")

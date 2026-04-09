"""
Layer database SQLAlchemy – PostgreSQL (con fallback SQLite per sviluppo locale).
"""

import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_url = os.getenv("DATABASE_URL", "sqlite:///./crm.db")
# SQLAlchemy richiede il dialetto esplicito (gestisce sia postgres:// che postgresql://)
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency – sessione per richiesta."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_id() -> str:
    """Genera un ID breve stile UUID (8 caratteri uppercase)."""
    return str(uuid.uuid4())[:8].upper()


def to_dict(obj) -> dict:
    """Converte un'istanza ORM in dict con datetime → stringa."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if val is None:
            result[col.name] = ""
        elif hasattr(val, "strftime"):
            # datetime → "gg/mm/aaaa hh:mm", date → "aaaa-mm-gg"
            if hasattr(val, "hour"):
                result[col.name] = val.strftime("%d/%m/%Y %H:%M")
            else:
                result[col.name] = val.strftime("%Y-%m-%d")
        else:
            result[col.name] = val
    return result


def log_action(db, azione: str, entita: str = "", id_entita: str = "",
               utente: str = "sistema", dettagli: str = ""):
    """Scrive una riga nel log del database."""
    from models.db_models import LogEntry
    db.add(LogEntry(
        azione=azione,
        entita=entita,
        id_entita=str(id_entita),
        utente=utente,
        dettagli=dettagli,
    ))
    db.commit()


def init_db():
    """Crea tutte le tabelle e il primo utente admin."""
    from models import db_models  # noqa: assicura che i modelli siano importati
    Base.metadata.create_all(bind=engine, checkfirst=True)
    _seed_admin()


def _seed_admin():
    """Crea l'utente admin se non esiste."""
    from models.db_models import Utente
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        if not db.query(Utente).filter(Utente.username == "admin").first():
            admin_pw = os.getenv("APP_PASSWORD", "admin")
            db.add(Utente(
                username="admin",
                password_hash=pwd_ctx.hash(admin_pw),
                email="admin@diozzi.it",
                ruolo="admin",
                attivo=True,
            ))
            db.commit()
            print("[DB] Utente admin creato")
    except Exception as e:
        print(f"[DB] Errore seed admin: {e}")
        db.rollback()
    finally:
        db.close()

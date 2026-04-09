"""Router Dashboard – KPI aggregati da PostgreSQL."""

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.db_models import Offerta, Attivita, Progetto
from routers.auth import get_current_user
from services.database import get_db, to_dict

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


@router.get("/")
async def get_dashboard(db: Session = Depends(get_db),
                        current_user: str = Depends(get_current_user)):
    oggi = date.today()

    offerte = db.query(Offerta).all()
    tasks = db.query(Attivita).all()
    progetti = db.query(Progetto).all()

    offerte_scadute = [
        to_dict(o) for o in offerte
        if o.stato == "Inviata"
        and _parse_date(o.scadenza_attesa or "")
        and _parse_date(o.scadenza_attesa) < oggi
    ]

    task_urgenti = [t for t in tasks if t.priorita == "Alta" and t.stato != "Fatto"]

    progetti_attivi = [p for p in progetti if p.stato == "Attivo"]

    da_fare_oggi = [
        to_dict(t) for t in tasks
        if t.stato != "Fatto"
        and _parse_date(t.scadenza or "")
        and _parse_date(t.scadenza) <= oggi
    ]

    stati_offerte: dict = {}
    for o in offerte:
        s = o.stato or "Sconosciuto"
        stati_offerte[s] = stati_offerte.get(s, 0) + 1

    return {
        "kpi": {
            "offerte_scadute": len(offerte_scadute),
            "task_urgenti": len(task_urgenti),
            "progetti_attivi": len(progetti_attivi),
            "offerte_totali": len(offerte),
            "task_totali": len(tasks),
        },
        "da_fare_oggi": da_fare_oggi[:10],
        "offerte_scadute": offerte_scadute[:5],
        "stati_offerte": stati_offerte,
    }

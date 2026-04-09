"""
Router Dashboard – KPI e dati aggregati per la home.
"""

from datetime import date
from fastapi import APIRouter, Depends

from routers.auth import get_current_user
from services.google_sheets import (
    SHEET_ATTIVITA,
    SHEET_OFFERTE,
    SHEET_PROGETTI,
    get_sheets_service,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _parse_date(s: str):
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            from datetime import datetime
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


@router.get("/", summary="KPI e dati dashboard")
async def get_dashboard(current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    oggi = date.today()

    offerte = sheets.get_all(SHEET_OFFERTE)
    tasks = sheets.get_all(SHEET_ATTIVITA)
    progetti = sheets.get_all(SHEET_PROGETTI)

    # Offerte scadute (Inviata + scadenza passata)
    offerte_scadute = [
        o for o in offerte
        if o.get("stato") == "Inviata"
        and _parse_date(o.get("scadenza_attesa", ""))
        and _parse_date(o.get("scadenza_attesa", "")) < oggi
    ]

    # Task urgenti: alta priorità, non completati
    task_urgenti = [
        t for t in tasks
        if t.get("priorita") == "Alta" and t.get("stato") != "Fatto"
    ]

    # Progetti attivi
    progetti_attivi = [p for p in progetti if p.get("stato") == "Attivo"]

    # Da fare oggi: task non completati con scadenza <= oggi
    da_fare_oggi = [
        t for t in tasks
        if t.get("stato") != "Fatto"
        and _parse_date(t.get("scadenza", ""))
        and _parse_date(t.get("scadenza", "")) <= oggi
    ]

    # Offerte per stato (per grafico)
    stati_offerte: dict = {}
    for o in offerte:
        s = o.get("stato", "Sconosciuto")
        stati_offerte[s] = stati_offerte.get(s, 0) + 1

    return {
        "kpi": {
            "offerte_scadute": len(offerte_scadute),
            "task_urgenti": len(task_urgenti),
            "progetti_attivi": len(progetti_attivi),
            "offerte_totali": len(offerte),
            "task_totali": len(tasks),
        },
        "da_fare_oggi": da_fare_oggi[:10],   # max 10 nella dashboard
        "offerte_scadute": offerte_scadute[:5],
        "stati_offerte": stati_offerte,
    }

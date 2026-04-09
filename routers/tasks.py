"""
Router Attività/Task – sincronizzazione con Google Calendar e Google Tasks.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from models.task import Attivita, AttivitaCreate, AttivitaUpdate
from routers.auth import get_current_user
from services.google_calendar import crea_evento_task, elimina_evento
from services.google_sheets import SHEET_ATTIVITA, get_sheets_service
from services.google_tasks import crea_task, elimina_task

router = APIRouter(prefix="/api/attivita", tags=["attività"])


@router.get("/", response_model=list[Attivita], summary="Lista attività")
async def lista_attivita(current_user: str = Depends(get_current_user)):
    return get_sheets_service().get_all(SHEET_ATTIVITA)


@router.get("/{task_id}", response_model=Attivita, summary="Dettaglio attività")
async def get_attivita(task_id: str, current_user: str = Depends(get_current_user)):
    record = get_sheets_service().get_by_id(SHEET_ATTIVITA, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attività non trovata")
    return record


@router.post("/", response_model=Attivita, status_code=201, summary="Crea attività")
async def crea_attivita(
    data: AttivitaCreate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    nuova = sheets.create(SHEET_ATTIVITA, data.model_dump())
    task_id = nuova.get("id", "")

    # Sync Google Calendar e Tasks in background
    background_tasks.add_task(
        _sync_google_integrazioni,
        task_id,
        data.titolo,
        data.scadenza or "",
        data.note or "",
        data.stato or "Da fare",
    )

    sheets.log_action("CREATE", "Attività", task_id, current_user, data.titolo)
    return nuova


@router.put("/{task_id}", response_model=Attivita, summary="Aggiorna attività")
async def aggiorna_attivita(
    task_id: str,
    data: AttivitaUpdate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    aggiornamenti = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = sheets.update(SHEET_ATTIVITA, task_id, aggiornamenti)
    if not updated:
        raise HTTPException(status_code=404, detail="Attività non trovata")

    # Aggiorna le integrazioni Google se cambiati titolo, scadenza o stato
    if any(k in aggiornamenti for k in ("titolo", "scadenza", "stato", "note")):
        background_tasks.add_task(
            _sync_google_integrazioni,
            task_id,
            updated.get("titolo", ""),
            updated.get("scadenza", ""),
            updated.get("note", ""),
            updated.get("stato", "Da fare"),
            updated.get("calendar_event_id", ""),
            updated.get("google_task_id", ""),
        )

    sheets.log_action("UPDATE", "Attività", task_id, current_user, str(aggiornamenti))
    return updated


@router.delete("/{task_id}", status_code=204, summary="Elimina attività")
async def elimina_attivita(
    task_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    record = sheets.get_by_id(SHEET_ATTIVITA, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attività non trovata")

    # Rimuovi eventi Google in background
    cal_event_id = record.get("calendar_event_id", "")
    gtask_id = record.get("google_task_id", "")
    if cal_event_id:
        background_tasks.add_task(elimina_evento, cal_event_id)
    if gtask_id:
        background_tasks.add_task(elimina_task, gtask_id)

    sheets.delete(SHEET_ATTIVITA, task_id)
    sheets.log_action("DELETE", "Attività", task_id, current_user)


# ─── Sync integrazioni Google (background) ───────────────────────────────────

def _sync_google_integrazioni(
    task_id: str,
    titolo: str,
    scadenza: str,
    note: str,
    stato: str,
    cal_event_id: str = "",
    gtask_id: str = "",
):
    """Sincronizza Calendar e Google Tasks per un'attività."""
    sheets = get_sheets_service()
    aggiornamenti = {}

    try:
        # Google Calendar
        if scadenza:
            new_cal_id = crea_evento_task(
                titolo, scadenza, note, cal_event_id or None
            )
            if new_cal_id:
                aggiornamenti["calendar_event_id"] = new_cal_id

        # Google Tasks
        new_gtask_id = crea_task(
            titolo, scadenza, note, stato, gtask_id or None
        )
        if new_gtask_id:
            aggiornamenti["google_task_id"] = new_gtask_id

        if aggiornamenti:
            sheets.update(SHEET_ATTIVITA, task_id, aggiornamenti)

    except Exception as e:
        print(f"[Tasks router] Errore sync Google: {e}")

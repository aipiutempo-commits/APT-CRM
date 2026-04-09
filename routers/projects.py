"""
Router Progetti.
"""

from fastapi import APIRouter, Depends, HTTPException

from models.project import Progetto, ProgettoCreate, ProgettoUpdate
from routers.auth import get_current_user
from services.google_sheets import SHEET_PROGETTI, get_sheets_service

router = APIRouter(prefix="/api/progetti", tags=["progetti"])


@router.get("/", response_model=list[Progetto], summary="Lista progetti")
async def lista_progetti(current_user: str = Depends(get_current_user)):
    return get_sheets_service().get_all(SHEET_PROGETTI)


@router.get("/{progetto_id}", response_model=Progetto, summary="Dettaglio progetto")
async def get_progetto(progetto_id: str, current_user: str = Depends(get_current_user)):
    record = get_sheets_service().get_by_id(SHEET_PROGETTI, progetto_id)
    if not record:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return record


@router.post("/", response_model=Progetto, status_code=201, summary="Crea progetto")
async def crea_progetto(data: ProgettoCreate, current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    nuovo = sheets.create(SHEET_PROGETTI, data.model_dump())
    sheets.log_action("CREATE", "Progetti", nuovo.get("id", ""), current_user, data.nome)
    return nuovo


@router.put("/{progetto_id}", response_model=Progetto, summary="Aggiorna progetto")
async def aggiorna_progetto(
    progetto_id: str,
    data: ProgettoUpdate,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    aggiornamenti = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = sheets.update(SHEET_PROGETTI, progetto_id, aggiornamenti)
    if not updated:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    sheets.log_action("UPDATE", "Progetti", progetto_id, current_user, str(aggiornamenti))
    return updated


@router.delete("/{progetto_id}", status_code=204, summary="Elimina progetto")
async def elimina_progetto(progetto_id: str, current_user: str = Depends(get_current_user)):
    ok = get_sheets_service().delete(SHEET_PROGETTI, progetto_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    get_sheets_service().log_action("DELETE", "Progetti", progetto_id, current_user)

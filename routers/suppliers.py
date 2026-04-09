"""
Router Fornitori.
"""

from fastapi import APIRouter, Depends, HTTPException

from models.supplier import Fornitore, FornitoreCreate, FornitoreUpdate
from routers.auth import get_current_user
from services.google_sheets import SHEET_FORNITORI, get_sheets_service

router = APIRouter(prefix="/api/fornitori", tags=["fornitori"])


@router.get("/", response_model=list[Fornitore], summary="Lista fornitori")
async def lista_fornitori(current_user: str = Depends(get_current_user)):
    return get_sheets_service().get_all(SHEET_FORNITORI)


@router.get("/{fornitore_id}", response_model=Fornitore, summary="Dettaglio fornitore")
async def get_fornitore(fornitore_id: str, current_user: str = Depends(get_current_user)):
    record = get_sheets_service().get_by_id(SHEET_FORNITORI, fornitore_id)
    if not record:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return record


@router.post("/", response_model=Fornitore, status_code=201, summary="Crea fornitore")
async def crea_fornitore(data: FornitoreCreate, current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    nuovo = sheets.create(SHEET_FORNITORI, data.model_dump())
    sheets.log_action("CREATE", "Fornitori", nuovo.get("id", ""), current_user, data.ragione_sociale)
    return nuovo


@router.put("/{fornitore_id}", response_model=Fornitore, summary="Aggiorna fornitore")
async def aggiorna_fornitore(
    fornitore_id: str,
    data: FornitoreUpdate,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    aggiornamenti = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = sheets.update(SHEET_FORNITORI, fornitore_id, aggiornamenti)
    if not updated:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    sheets.log_action("UPDATE", "Fornitori", fornitore_id, current_user, str(aggiornamenti))
    return updated


@router.delete("/{fornitore_id}", status_code=204, summary="Elimina fornitore")
async def elimina_fornitore(fornitore_id: str, current_user: str = Depends(get_current_user)):
    ok = get_sheets_service().delete(SHEET_FORNITORI, fornitore_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    get_sheets_service().log_action("DELETE", "Fornitori", fornitore_id, current_user)

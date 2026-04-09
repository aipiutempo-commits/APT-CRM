"""
Router Clienti/Committenti.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from models.client import Cliente, ClienteCreate, ClienteUpdate
from routers.auth import get_current_user
from services.google_sheets import SHEET_CLIENTI, get_sheets_service

router = APIRouter(prefix="/api/clienti", tags=["clienti"])


@router.get("/", response_model=list[Cliente], summary="Lista clienti")
async def lista_clienti(current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    return sheets.get_all(SHEET_CLIENTI)


@router.get("/{cliente_id}", response_model=Cliente, summary="Dettaglio cliente")
async def get_cliente(cliente_id: str, current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    record = sheets.get_by_id(SHEET_CLIENTI, cliente_id)
    if not record:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return record


@router.post("/", response_model=Cliente, status_code=201, summary="Crea cliente")
async def crea_cliente(data: ClienteCreate, current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    nuovo = sheets.create(SHEET_CLIENTI, data.model_dump())
    sheets.log_action("CREATE", "Clienti", nuovo.get("id", ""), current_user, data.ragione_sociale)
    return nuovo


@router.put("/{cliente_id}", response_model=Cliente, summary="Aggiorna cliente")
async def aggiorna_cliente(
    cliente_id: str,
    data: ClienteUpdate,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    # Rimuovi campi None
    aggiornamenti = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = sheets.update(SHEET_CLIENTI, cliente_id, aggiornamenti)
    if not updated:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    sheets.log_action("UPDATE", "Clienti", cliente_id, current_user, str(aggiornamenti))
    return updated


@router.delete("/{cliente_id}", status_code=204, summary="Elimina cliente")
async def elimina_cliente(cliente_id: str, current_user: str = Depends(get_current_user)):
    sheets = get_sheets_service()
    ok = sheets.delete(SHEET_CLIENTI, cliente_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    sheets.log_action("DELETE", "Clienti", cliente_id, current_user)

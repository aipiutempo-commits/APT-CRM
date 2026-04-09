"""
Router Log – lettura del registro attività dal foglio Google.
"""

from fastapi import APIRouter, Depends

from routers.auth import get_current_user
from services.google_sheets import SHEET_LOG, get_sheets_service

router = APIRouter(prefix="/api/log", tags=["log"])


@router.get("/", summary="Ultimi log di attività")
async def lista_log(
    limite: int = 200,
    current_user: str = Depends(get_current_user),
):
    """Ritorna gli ultimi N log in ordine cronologico inverso."""
    sheets = get_sheets_service()
    tutti = sheets.get_all(SHEET_LOG)
    # Ordine inverso (più recenti prima), limite
    return list(reversed(tutti))[:limite]

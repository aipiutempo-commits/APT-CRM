"""
Router Offerte/Preventivi – include invio email e solleciti via Gmail.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from models.offer import Offerta, OffertaCreate, OffertaUpdate
from routers.auth import get_current_user
from services.google_sheets import SHEET_OFFERTE, get_sheets_service
from services.google_calendar import crea_reminder_offerta, elimina_evento
import services.gmail_service as gmail

router = APIRouter(prefix="/api/offerte", tags=["offerte"])


# ─── CRUD base ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[Offerta], summary="Lista offerte")
async def lista_offerte(current_user: str = Depends(get_current_user)):
    return get_sheets_service().get_all(SHEET_OFFERTE)


@router.get("/{offerta_id}", response_model=Offerta, summary="Dettaglio offerta")
async def get_offerta(offerta_id: str, current_user: str = Depends(get_current_user)):
    record = get_sheets_service().get_by_id(SHEET_OFFERTE, offerta_id)
    if not record:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    return record


@router.post("/", response_model=Offerta, status_code=201, summary="Crea offerta")
async def crea_offerta(
    data: OffertaCreate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    nuova = sheets.create(SHEET_OFFERTE, data.model_dump())
    offerta_id = nuova.get("id", "")

    # Crea reminder Calendar se c'è una scadenza
    if data.scadenza_attesa:
        background_tasks.add_task(
            _sync_calendar_offerta,
            offerta_id,
            data.descrizione or "",
            data.scadenza_attesa,
            data.progetto_nome or "",
        )

    sheets.log_action("CREATE", "Offerte", offerta_id, current_user, data.descrizione or "")
    return nuova


@router.put("/{offerta_id}", response_model=Offerta, summary="Aggiorna offerta")
async def aggiorna_offerta(
    offerta_id: str,
    data: OffertaUpdate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    aggiornamenti = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = sheets.update(SHEET_OFFERTE, offerta_id, aggiornamenti)
    if not updated:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    # Aggiorna reminder Calendar se la scadenza è cambiata
    if data.scadenza_attesa:
        existing_event = updated.get("calendar_event_id", "")
        background_tasks.add_task(
            _sync_calendar_offerta,
            offerta_id,
            updated.get("descrizione", ""),
            data.scadenza_attesa,
            updated.get("progetto_nome", ""),
            existing_event,
        )

    sheets.log_action("UPDATE", "Offerte", offerta_id, current_user, str(aggiornamenti))
    return updated


@router.delete("/{offerta_id}", status_code=204, summary="Elimina offerta")
async def elimina_offerta(
    offerta_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    sheets = get_sheets_service()
    record = sheets.get_by_id(SHEET_OFFERTE, offerta_id)
    if not record:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    # Elimina evento Calendar se presente
    event_id = record.get("calendar_event_id", "")
    if event_id:
        background_tasks.add_task(elimina_evento, event_id)

    sheets.delete(SHEET_OFFERTE, offerta_id)
    sheets.log_action("DELETE", "Offerte", offerta_id, current_user)


# ─── Invio email ──────────────────────────────────────────────────────────────

class EmailRichiestaBody(BaseModel):
    email_destinatario: str
    scadenza: str = ""


class SollecitaBody(BaseModel):
    email_destinatario: str


@router.post("/{offerta_id}/invia-richiesta", summary="Invia email richiesta preventivo")
async def invia_richiesta_preventivo(
    offerta_id: str,
    body: EmailRichiestaBody,
    current_user: str = Depends(get_current_user),
):
    """Invia email di richiesta preventivo al fornitore e aggiorna lo stato."""
    sheets = get_sheets_service()
    offerta = sheets.get_by_id(SHEET_OFFERTE, offerta_id)
    if not offerta:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    subject, body_html = gmail.template_richiesta_preventivo(
        fornitore_nome=offerta.get("fornitore_nome", ""),
        progetto_nome=offerta.get("progetto_nome", ""),
        descrizione=offerta.get("descrizione", ""),
        scadenza=body.scadenza,
    )

    ok = gmail.invia_email(body.email_destinatario, subject, body_html)
    if not ok:
        raise HTTPException(status_code=500, detail="Errore invio email")

    # Aggiorna stato offerta
    from datetime import date
    sheets.update(SHEET_OFFERTE, offerta_id, {
        "stato": "Inviata",
        "data_invio_richiesta": date.today().strftime("%d/%m/%Y"),
    })
    sheets.log_action(
        "EMAIL_RICHIESTA", "Offerte", offerta_id, current_user,
        f"Email inviata a {body.email_destinatario}"
    )
    return {"ok": True, "message": f"Email inviata a {body.email_destinatario}"}


@router.post("/{offerta_id}/sollecita", summary="Invia sollecito")
async def sollecita_offerta(
    offerta_id: str,
    body: SollecitaBody,
    current_user: str = Depends(get_current_user),
):
    """Invia email di sollecito e incrementa il contatore solleciti."""
    sheets = get_sheets_service()
    offerta = sheets.get_by_id(SHEET_OFFERTE, offerta_id)
    if not offerta:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    num_solleciti = int(offerta.get("num_solleciti", 0) or 0) + 1

    subject, body_html = gmail.template_sollecito(
        fornitore_nome=offerta.get("fornitore_nome", ""),
        progetto_nome=offerta.get("progetto_nome", ""),
        descrizione=offerta.get("descrizione", ""),
        data_invio_originale=offerta.get("data_invio_richiesta", ""),
        num_sollecito=num_solleciti,
    )

    ok = gmail.invia_email(body.email_destinatario, subject, body_html)
    if not ok:
        raise HTTPException(status_code=500, detail="Errore invio email")

    sheets.update(SHEET_OFFERTE, offerta_id, {"num_solleciti": str(num_solleciti)})
    sheets.log_action(
        "SOLLECITO", "Offerte", offerta_id, current_user,
        f"Sollecito n.{num_solleciti} a {body.email_destinatario}"
    )
    return {"ok": True, "num_solleciti": num_solleciti}


# ─── Sync Calendar (background) ──────────────────────────────────────────────

def _sync_calendar_offerta(
    offerta_id: str,
    descrizione: str,
    scadenza: str,
    progetto_nome: str,
    event_id_esistente: str = "",
):
    """Crea/aggiorna il reminder Calendar per l'offerta e salva l'event_id."""
    try:
        event_id = crea_reminder_offerta(
            descrizione, scadenza, progetto_nome, event_id_esistente or None
        )
        if event_id:
            get_sheets_service().update(
                SHEET_OFFERTE, offerta_id, {"calendar_event_id": event_id}
            )
    except Exception as e:
        print(f"[Offers] Errore sync Calendar: {e}")

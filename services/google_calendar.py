"""
Servizio Google Calendar – crea/aggiorna eventi per task e offerte.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def _get_service():
    """Costruisce il client Google Calendar."""
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)


def _parse_date(date_str: str) -> Optional[str]:
    """
    Tenta di parsare la data in formato gg/mm/aaaa o aaaa-mm-gg.
    Ritorna la stringa in formato ISO (aaaa-mm-gg) o None se non parsabile.
    """
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def crea_evento_task(
    titolo: str,
    scadenza: str,
    descrizione: str = "",
    event_id_esistente: Optional[str] = None,
) -> Optional[str]:
    """
    Crea o aggiorna un evento a tutto giorno nel calendario per un task.
    Ritorna l'ID dell'evento creato/aggiornato, None in caso di errore.
    """
    iso_date = _parse_date(scadenza)
    if not iso_date:
        return None

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    service = _get_service()

    # La data di fine è il giorno successivo (formato all-day)
    end_date = (datetime.strptime(iso_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    evento = {
        "summary": f"[CRM Task] {titolo}",
        "description": descrizione,
        "start": {"date": iso_date},
        "end": {"date": end_date},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "email", "minutes": 1440},
            ],
        },
    }

    try:
        if event_id_esistente:
            # Aggiorna l'evento esistente
            result = service.events().update(
                calendarId=calendar_id,
                eventId=event_id_esistente,
                body=evento,
            ).execute()
        else:
            # Crea un nuovo evento
            result = service.events().insert(
                calendarId=calendar_id,
                body=evento,
            ).execute()

        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Errore creazione evento: {e}")
        return None


def crea_reminder_offerta(
    descrizione_offerta: str,
    scadenza: str,
    progetto_nome: str = "",
    event_id_esistente: Optional[str] = None,
) -> Optional[str]:
    """
    Crea o aggiorna un reminder nel calendario per la scadenza di un'offerta.
    Ritorna l'ID dell'evento, None in caso di errore.
    """
    iso_date = _parse_date(scadenza)
    if not iso_date:
        return None

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    service = _get_service()

    end_date = (datetime.strptime(iso_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    summary = f"[CRM Offerta] {descrizione_offerta[:50]}"
    if progetto_nome:
        summary = f"[CRM Offerta] {progetto_nome} – {descrizione_offerta[:40]}"

    evento = {
        "summary": summary,
        "description": f"Scadenza attesa offerta per: {progetto_nome}\n{descrizione_offerta}",
        "start": {"date": iso_date},
        "end": {"date": end_date},
        "colorId": "11",  # rosso tomato
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 120},
                {"method": "email", "minutes": 2880},
            ],
        },
    }

    try:
        if event_id_esistente:
            result = service.events().update(
                calendarId=calendar_id,
                eventId=event_id_esistente,
                body=evento,
            ).execute()
        else:
            result = service.events().insert(
                calendarId=calendar_id,
                body=evento,
            ).execute()

        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Errore reminder offerta: {e}")
        return None


def elimina_evento(event_id: str) -> bool:
    """Elimina un evento dal calendario."""
    if not event_id:
        return False
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    service = _get_service()
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"[Calendar] Errore eliminazione evento: {e}")
        return False

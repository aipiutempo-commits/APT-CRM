"""
Servizio Google Tasks – sincronizza le attività del CRM con Google Tasks.
"""

import os
from datetime import datetime
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/tasks",
]

# Nome della task list da usare nel CRM
TASKLIST_NAME = "CRM Attività"


def _get_service():
    """Costruisce il client Google Tasks."""
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("tasks", "v1", credentials=creds)


def _get_or_create_tasklist(service) -> str:
    """Trova o crea la task list del CRM, ritorna il suo ID."""
    try:
        lists = service.tasklists().list().execute()
        for tl in lists.get("items", []):
            if tl.get("title") == TASKLIST_NAME:
                return tl["id"]
        # Crea la lista se non esiste
        new_list = service.tasklists().insert(body={"title": TASKLIST_NAME}).execute()
        return new_list["id"]
    except Exception as e:
        print(f"[Tasks] Errore recupero task list: {e}")
        return "@default"


def _parse_rfc3339(date_str: str) -> Optional[str]:
    """Converte gg/mm/aaaa o aaaa-mm-gg in formato RFC3339 per Google Tasks."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            continue
    return None


def crea_task(
    titolo: str,
    scadenza: str = "",
    note: str = "",
    stato: str = "Da fare",
    task_id_esistente: Optional[str] = None,
) -> Optional[str]:
    """
    Crea o aggiorna un task in Google Tasks.
    Ritorna l'ID del task, None in caso di errore.
    """
    service = _get_service()
    tasklist_id = _get_or_create_tasklist(service)

    # Mappa lo stato CRM → status Google Tasks
    status = "needsAction" if stato != "Fatto" else "completed"

    task_body = {
        "title": titolo,
        "notes": note,
        "status": status,
    }

    due_rfc = _parse_rfc3339(scadenza)
    if due_rfc:
        task_body["due"] = due_rfc

    try:
        if task_id_esistente:
            task_body["id"] = task_id_esistente
            result = service.tasks().update(
                tasklist=tasklist_id,
                task=task_id_esistente,
                body=task_body,
            ).execute()
        else:
            result = service.tasks().insert(
                tasklist=tasklist_id,
                body=task_body,
            ).execute()

        return result.get("id")
    except Exception as e:
        print(f"[Tasks] Errore creazione/aggiornamento task: {e}")
        return None


def elimina_task(task_id: str) -> bool:
    """Elimina un task da Google Tasks."""
    if not task_id:
        return False
    service = _get_service()
    tasklist_id = _get_or_create_tasklist(service)
    try:
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return True
    except Exception as e:
        print(f"[Tasks] Errore eliminazione task: {e}")
        return False

"""
Servizio Google Contacts – legge i contatti da Google Workspace via People API.
Usa lo stesso Service Account con domain-wide delegation di Gmail/Calendar/Tasks.
"""

import os
from typing import List, Dict

SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]


def fetch_google_contacts() -> List[Dict]:
    """
    Recupera tutti i contatti Google Workspace dell'utente.
    Ritorna una lista di dict con: nome, cognome, email, telefono, ruolo, azienda
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    subject = os.getenv("GOOGLE_CONTACTS_SUBJECT") or os.getenv("GMAIL_FROM_EMAIL", "")

    if not subject:
        raise ValueError("GOOGLE_CONTACTS_SUBJECT o GMAIL_FROM_EMAIL non configurati")

    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    creds = creds.with_subject(subject)

    service = build("people", "v1", credentials=creds, cache_discovery=False)

    contacts = []
    page_token = None

    while True:
        kwargs = {
            "resourceName": "people/me",
            "pageSize": 1000,
            "personFields": "names,emailAddresses,phoneNumbers,organizations",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.people().connections().list(**kwargs).execute()
        connections = result.get("connections", [])

        for person in connections:
            contact = _parse_person(person)
            if contact:
                contacts.append(contact)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return contacts


def _parse_person(person: dict) -> dict | None:
    """Converte un oggetto People API in dict normalizzato per il CRM."""
    names = person.get("names", [])
    emails = person.get("emailAddresses", [])
    phones = person.get("phoneNumbers", [])
    orgs = person.get("organizations", [])

    # Serve almeno un nome
    if not names:
        return None

    name = names[0]
    org = orgs[0] if orgs else {}

    return {
        "nome": name.get("givenName", "").strip(),
        "cognome": name.get("familyName", "").strip(),
        "email": emails[0].get("value", "").strip() if emails else "",
        "telefono": phones[0].get("value", "").strip() if phones else "",
        "ruolo": org.get("title", "").strip(),
        "azienda": org.get("name", "").strip(),
        "google_resource_name": person.get("resourceName", ""),
    }

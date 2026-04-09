"""
Servizio Google Sheets – unico source of truth del CRM.
Gestisce tutte le operazioni CRUD sui fogli Google.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

# Scope necessari per Sheets e Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Nomi dei fogli (tab)
SHEET_CLIENTI = "Clienti"
SHEET_FORNITORI = "Fornitori"
SHEET_PROGETTI = "Progetti"
SHEET_OFFERTE = "Offerte"
SHEET_ATTIVITA = "Attività"
SHEET_LOG = "Log"

# Intestazioni per ogni foglio – l'ordine definisce le colonne
HEADERS: Dict[str, List[str]] = {
    SHEET_CLIENTI: [
        "ID", "Ragione Sociale", "Referente", "Email", "Telefono", "Note", "Data Creazione"
    ],
    SHEET_FORNITORI: [
        "ID", "Ragione Sociale", "Tipo", "Referente", "Email", "Telefono", "Note", "Data Creazione"
    ],
    SHEET_PROGETTI: [
        "ID", "Nome", "Cliente ID", "Cliente Nome", "Stato",
        "Data Inizio", "Data Fine Prevista", "Note", "Data Creazione"
    ],
    SHEET_OFFERTE: [
        "ID", "Progetto ID", "Progetto Nome", "Tipo", "Fornitore ID", "Fornitore Nome",
        "Descrizione", "Data Invio Richiesta", "Scadenza Attesa", "Stato",
        "Data Ricezione", "Importo", "Priorità", "Num Solleciti", "Note", "Data Creazione"
    ],
    SHEET_ATTIVITA: [
        "ID", "Titolo", "Progetto ID", "Progetto Nome", "Assegnato A",
        "Scadenza", "Stato", "Priorità", "Note",
        "Calendar Event ID", "Google Task ID", "Data Creazione"
    ],
    SHEET_LOG: [
        "Timestamp", "Azione", "Entità", "ID Entità", "Utente", "Dettagli"
    ],
}

# Mappatura da chiavi snake_case Python alle intestazioni del foglio
KEY_MAP: Dict[str, Dict[str, str]] = {
    SHEET_CLIENTI: {
        "id": "ID", "ragione_sociale": "Ragione Sociale", "referente": "Referente",
        "email": "Email", "telefono": "Telefono", "note": "Note",
        "data_creazione": "Data Creazione",
    },
    SHEET_FORNITORI: {
        "id": "ID", "ragione_sociale": "Ragione Sociale", "tipo": "Tipo",
        "referente": "Referente", "email": "Email", "telefono": "Telefono",
        "note": "Note", "data_creazione": "Data Creazione",
    },
    SHEET_PROGETTI: {
        "id": "ID", "nome": "Nome", "cliente_id": "Cliente ID",
        "cliente_nome": "Cliente Nome", "stato": "Stato",
        "data_inizio": "Data Inizio", "data_fine_prevista": "Data Fine Prevista",
        "note": "Note", "data_creazione": "Data Creazione",
    },
    SHEET_OFFERTE: {
        "id": "ID", "progetto_id": "Progetto ID", "progetto_nome": "Progetto Nome",
        "tipo": "Tipo", "fornitore_id": "Fornitore ID", "fornitore_nome": "Fornitore Nome",
        "descrizione": "Descrizione", "data_invio_richiesta": "Data Invio Richiesta",
        "scadenza_attesa": "Scadenza Attesa", "stato": "Stato",
        "data_ricezione": "Data Ricezione", "importo": "Importo",
        "priorita": "Priorità", "num_solleciti": "Num Solleciti",
        "note": "Note", "data_creazione": "Data Creazione",
    },
    SHEET_ATTIVITA: {
        "id": "ID", "titolo": "Titolo", "progetto_id": "Progetto ID",
        "progetto_nome": "Progetto Nome", "assegnato_a": "Assegnato A",
        "scadenza": "Scadenza", "stato": "Stato", "priorita": "Priorità",
        "note": "Note", "calendar_event_id": "Calendar Event ID",
        "google_task_id": "Google Task ID", "data_creazione": "Data Creazione",
    },
}


def _snake_to_sheet(sheet_name: str, data: Dict) -> Dict:
    """Converte le chiavi snake_case del modello nelle intestazioni del foglio."""
    km = KEY_MAP.get(sheet_name, {})
    result = {}
    for k, v in data.items():
        sheet_key = km.get(k, k)
        result[sheet_key] = v if v is not None else ""
    return result


def _sheet_to_snake(sheet_name: str, record: Dict) -> Dict:
    """Converte le intestazioni del foglio in chiavi snake_case."""
    reverse_map = {v: k for k, v in KEY_MAP.get(sheet_name, {}).items()}
    result = {}
    for k, v in record.items():
        snake_key = reverse_map.get(k, k.lower().replace(" ", "_"))
        result[snake_key] = v
    return result


class GoogleSheetsService:
    def __init__(self):
        self.gc: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self._connect()

    def _connect(self):
        """Connetti a Google Sheets usando il service account."""
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID", "")
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.spreadsheet = self.gc.open_by_key(spreadsheet_id)

    def _get_sheet(self, name: str) -> gspread.Worksheet:
        """Ritorna il foglio con quel nome, creandolo con gli header se mancante."""
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self.spreadsheet.add_worksheet(title=name, rows=2000, cols=30)
            if name in HEADERS:
                ws.append_row(HEADERS[name], value_input_option="USER_ENTERED")
            return ws

    # ─── CRUD generico ──────────────────────────────────────────────────────

    def get_all(self, sheet_name: str) -> List[Dict]:
        """Leggi tutti i record del foglio come lista di dizionari snake_case."""
        ws = self._get_sheet(sheet_name)
        records = ws.get_all_records(default_blank="")
        return [_sheet_to_snake(sheet_name, r) for r in records]

    def get_by_id(self, sheet_name: str, record_id: str) -> Optional[Dict]:
        """Trova un record per ID."""
        for r in self.get_all(sheet_name):
            if r.get("id") == record_id:
                return r
        return None

    def create(self, sheet_name: str, data: Dict) -> Dict:
        """Inserisce un nuovo record; genera ID e timestamp se assenti."""
        ws = self._get_sheet(sheet_name)
        headers = HEADERS[sheet_name]

        # Converti in chiavi del foglio
        sheet_data = _snake_to_sheet(sheet_name, data)

        # ID automatico
        if not sheet_data.get("ID"):
            sheet_data["ID"] = str(uuid.uuid4())[:8].upper()

        # Timestamp creazione
        if "Data Creazione" in headers and not sheet_data.get("Data Creazione"):
            sheet_data["Data Creazione"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Riga nell'ordine esatto degli header
        row = [sheet_data.get(h, "") for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")

        # Ritorna il record con chiavi snake_case
        return _sheet_to_snake(sheet_name, sheet_data)

    def update(self, sheet_name: str, record_id: str, data: Dict) -> Optional[Dict]:
        """Aggiorna i campi di un record esistente."""
        ws = self._get_sheet(sheet_name)
        all_values = ws.get_all_values()
        if len(all_values) < 2:
            return None

        header_row = all_values[0]
        try:
            id_col = header_row.index("ID")
        except ValueError:
            return None

        sheet_data = _snake_to_sheet(sheet_name, data)

        for row_idx, row in enumerate(all_values[1:], start=2):
            if row[id_col] == record_id:
                for col_header, value in sheet_data.items():
                    if col_header in header_row:
                        col_num = header_row.index(col_header) + 1
                        ws.update_cell(row_idx, col_num, value)
                return self.get_by_id(sheet_name, record_id)

        return None

    def delete(self, sheet_name: str, record_id: str) -> bool:
        """Elimina la riga con quell'ID."""
        ws = self._get_sheet(sheet_name)
        all_values = ws.get_all_values()
        if len(all_values) < 2:
            return False

        header_row = all_values[0]
        try:
            id_col = header_row.index("ID")
        except ValueError:
            return False

        for row_idx, row in enumerate(all_values[1:], start=2):
            if row[id_col] == record_id:
                ws.delete_rows(row_idx)
                return True

        return False

    # ─── Log ────────────────────────────────────────────────────────────────

    def log_action(
        self,
        azione: str,
        entita: str,
        id_entita: str = "",
        utente: str = "sistema",
        dettagli: str = "",
    ):
        """Scrive una riga nel foglio Log."""
        ws = self._get_sheet(SHEET_LOG)
        ws.append_row(
            [
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                azione,
                entita,
                id_entita,
                utente,
                dettagli,
            ],
            value_input_option="USER_ENTERED",
        )

    # ─── Inizializzazione struttura ─────────────────────────────────────────

    def init_structure(self):
        """Crea tutti i fogli con le intestazioni se non esistono già."""
        for sheet_name in HEADERS:
            self._get_sheet(sheet_name)


# ─── Singleton ──────────────────────────────────────────────────────────────

_service: Optional[GoogleSheetsService] = None


def get_sheets_service() -> GoogleSheetsService:
    """Ritorna l'istanza singleton del servizio."""
    global _service
    if _service is None:
        _service = GoogleSheetsService()
    return _service

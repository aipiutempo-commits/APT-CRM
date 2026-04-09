"""
Import CSV – importa record da file CSV per tutte le entità del CRM.
GET  /api/import/{entity}/template  → scarica CSV con solo gli header
POST /api/import/{entity}           → importa CSV, ritorna {imported, skipped, errors}
"""

import csv
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from models.db_models import Cliente, Contatto, Fornitore, Progetto, Offerta, Attivita
from routers.auth import get_current_user
from services.database import get_db, log_action

router = APIRouter(prefix="/api/import", tags=["import"])

# ─── Configurazione per entità ───────────────────────────────────────────────

ENTITY_CONFIG = {
    "clienti": {
        "model": Cliente,
        "required": ["ragione_sociale"],
        "fields": ["ragione_sociale", "referente", "email", "telefono", "note"],
    },
    "fornitori": {
        "model": Fornitore,
        "required": ["ragione_sociale"],
        "fields": ["ragione_sociale", "tipo", "referente", "email", "telefono", "note"],
    },
    "contatti": {
        "model": Contatto,
        "required": ["nome"],
        "fields": ["nome", "cognome", "cliente_nome", "cliente_id", "ruolo", "email", "telefono", "note"],
    },
    "progetti": {
        "model": Progetto,
        "required": ["nome"],
        "fields": ["nome", "cliente_nome", "cliente_id", "stato", "data_inizio", "data_fine_prevista", "note"],
    },
    "offerte": {
        "model": Offerta,
        "required": ["descrizione"],
        "fields": ["descrizione", "progetto_nome", "progetto_id", "tipo", "fornitore_nome",
                   "fornitore_id", "stato", "importo", "priorita", "scadenza_attesa",
                   "data_invio_richiesta", "note"],
    },
    "attivita": {
        "model": Attivita,
        "required": ["titolo"],
        "fields": ["titolo", "progetto_nome", "progetto_id", "assegnato_a",
                   "scadenza", "stato", "priorita", "note", "data_inizio", "data_fine"],
    },
}

VALID_STATI = {
    "progetti": ["Attivo", "Sospeso", "Chiuso"],
    "offerte": ["Da Inviare", "Inviata", "Ricevuta", "In Valutazione", "Aggiudicata", "Rifiutata"],
    "attivita": ["Da fare", "In corso", "Fatto"],
}

VALID_TIPO_FORNITORE = ["Elettrico", "Software", "Altro"]
VALID_TIPO_OFFERTA = ["Elettrico", "Software"]
VALID_PRIORITA = ["Bassa", "Media", "Alta"]


# ─── Template CSV ─────────────────────────────────────────────────────────────

@router.get("/{entity}/template")
async def scarica_template(entity: str, current_user: str = Depends(get_current_user)):
    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail=f"Entità '{entity}' non supportata")

    cfg = ENTITY_CONFIG[entity]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cfg["fields"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=template_{entity}.csv"},
    )


# ─── Import CSV ───────────────────────────────────────────────────────────────

@router.post("/{entity}")
async def importa_csv(
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail=f"Entità '{entity}' non supportata")

    cfg = ENTITY_CONFIG[entity]
    Model = cfg["model"]
    required = cfg["required"]
    allowed_fields = set(cfg["fields"])

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # gestisce BOM di Excel
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    # Normalizza gli header (lowercase, strip spazi)
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="File CSV vuoto o non valido")

    imported = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        # Normalizza le chiavi
        norm_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}

        # Verifica campi obbligatori
        missing = [f for f in required if not norm_row.get(f)]
        if missing:
            errors.append(f"Riga {row_num}: campo obbligatorio mancante: {', '.join(missing)}")
            skipped += 1
            continue

        try:
            # Filtra solo i campi validi per il modello
            data = {k: v for k, v in norm_row.items() if k in allowed_fields and v != ""}

            # Validazione stati
            if "stato" in data and entity in VALID_STATI:
                if data["stato"] not in VALID_STATI[entity]:
                    data["stato"] = VALID_STATI[entity][0]  # default al primo valore

            # Validazione tipo fornitore
            if entity == "fornitori" and "tipo" in data:
                if data["tipo"] not in VALID_TIPO_FORNITORE:
                    data["tipo"] = "Altro"

            # Validazione tipo offerta
            if entity == "offerte" and "tipo" in data:
                if data["tipo"] not in VALID_TIPO_OFFERTA:
                    data["tipo"] = "Elettrico"

            # Validazione priorità
            if "priorita" in data and data["priorita"] not in VALID_PRIORITA:
                data["priorita"] = "Media"

            # num_solleciti deve essere int
            if entity == "offerte":
                data.setdefault("num_solleciti", 0)

            obj = Model(**data)
            db.add(obj)
            imported += 1

        except Exception as e:
            errors.append(f"Riga {row_num}: {str(e)}")
            skipped += 1
            db.rollback()
            continue

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore salvataggio: {str(e)}")

    log_action(db, "IMPORT_CSV", entity.capitalize(), "", current_user,
               f"Importati {imported}, saltati {skipped}")

    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}

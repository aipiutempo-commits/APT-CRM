"""
Router Sync Contatti Google – importa/aggiorna contatti da Google Workspace.
POST /api/sync/google-contacts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.db_models import Contatto as ContattoORM, Cliente as ClienteORM
from routers.auth import get_current_user
from services.database import get_db, log_action

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/google-contacts")
async def sync_google_contacts(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Importa i contatti da Google Workspace nel CRM.
    - Deduplicazione per email (non crea duplicati)
    - Tenta di abbinare il cliente per nome azienda
    - Aggiorna i contatti già esistenti se i dati sono cambiati
    """
    try:
        from services.google_contacts import fetch_google_contacts
        google_contacts = fetch_google_contacts()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore connessione Google: {str(e)}")

    if not google_contacts:
        return {"synced": 0, "updated": 0, "skipped": 0, "errors": []}

    # Cache clienti per nome azienda (per abbinamento)
    clienti = db.query(ClienteORM).all()
    clienti_by_name = {c.ragione_sociale.lower().strip(): c for c in clienti if c.ragione_sociale}

    synced = 0
    updated = 0
    skipped = 0
    errors = []

    for gc in google_contacts:
        nome = gc.get("nome", "").strip()
        cognome = gc.get("cognome", "").strip()
        email = gc.get("email", "").strip()
        telefono = gc.get("telefono", "").strip()
        ruolo = gc.get("ruolo", "").strip()
        azienda = gc.get("azienda", "").strip()

        if not nome and not cognome:
            skipped += 1
            continue

        # Abbinamento cliente per nome azienda
        cliente_id = ""
        cliente_nome = azienda
        if azienda:
            match = clienti_by_name.get(azienda.lower().strip())
            if match:
                cliente_id = match.id
                cliente_nome = match.ragione_sociale

        try:
            # Deduplicazione per email
            existing = None
            if email:
                existing = db.query(ContattoORM).filter(
                    ContattoORM.email == email
                ).first()

            if existing:
                # Aggiorna solo se ci sono cambiamenti
                changed = False
                updates = {
                    "nome": nome or existing.nome,
                    "cognome": cognome or existing.cognome,
                    "telefono": telefono or existing.telefono,
                    "ruolo": ruolo or existing.ruolo,
                    "cliente_id": cliente_id or existing.cliente_id,
                    "cliente_nome": cliente_nome or existing.cliente_nome,
                }
                for k, v in updates.items():
                    if v and getattr(existing, k) != v:
                        setattr(existing, k, v)
                        changed = True
                if changed:
                    db.commit()
                    updated += 1
                else:
                    skipped += 1
            else:
                # Crea nuovo contatto
                obj = ContattoORM(
                    nome=nome or cognome,
                    cognome=cognome,
                    email=email,
                    telefono=telefono,
                    ruolo=ruolo,
                    cliente_id=cliente_id,
                    cliente_nome=cliente_nome,
                    note=f"Importato da Google Contacts",
                )
                db.add(obj)
                db.commit()
                synced += 1

        except Exception as e:
            db.rollback()
            errors.append(f"{nome} {cognome}: {str(e)}")
            continue

    log_action(
        db, "SYNC_GOOGLE_CONTACTS", "Contatti", "", current_user,
        f"Sync: {synced} nuovi, {updated} aggiornati, {skipped} saltati"
    )

    return {
        "synced": synced,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],
    }

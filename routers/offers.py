"""Router Offerte – PostgreSQL via SQLAlchemy."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.offer import Offerta, OffertaCreate, OffertaUpdate
from models.db_models import Offerta as OffertaORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/offerte", tags=["offerte"])


@router.get("/", response_model=list[Offerta])
async def lista_offerte(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(OffertaORM).order_by(OffertaORM.data_creazione.desc()).all()
    return [_offerta_dict(r) for r in records]


@router.get("/{offerta_id}", response_model=Offerta)
async def get_offerta(offerta_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    r = db.query(OffertaORM).filter(OffertaORM.id == offerta_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    return _offerta_dict(r)


@router.post("/", response_model=Offerta, status_code=201)
async def crea_offerta(data: OffertaCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    d = data.model_dump()
    # Converti num_solleciti in int
    try:
        d["num_solleciti"] = int(d.get("num_solleciti") or 0)
    except (ValueError, TypeError):
        d["num_solleciti"] = 0
    obj = OffertaORM(**d)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Offerte", obj.id, current_user, data.descrizione or "")
    return _offerta_dict(obj)


@router.put("/{offerta_id}", response_model=Offerta)
async def aggiorna_offerta(offerta_id: str, data: OffertaUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(OffertaORM).filter(OffertaORM.id == offerta_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "num_solleciti" in updates:
        try:
            updates["num_solleciti"] = int(updates["num_solleciti"])
        except (ValueError, TypeError):
            updates["num_solleciti"] = 0
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Offerte", offerta_id, current_user, str(updates))
    return _offerta_dict(obj)


@router.delete("/{offerta_id}", status_code=204)
async def elimina_offerta(offerta_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(OffertaORM).filter(OffertaORM.id == offerta_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Offerte", offerta_id, current_user)


# ─── Azioni email ─────────────────────────────────────────────────────────────

class EmailRichiestaBody(BaseModel):
    email_destinatario: str
    scadenza: str = ""


class SollecitaBody(BaseModel):
    email_destinatario: str


@router.post("/{offerta_id}/invia-richiesta")
async def invia_richiesta_preventivo(offerta_id: str, body: EmailRichiestaBody,
                                      db: Session = Depends(get_db),
                                      current_user: str = Depends(get_current_user)):
    obj = db.query(OffertaORM).filter(OffertaORM.id == offerta_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    try:
        import services.gmail_service as gmail
        subject, body_html = gmail.template_richiesta_preventivo(
            fornitore_nome=obj.fornitore_nome or "",
            progetto_nome=obj.progetto_nome or "",
            descrizione=obj.descrizione or "",
            scadenza=body.scadenza,
        )
        gmail.invia_email(body.email_destinatario, subject, body_html)
    except Exception as e:
        print(f"[Offerte] Email non inviata: {e}")

    obj.stato = "Inviata"
    obj.data_invio_richiesta = date.today().strftime("%Y-%m-%d")
    db.commit()
    log_action(db, "EMAIL_RICHIESTA", "Offerte", offerta_id, current_user,
               f"Email a {body.email_destinatario}")
    return {"ok": True}


@router.post("/{offerta_id}/sollecita")
async def sollecita_offerta(offerta_id: str, body: SollecitaBody,
                             db: Session = Depends(get_db),
                             current_user: str = Depends(get_current_user)):
    obj = db.query(OffertaORM).filter(OffertaORM.id == offerta_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Offerta non trovata")

    num_solleciti = (obj.num_solleciti or 0) + 1

    try:
        import services.gmail_service as gmail
        subject, body_html = gmail.template_sollecito(
            fornitore_nome=obj.fornitore_nome or "",
            progetto_nome=obj.progetto_nome or "",
            descrizione=obj.descrizione or "",
            data_invio_originale=obj.data_invio_richiesta or "",
            num_sollecito=num_solleciti,
        )
        gmail.invia_email(body.email_destinatario, subject, body_html)
    except Exception as e:
        print(f"[Offerte] Sollecito non inviato: {e}")

    obj.num_solleciti = num_solleciti
    db.commit()
    log_action(db, "SOLLECITO", "Offerte", offerta_id, current_user,
               f"Sollecito n.{num_solleciti} a {body.email_destinatario}")
    return {"ok": True, "num_solleciti": num_solleciti}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _offerta_dict(obj) -> dict:
    d = to_dict(obj)
    # num_solleciti è int nel DB, il modello Pydantic vuole str
    d["num_solleciti"] = str(d.get("num_solleciti", "0"))
    return d

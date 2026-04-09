"""Router Attività – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.task import Attivita, AttivitaCreate, AttivitaUpdate
from models.db_models import Attivita as AttivitaORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/attivita", tags=["attività"])


@router.get("/", response_model=list[Attivita])
async def lista_attivita(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(AttivitaORM).order_by(AttivitaORM.scadenza).all()
    return [to_dict(r) for r in records]


@router.get("/{task_id}", response_model=Attivita)
async def get_attivita(task_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    r = db.query(AttivitaORM).filter(AttivitaORM.id == task_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Attività non trovata")
    return to_dict(r)


@router.post("/", response_model=Attivita, status_code=201)
async def crea_attivita(data: AttivitaCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = AttivitaORM(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Attività", obj.id, current_user, data.titolo)
    return to_dict(obj)


@router.put("/{task_id}", response_model=Attivita)
async def aggiorna_attivita(task_id: str, data: AttivitaUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(AttivitaORM).filter(AttivitaORM.id == task_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Attività non trovata")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Attività", task_id, current_user, str(updates))
    return to_dict(obj)


@router.delete("/{task_id}", status_code=204)
async def elimina_attivita(task_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(AttivitaORM).filter(AttivitaORM.id == task_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Attività non trovata")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Attività", task_id, current_user)

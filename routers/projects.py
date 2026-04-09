"""Router Progetti – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.project import Progetto, ProgettoCreate, ProgettoUpdate
from models.db_models import Progetto as ProgettoORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/progetti", tags=["progetti"])


@router.get("/", response_model=list[Progetto])
async def lista_progetti(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(ProgettoORM).order_by(ProgettoORM.data_creazione.desc()).all()
    return [to_dict(r) for r in records]


@router.get("/{progetto_id}", response_model=Progetto)
async def get_progetto(progetto_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    r = db.query(ProgettoORM).filter(ProgettoORM.id == progetto_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return to_dict(r)


@router.post("/", response_model=Progetto, status_code=201)
async def crea_progetto(data: ProgettoCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = ProgettoORM(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Progetti", obj.id, current_user, data.nome)
    return to_dict(obj)


@router.put("/{progetto_id}", response_model=Progetto)
async def aggiorna_progetto(progetto_id: str, data: ProgettoUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(ProgettoORM).filter(ProgettoORM.id == progetto_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Progetti", progetto_id, current_user, str(updates))
    return to_dict(obj)


@router.delete("/{progetto_id}", status_code=204)
async def elimina_progetto(progetto_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(ProgettoORM).filter(ProgettoORM.id == progetto_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Progetti", progetto_id, current_user)

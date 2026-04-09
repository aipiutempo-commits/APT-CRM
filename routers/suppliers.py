"""Router Fornitori – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.supplier import Fornitore, FornitoreCreate, FornitoreUpdate
from models.db_models import Fornitore as FornitoreORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/fornitori", tags=["fornitori"])


@router.get("/", response_model=list[Fornitore])
async def lista_fornitori(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(FornitoreORM).order_by(FornitoreORM.ragione_sociale).all()
    return [to_dict(r) for r in records]


@router.get("/{fornitore_id}", response_model=Fornitore)
async def get_fornitore(fornitore_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    r = db.query(FornitoreORM).filter(FornitoreORM.id == fornitore_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return to_dict(r)


@router.post("/", response_model=Fornitore, status_code=201)
async def crea_fornitore(data: FornitoreCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = FornitoreORM(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Fornitori", obj.id, current_user, data.ragione_sociale)
    return to_dict(obj)


@router.put("/{fornitore_id}", response_model=Fornitore)
async def aggiorna_fornitore(fornitore_id: str, data: FornitoreUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(FornitoreORM).filter(FornitoreORM.id == fornitore_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Fornitori", fornitore_id, current_user, str(updates))
    return to_dict(obj)


@router.delete("/{fornitore_id}", status_code=204)
async def elimina_fornitore(fornitore_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(FornitoreORM).filter(FornitoreORM.id == fornitore_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Fornitori", fornitore_id, current_user)

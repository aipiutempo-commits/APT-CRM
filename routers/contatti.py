"""Router Contatti – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.contact import Contatto, ContattoCreate, ContattoUpdate
from models.db_models import Contatto as ContattoORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/contatti", tags=["contatti"])


@router.get("/", response_model=list[Contatto])
async def lista_contatti(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(ContattoORM).order_by(ContattoORM.cognome, ContattoORM.nome).all()
    return [to_dict(r) for r in records]


@router.get("/by-cliente/{cliente_id}", response_model=list[Contatto])
async def contatti_by_cliente(cliente_id: str, db: Session = Depends(get_db),
                               current_user: str = Depends(get_current_user)):
    records = db.query(ContattoORM).filter(ContattoORM.cliente_id == cliente_id).all()
    return [to_dict(r) for r in records]


@router.get("/{contatto_id}", response_model=Contatto)
async def get_contatto(contatto_id: str, db: Session = Depends(get_db),
                        current_user: str = Depends(get_current_user)):
    r = db.query(ContattoORM).filter(ContattoORM.id == contatto_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Contatto non trovato")
    return to_dict(r)


@router.post("/", response_model=Contatto, status_code=201)
async def crea_contatto(data: ContattoCreate, db: Session = Depends(get_db),
                         current_user: str = Depends(get_current_user)):
    obj = ContattoORM(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Contatti", obj.id, current_user, f"{data.nome} {data.cognome}")
    return to_dict(obj)


@router.put("/{contatto_id}", response_model=Contatto)
async def aggiorna_contatto(contatto_id: str, data: ContattoUpdate,
                             db: Session = Depends(get_db),
                             current_user: str = Depends(get_current_user)):
    obj = db.query(ContattoORM).filter(ContattoORM.id == contatto_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contatto non trovato")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Contatti", contatto_id, current_user, str(updates))
    return to_dict(obj)


@router.delete("/{contatto_id}", status_code=204)
async def elimina_contatto(contatto_id: str, db: Session = Depends(get_db),
                            current_user: str = Depends(get_current_user)):
    obj = db.query(ContattoORM).filter(ContattoORM.id == contatto_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contatto non trovato")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Contatti", contatto_id, current_user)

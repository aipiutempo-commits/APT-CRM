"""Router Clienti – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.client import Cliente, ClienteCreate, ClienteUpdate
from models.db_models import Cliente as ClienteORM
from routers.auth import get_current_user
from services.database import get_db, to_dict, log_action

router = APIRouter(prefix="/api/clienti", tags=["clienti"])


@router.get("/", response_model=list[Cliente])
async def lista_clienti(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    records = db.query(ClienteORM).order_by(ClienteORM.ragione_sociale).all()
    return [to_dict(r) for r in records]


@router.get("/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    r = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return to_dict(r)


@router.post("/", response_model=Cliente, status_code=201)
async def crea_cliente(data: ClienteCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = ClienteORM(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    log_action(db, "CREATE", "Clienti", obj.id, current_user, data.ragione_sociale)
    return to_dict(obj)


@router.put("/{cliente_id}", response_model=Cliente)
async def aggiorna_cliente(cliente_id: str, data: ClienteUpdate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    log_action(db, "UPDATE", "Clienti", cliente_id, current_user, str(updates))
    return to_dict(obj)


@router.delete("/{cliente_id}", status_code=204)
async def elimina_cliente(cliente_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    obj = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    db.delete(obj)
    db.commit()
    log_action(db, "DELETE", "Clienti", cliente_id, current_user)

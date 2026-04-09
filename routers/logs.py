"""Router Log – PostgreSQL via SQLAlchemy."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.db_models import LogEntry
from routers.auth import get_current_user
from services.database import get_db, to_dict

router = APIRouter(prefix="/api/log", tags=["log"])


@router.get("/")
async def lista_log(limite: int = 200, db: Session = Depends(get_db),
                    current_user: str = Depends(get_current_user)):
    records = (
        db.query(LogEntry)
        .order_by(LogEntry.timestamp.desc())
        .limit(limite)
        .all()
    )
    return [to_dict(r) for r in records]

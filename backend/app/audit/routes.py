from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("")
def get_audit_trail(session: Session = Depends(get_session)):
    events = session.exec(select(AuditEvent).order_by(AuditEvent.timestamp.asc())).all()
    return events

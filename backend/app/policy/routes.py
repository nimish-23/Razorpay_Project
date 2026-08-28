from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from app.models import Policy, PolicyCreateRequest

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("")
def create_policy(req: PolicyCreateRequest, session: Session = Depends(get_session)):
    # Only one policy should be "active" at a time — deactivate any existing one first
    existing = session.exec(select(Policy).where(Policy.active == True)).all()
    for p in existing:
        p.active = False
        session.add(p)

    policy = Policy(
        max_amount=req.max_amount,
        merchant_id=req.merchant_id,
        allowed_categories=",".join(req.allowed_categories),
        expires_at=req.expires_at,
        require_confirmation_above=req.require_confirmation_above,
        active=True,
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return policy


@router.get("/active")
def get_active_policy(session: Session = Depends(get_session)):
    policy = session.exec(select(Policy).where(Policy.active == True)).first()
    if not policy:
        raise HTTPException(status_code=404, detail="No active policy set")
    return policy

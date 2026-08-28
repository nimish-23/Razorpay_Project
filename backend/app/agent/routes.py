from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import json

from app.db import get_session
from app.models import IntentRequest, Proposal, IntentResponse, Policy, Decision, AuditEvent
from app.policy.engine import evaluate

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/intent", response_model=IntentResponse)
def process_intent(request: IntentRequest, session: Session = Depends(get_session)):
    """
    Accepts a natural-language purchase request.
    Generates a proposal and evaluates it against the active policy.
    """
    # M8: Log intent received
    session.add(AuditEvent(event_type="intent", payload=json.dumps({"text": request.text})))
    session.commit()

    # M5: Generate a hardcoded Proposal
    proposal = Proposal(
        product_id="p_001",
        product_name="Sample Gift Box",
        amount=150000,
        merchant_id="rzp_test_merchant_123",
        category="gifts",
        reasoning="Hardcoded response for M5."
    )
    
    # M8: Log proposal generated
    session.add(AuditEvent(event_type="proposal", payload=proposal.model_dump_json()))
    session.commit()
    
    # M6: Pipeline wiring - fetch policy and evaluate
    active_policy = session.exec(select(Policy).where(Policy.active == True)).first()
    
    if not active_policy:
        decision = Decision(allowed=False, reason="No active policy found", rule_triggered=None)
    else:
        decision = evaluate(proposal, active_policy)
        
    # M8: Log policy check
    session.add(AuditEvent(event_type="policy_check", payload=decision.model_dump_json()))
    session.commit()
        
    return IntentResponse(proposal=proposal, decision=decision)

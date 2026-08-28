from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from pydantic import BaseModel
import json

from app.db import get_session
from app.models import AuditEvent
from .razorpay_client import client

router = APIRouter(prefix="/payments", tags=["Payments"])

class PaymentExecuteRequest(BaseModel):
    amount: int  # paise
    receipt: str = "order_receipt"

class PaymentExecuteResponse(BaseModel):
    order_id: str
    amount: int
    currency: str

@router.post("/execute", response_model=PaymentExecuteResponse)
def execute_payment(req: PaymentExecuteRequest, session: Session = Depends(get_session)):
    try:
        data = {
            "amount": req.amount,
            "currency": "INR",
            "receipt": req.receipt,
        }
        order = client.order.create(data=data)
        
        # M8: Log payment created
        session.add(AuditEvent(
            event_type="payment_created", 
            payload=json.dumps({"order_id": order["id"], "amount": order["amount"]})
        ))
        session.commit()
        
        return PaymentExecuteResponse(
            order_id=order["id"],
            amount=order["amount"],
            currency=order["currency"]
        )
    except Exception as e:
        # M8: Log payment failed
        session.add(AuditEvent(
            event_type="payment_failed",
            payload=json.dumps({"error": str(e)})
        ))
        session.commit()
        raise HTTPException(status_code=500, detail=str(e))

# TODO: POST /payments/webhook (optional)

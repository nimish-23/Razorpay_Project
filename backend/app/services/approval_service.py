from typing import Optional

from sqlmodel import Session

from app.models.agent_authorization import AgentAuthorization
from app.models.order import Order
from app.services.audit_service import AuditService


class ApprovalService:

    def __init__(self, session: Session):
        self.session = session

    def approve(
        self,
        order: Optional[Order],
        authorization: Optional[AgentAuthorization],
        session_id: str,
    ) -> tuple[Optional[Order], str]:
        audit_service = AuditService(self.session, session_id)

        if not order or order.session_id != session_id:
            if order:
                audit_service.log_approval_failed(
                    order_id=order.order_id,
                    agent_id=authorization.agent_id if authorization else None,
                    amount=order.amount,
                    reason="Order does not belong to the current session.",
                )
            return None, "order_not_found"

        if order.status != "approval_required":
            audit_service.log_approval_failed(
                order_id=order.order_id,
                agent_id=authorization.agent_id if authorization else None,
                amount=order.amount,
                reason="Order is not waiting for user approval.",
            )
            return None, "not_awaiting_approval"

        if not authorization:
            audit_service.log_approval_failed(
                order_id=order.order_id,
                agent_id=None,
                amount=order.amount,
                reason="No active authorization exists for the current session.",
            )
            return None, "not_authorized"

        order.status = "approved"
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        audit_service.log_transaction_approved(
            order_id=order.order_id,
            agent_id=authorization.agent_id,
            amount=order.amount,
        )
        return order, "approved"

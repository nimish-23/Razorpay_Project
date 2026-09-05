from typing import Any, Optional
from sqlmodel import Session, select

from app.models.audit_log import AuditLog
from app.models.order import Order


class AuditService:

    def __init__(
        self,
        session: Session,
        session_id: str = ""
    ):
        self.session = session
        self.session_id = session_id

    def log_event(
        self,
        tool_name: str,
        decision: str = "success",
        reason: str = "",
        input_data: Optional[dict[str, Any]] = None,
        result_data: Optional[dict[str, Any]] = None,
        order_id: Optional[str] = None,
        event_id: Optional[str] = None,
        commit: bool = True,
    ) -> AuditLog:
        audit_log = AuditLog(
            session_id=self.session_id,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            input=input_data or {},
            result=result_data or {},
            order_id=order_id,
            event_id=event_id,
        )
        
        self.session.add(audit_log)
        if commit:
            self.session.commit()
            self.session.refresh(audit_log)
        return audit_log

    def log_catalog_search(
        self,
        query: Optional[str] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
        product_ids: Optional[list[str]] = None,
        products: Optional[list[dict[str, Any]]] = None,
    ) -> AuditLog:
        returned_products = products or []
        returned_product_ids = product_ids or [
            product["id"]
            for product in returned_products
            if "id" in product
        ]
        return self.log_event(
            tool_name="catalog_search",
            decision="success",
            reason=f"Catalog searched with query: '{query}'." if query else "Catalog searched.",
            input_data={
                "query": query,
                "max_price": max_price,
                "category": category,
                "attributes": attributes or {},
            },
            result_data={
                "count": len(returned_products) if products is not None else len(returned_product_ids),
                "products": returned_products,
                "product_ids": returned_product_ids,
            },
            order_id=None,
        )

    def log_order_created(self, order: Order) -> AuditLog:
        return self.log_event(
            tool_name="order_created",
            decision="created",
            reason=f"Order '{order.order_id}' created.",
            input_data={
                "item_id": order.item_id,
                "qty": order.qty,
                "selected_attributes": order.selected_attributes or {},
            },
            result_data={
                "order_id": order.order_id,
                "item_id": order.item_id,
                "qty": order.qty,
                "amount": order.amount,
                "currency": order.currency,
                "status": order.status,
                "selected_attributes": order.selected_attributes or {},
            },
            order_id=order.order_id,
        )

    def log_payment_initiated(
        self,
        order_id: str,
        razorpay_order_id: str,
        payment_link_id: str,
        amount: float,
        currency: str,
    ) -> AuditLog:
        return self.log_event(
            tool_name="payment_initiated",
            decision="initiated",
            reason=f"Payment link initiated for order '{order_id}'.",
            input_data={
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
            },
            result_data={
                "order_id": order_id,
                "razorpay_order_id": razorpay_order_id,
                "payment_link_id": payment_link_id,
                "amount": amount,
                "currency": currency,
            },
            order_id=order_id,
        )

    def log_payment_status_changed(
        self,
        order_id: str,
        status: str,
        razorpay_status: Optional[str] = None,
        payment_id: Optional[str] = None,
        amount_paid: Optional[float] = None,
        event_id: Optional[str] = None,
        event_name: Optional[str] = None,
    ) -> AuditLog:
        return self.log_event(
            tool_name="payment_status_changed",
            decision=status,
            reason=f"Payment status changed to '{status}'.",
            input_data={
                "order_id": order_id,
                "event": event_name,
            },
            result_data={
                "order_id": order_id,
                "status": status,
                "razorpay_status": razorpay_status,
                "payment_id": payment_id,
                "amount_paid": amount_paid,
            },
            order_id=order_id,
            event_id=event_id,
        )

    def log_payment_finished(
        self,
        order_id: str,
        payment_id: Optional[str],
        amount_paid: float,
    ) -> AuditLog:
        return self.log_event(
            tool_name="payment_finished",
            decision="paid",
            reason=f"Payment finished successfully for order '{order_id}'.",
            input_data={
                "order_id": order_id,
                "payment_id": payment_id,
            },
            result_data={
                "order_id": order_id,
                "payment_id": payment_id,
                "amount_paid": amount_paid,
            },
            order_id=order_id,
        )

    def log_order_placed(
        self,
        order_id: str,
        status: str = "paid",
    ) -> AuditLog:
        return self.log_event(
            tool_name="order_placed",
            decision="placed",
            reason=f"Order '{order_id}' placed and completed successfully.",
            input_data={
                "order_id": order_id,
            },
            result_data={
                "order_id": order_id,
                "status": status,
            },
            order_id=order_id,
        )

    def log_transaction_approved(
        self,
        order_id: str,
        agent_id: str,
        amount: float,
    ) -> AuditLog:
        return self.log_event(
            tool_name="transaction_approved",
            decision="approved",
            reason="Transaction approved by the user.",
            input_data={
                "order_id": order_id,
                "agent_id": agent_id,
                "amount": amount,
                "session_id": self.session_id,
            },
            result_data={
                "order_id": order_id,
                "approved": True,
                "amount": amount,
            },
            order_id=order_id,
        )

    def log_approval_failed(
        self,
        order_id: str,
        agent_id: str | None,
        amount: float,
        reason: str,
    ) -> AuditLog:
        return self.log_event(
            tool_name="approval_failed",
            decision="denied",
            reason=reason,
            input_data={
                "order_id": order_id,
                "agent_id": agent_id,
                "amount": amount,
                "session_id": self.session_id,
            },
            result_data={
                "order_id": order_id,
                "approved": False,
                "reason": reason,
            },
            order_id=order_id,
        )

    def get_order_history(self, order_id: str) -> list[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.order_id == order_id)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        )
        if self.session_id:
            statement = statement.where(AuditLog.session_id == self.session_id)
        return list(self.session.exec(statement).all())

    def get_by_event_id(self, event_id: str) -> Optional[AuditLog]:
        statement = select(AuditLog).where(AuditLog.event_id == event_id)
        return self.session.exec(statement).first()

    def get_recent_logs(
        self,
        limit: int = 50,
        session_id: Optional[str] = None,
    ) -> list[AuditLog]:
        statement = (
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        effective_session_id = session_id if session_id is not None else self.session_id
        if effective_session_id:
            statement = statement.where(AuditLog.session_id == effective_session_id)
        return list(self.session.exec(statement).all())


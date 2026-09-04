from typing import Any

from sqlmodel import Session, select
from app.models.order import Order
from app.services.audit_service import AuditService


class WebhookService:

    def __init__(self, session: Session):
        self.session = session
        self.audit_service = AuditService(session)

    def process_razorpay_event(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:

        event_name = event.get("event")
        event_id = event.get("event_id")

        if event_id:
            existing_event = self.audit_service.get_by_event_id(event_id)

            if existing_event:
                return {
                    "success": True,
                    "processed": False,
                    "duplicate": True,
                    "event": event_name,
                    "event_id": event_id,
                    "message": "Webhook event already processed.",
                }

        handled_events = {
            "payment_link.paid",
            "payment_link.partially_paid",
            "payment_link.cancelled",
            "payment_link.expired",
        }

        if event_name not in handled_events:
            return {
                "success": True,
                "processed": False,
                "message": f"Event '{event_name}' is not handled.",
            }

        payment_link_entity = (
            event.get("payload", {})
            .get("payment_link", {})
            .get("entity", {})
        )

        payment_link_id = payment_link_entity.get("id")

        if not payment_link_id:
            return {
                "success": False,
                "processed": False,
                "message": "Payment Link ID not found in webhook.",
            }

        statement = select(Order).where(
            Order.razorpay_payment_link_id == payment_link_id
        )

        order = self.session.exec(statement).first()

        if order is None:
            return {
                "success": False,
                "processed": False,
                "message": (
                    f"No local order found for "
                    f"Payment Link '{payment_link_id}'."
                ),
            }

        self.audit_service = AuditService(
            self.session,
            order.session_id,
        )

        status_map = {
            "payment_link.paid": "paid",
            "payment_link.partially_paid": "partially_paid",
            "payment_link.cancelled": "cancelled",
            "payment_link.expired": "expired",
        }

        order.status = status_map[event_name]

        amount_paid_paise = payment_link_entity.get(
            "amount_paid",
            0,
        )

        payments = payment_link_entity.get(
            "payments",
            [],
        )

        payment_id = None

        if payments:
            payment_id = payments[0].get("payment_id")

        if payment_id:
            order.razorpay_payment_id = payment_id

        self.session.add(order)

        self.session.commit()
        self.session.refresh(order)

        self.audit_service.log_payment_status_changed(
            order_id=order.order_id,
            status=order.status,
            razorpay_status=payment_link_entity.get("status"),
            payment_id=order.razorpay_payment_id,
            amount_paid=amount_paid_paise / 100,
            event_id=event_id,
            event_name=event_name,
        )

        if order.status == "paid":
            self.audit_service.log_payment_finished(
                order_id=order.order_id,
                payment_id=order.razorpay_payment_id,
                amount_paid=amount_paid_paise / 100,
            )
            self.audit_service.log_order_placed(
                order_id=order.order_id,
                status=order.status,
            )

        return {
            "success": True,
            "processed": True,
            "event": event_name,
            "order_id": order.order_id,
            "payment_link_id": order.razorpay_payment_link_id,
            "payment_id": order.razorpay_payment_id,
            "status": order.status,
            "amount_paid": amount_paid_paise / 100,
        }
from typing import Any

from sqlmodel import Session

from app.models.order import Order
from app.razorpay_client import client
from app.services.audit_service import AuditService


class PaymentService:

    def __init__(self, session: Session):
        self.session = session
        self.audit_service = AuditService(
            session,
            session_id=""
        )

    def create_payment(
        self,
        order: Order,
        product_name: str,
    ) -> dict[str, Any]:

        if order.razorpay_payment_link_id:
            status = self.get_payment_status(order)

            payment_link = client.payment_link.fetch(
                order.razorpay_payment_link_id
            )

            return {
                "order_id": order.order_id,
                "razorpay_order_id": order.razorpay_order_id,
                "payment_link_id": order.razorpay_payment_link_id,
                "payment_url": payment_link["short_url"],
                "amount": order.amount,
                "currency": order.currency,
                "status": status["status"],
                "razorpay_status": status["razorpay_status"],
                "payment_id": status["payment_id"],
                "amount_paid": status["amount_paid"],
            }

        # Razorpay expects the amount in paise.
        amount_paise = int(round(order.amount * 100))

        # 1. Create Razorpay Order
        razorpay_order = client.order.create(
            data={
                "amount": amount_paise,
                "currency": order.currency,
                "receipt": order.order_id,
                "notes": {
                    "local_order_id": order.order_id,
                    "product_name": product_name,
                },
            }
        )

        razorpay_order_id = razorpay_order["id"]

        # 2. Create Razorpay Payment Link
        payment_link = client.payment_link.create(
            data={
                "amount": amount_paise,
                "currency": order.currency,
                "accept_partial": False,
                "reference_id": order.order_id,
                "description": (
                    f"Payment for {product_name}"
                ),
                "notes": {
                    "local_order_id": order.order_id,
                    "razorpay_order_id": razorpay_order_id,
                },
            }
        )

        # 3. Save Razorpay IDs locally
        order.razorpay_order_id = razorpay_order_id
        order.razorpay_payment_link_id = payment_link["id"]

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        self.audit_service.log_payment_initiated(
            order_id=order.order_id,
            razorpay_order_id=razorpay_order_id,
            payment_link_id=payment_link["id"],
            amount=order.amount,
            currency=order.currency,
        )

        return {
            "order_id": order.order_id,
            "razorpay_order_id": razorpay_order_id,
            "payment_link_id": payment_link["id"],
            "payment_url": payment_link["short_url"],
            "amount": order.amount,
            "currency": order.currency,
            "status": order.status,
        }


    def get_payment_status(self, order: Order) -> dict[str, Any]:
        if not order.razorpay_payment_link_id:
            raise ValueError(
                f"Order '{order.order_id}' does not have a Razorpay payment link."
            )

        payment_link = client.payment_link.fetch(
            order.razorpay_payment_link_id
        )

        razorpay_status = payment_link.get("status")
        amount_paid_paise = payment_link.get("amount_paid", 0)

        # Map Razorpay status to our local order status
        status_map = {
            "paid": "paid",
            "partially_paid": "partially_paid",
            "created": "pending_payment",
            "expired": "expired",
            "cancelled": "cancelled",
        }

        local_status = status_map.get(
            razorpay_status,
            "pending_payment"
        )

        old_status = order.status
        order.status = local_status

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        payment_id = None
        payments = payment_link.get("payments")

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
            razorpay_status=razorpay_status,
            payment_id=payment_id,
            amount_paid=amount_paid_paise / 100,
        )

        if local_status == "paid" and old_status != "paid":
            self.audit_service.log_payment_finished(
                order_id=order.order_id,
                payment_id=payment_id,
                amount_paid=amount_paid_paise / 100,
            )
            self.audit_service.log_order_placed(
                order_id=order.order_id,
                status=order.status,
            )

        return {
            "order_id": order.order_id,
            "razorpay_order_id": order.razorpay_order_id,
            "payment_link_id": order.razorpay_payment_link_id,
            "payment_id": payment_id,
            "razorpay_status": razorpay_status,
            "status": order.status,
            "amount": order.amount,
            "amount_paid": amount_paid_paise / 100,
            "currency": order.currency,
        }
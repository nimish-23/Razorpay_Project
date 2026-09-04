import pytest
from razorpay.errors import BadRequestError

from app.db import get_session
from app.services.order_service import OrderService
from app.models.order import Order


def test_get_order_status():

    order_id = "ORD-EC054B07E83B"

    with get_session() as session:

        order = session.get(Order, order_id)

        assert order is not None
        assert order.razorpay_payment_link_id is not None

        order_service = OrderService(session)

        try:
            result = order_service.sync_payment_status(
                order_id=order_id
            )
        except BadRequestError as error:
            if str(error) == "The id provided does not exist":
                pytest.skip(
                    "Skipping obsolete fixture: the referenced Razorpay "
                    "Payment Link no longer exists."
                )
            raise

        print("\nORDER STATUS SYNC")
        print("--------------------")
        print("Order ID:", result["order_id"])
        print("Razorpay Order ID:", result["razorpay_order_id"])
        print("Payment Link ID:", result["payment_link_id"])
        print("Payment ID:", result["payment_id"])
        print("Razorpay Status:", result["razorpay_status"])
        print("Local Status:", result["status"])
        print("Amount:", result["amount"])
        print("Amount Paid:", result["amount_paid"])
        print("Currency:", result["currency"])

        assert result["razorpay_status"] in {
            "created",
            "partially_paid",
            "paid",
            "expired",
            "cancelled",
        }

        assert result["status"] == {
            "created": "pending_payment",
            "partially_paid": "partially_paid",
            "paid": "paid",
            "expired": "expired",
            "cancelled": "cancelled",
        }[result["razorpay_status"]]

        assert result["amount_paid"] >= 0
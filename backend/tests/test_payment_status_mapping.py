from unittest.mock import patch

from app.db import get_session
from app.models.order import Order
from app.services.payment_service import PaymentService


def test_expired_payment_status():
    with get_session() as session:
        order = session.get(
            Order,
            "ORD-99BAC5331F47"
        )

        assert order is not None

        fake_payment_link = {
            "status": "expired",
            "amount_paid": 0,
            "payments": [],
        }

        with patch(
            "app.services.payment_service.client.payment_link.fetch",
            return_value=fake_payment_link,
        ):
            service = PaymentService(session)

            result = service.get_payment_status(order)

        print("\nEXPIRED PAYMENT TEST")
        print("--------------------")
        print("Razorpay Status:", result["razorpay_status"])
        print("Local Status:", result["status"])
        print("Amount Paid:", result["amount_paid"])

        assert result["razorpay_status"] == "expired"
        assert result["status"] == "expired"
        assert result["amount_paid"] == 0

def test_cancelled_payment_status():
    with get_session() as session:
        order = session.get(
            Order,
            "ORD-99BAC5331F47"
        )

        assert order is not None

        fake_payment_link = {
            "status": "cancelled",
            "amount_paid": 0,
            "payments": [],
        }

        with patch(
            "app.services.payment_service.client.payment_link.fetch",
            return_value=fake_payment_link,
        ):
            service = PaymentService(session)

            result = service.get_payment_status(order)

        print("\nCANCELLED PAYMENT TEST")
        print("----------------------")
        print("Razorpay Status:", result["razorpay_status"])
        print("Local Status:", result["status"])
        print("Amount Paid:", result["amount_paid"])

        assert result["razorpay_status"] == "cancelled"
        assert result["status"] == "cancelled"
        assert result["amount_paid"] == 0

def test_partially_paid_payment_status():
    with get_session() as session:
        order = session.get(
            Order,
            "ORD-99BAC5331F47"
        )

        assert order is not None

        fake_payment_link = {
            "status": "partially_paid",
            "amount_paid": 100000,
            "payments": [
                {
                    "payment_id": "pay_TEST_PARTIAL"
                }
            ],
        }

        with patch(
            "app.services.payment_service.client.payment_link.fetch",
            return_value=fake_payment_link,
        ):
            service = PaymentService(session)

            result = service.get_payment_status(order)

        print("\nPARTIALLY PAID PAYMENT TEST")
        print("---------------------------")
        print("Razorpay Status:", result["razorpay_status"])
        print("Local Status:", result["status"])
        print("Amount Paid:", result["amount_paid"])
        print("Payment ID:", result["payment_id"])

        assert result["razorpay_status"] == "partially_paid"
        assert result["status"] == "partially_paid"
        assert result["amount_paid"] == 1000.0
        assert result["payment_id"] == "pay_TEST_PARTIAL"
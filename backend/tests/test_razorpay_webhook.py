from app.db import get_session
from app.models.order import Order
from app.services.webhook_service import WebhookService


def test_payment_link_paid_webhook():

    payment_link_id = "plink_TXgIuRlVW8cDL9"
    order_id = "ORD-BBEEB736DE74"

    webhook_event = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": payment_link_id,
                    "amount": 439800,
                    "amount_paid": 439800,
                    "status": "paid",
                    "payments": [
                        {
                            "payment_id": "pay_TEST_WEBHOOK_123"
                        }
                    ],
                }
            }
        },
    }

    with get_session() as session:

        service = WebhookService(session)

        result = service.process_razorpay_event(
            webhook_event
        )

        print("\nWEBHOOK TEST")
        print("--------------------")
        print("Event:", result["event"])
        print("Order ID:", result["order_id"])
        print("Payment Link ID:", result["payment_link_id"])
        print("Payment ID:", result["payment_id"])
        print("Status:", result["status"])
        print("Amount Paid:", result["amount_paid"])

        assert result["success"] is True
        assert result["processed"] is True
        assert result["order_id"] == order_id
        assert result["status"] == "paid"
        assert result["payment_id"] == "pay_TEST_WEBHOOK_123"
        assert result["amount_paid"] == 4398.0

        order = session.get(Order, order_id)

        assert order is not None
        assert order.status == "paid"
        assert order.razorpay_payment_id == "pay_TEST_WEBHOOK_123"
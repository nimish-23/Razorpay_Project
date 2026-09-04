import json
from pathlib import Path
from unittest.mock import patch

from app.db import get_session
from app.models.order import Order
from app.razorpay_client import client


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_get_razorpay_payment():

    assert TEST_DATA_FILE.exists(), (
        "test_payment_data.json not found. "
        "Run the previous tests first."
    )

    data = json.loads(
        TEST_DATA_FILE.read_text(encoding="utf-8")
    )

    order_id = data["order_id"]
    razorpay_order_id = data["razorpay_order_id"]

    with get_session() as session:

        order = session.get(Order, order_id)

        assert order is not None

        mock_payments = {
            "entity": "collection",
            "count": 0,
            "items": [],
        }

        with patch.object(client.order, "payments", return_value=mock_payments):
            payments = client.order.payments(
                razorpay_order_id
            )

            print("\nRAZORPAY PAYMENTS (MOCKED)")
            print("--------------------")
            print("Local Order ID:", order_id)
            print("Razorpay Order ID:", razorpay_order_id)
            print("Payment Count:", payments.get("count", 0))

            for payment in payments.get("items", []):
                print("\nPayment ID:", payment["id"])
                print("Status:", payment["status"])
                print("Amount:", payment["amount"] / 100)
                print("Method:", payment.get("method"))

            assert payments["entity"] == "collection"
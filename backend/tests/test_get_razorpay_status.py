import json
from pathlib import Path
from unittest.mock import patch

from app.db import get_session
from app.models.order import Order
from app.razorpay_client import client


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_get_razorpay_status():

    assert TEST_DATA_FILE.exists(), (
        "test_payment_data.json not found. "
        "Run test_create_order.py and test_create_payment.py first."
    )

    data = json.loads(
        TEST_DATA_FILE.read_text(encoding="utf-8")
    )

    order_id = data["order_id"]
    razorpay_order_id = data["razorpay_order_id"]

    with get_session() as session:

        order = session.get(Order, order_id)

        assert order is not None

        mock_order = {
            "id": razorpay_order_id,
            "status": "created",
            "amount": int(order.amount * 100),
            "amount_paid": 0,
            "amount_due": int(order.amount * 100),
        }

        with patch.object(client.order, "fetch", return_value=mock_order):
            razorpay_order = client.order.fetch(
                razorpay_order_id
            )

            print("\nRAZORPAY STATUS (MOCKED)")
            print("--------------------")
            print("Local Order ID:", order_id)
            print("Razorpay Order ID:", razorpay_order_id)
            print("Razorpay Status:", razorpay_order["status"])
            print(
                "Amount:",
                razorpay_order["amount"] / 100
            )
            print(
                "Amount Paid:",
                razorpay_order.get("amount_paid", 0) / 100
            )
            print(
                "Amount Due:",
                razorpay_order.get("amount_due", 0) / 100
            )

            assert razorpay_order["id"] == razorpay_order_id
            assert razorpay_order["amount"] == int(
                order.amount * 100
            )
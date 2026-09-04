import json
from pathlib import Path
from unittest.mock import patch

from app.db import get_session
from app.services.order_service import OrderService


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_sync_payment_service():
    data = json.loads(
        TEST_DATA_FILE.read_text(encoding="utf-8")
    )

    order_id = data["order_id"]

    with get_session() as session:
        order_service = OrderService(session)

        mock_payment_link = {
            "id": data.get("payment_link_id", "plink_mock_123"),
            "status": "paid",
            "amount": int(data["amount"] * 100),
            "amount_paid": int(data["amount"] * 100),
            "payments": [
                {
                    "payment_id": "pay_TEST_SYNC_123"
                }
            ],
        }

        with patch("app.services.payment_service.client.payment_link.fetch", return_value=mock_payment_link):
            result = order_service.sync_payment_status(
                order_id
            )

            print("\nPAYMENT SYNC (MOCKED)")
            print("--------------------")
            print("Order ID:", result["order_id"])
            print("Razorpay Order ID:", result["razorpay_order_id"])
            print("Payment Link ID:", result["payment_link_id"])
            print("Payment ID:", result["payment_id"])
            print("Razorpay Status:", result["razorpay_status"])
            print("Local Status:", result["status"])
            print("Amount:", result["amount"])
            print("Amount Paid:", result["amount_paid"])

            status_map = {
                "created": "pending_payment",
                "partially_paid": "partially_paid",
                "paid": "paid",
                "expired": "expired",
                "cancelled": "cancelled",
            }

            assert result["razorpay_status"] in status_map

            assert result["status"] == status_map[
                result["razorpay_status"]
            ]

            assert result["amount_paid"] >= 0

            if result["razorpay_status"] == "paid":
                assert result["payment_id"]
                assert result["amount_paid"] == result["amount"]
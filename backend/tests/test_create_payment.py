import json
from pathlib import Path
from unittest.mock import patch

from app.db import get_session
from app.models.order import Order
from app.services.payment_service import PaymentService


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_create_payment():

    assert TEST_DATA_FILE.exists(), (
        "test_payment_data.json not found. "
        "Run test_create_order.py first."
    )

    data = json.loads(
        TEST_DATA_FILE.read_text(encoding="utf-8")
    )

    order_id = data["order_id"]

    mock_razorpay_order_id = "order_MOCK_" + order_id[-6:]
    mock_payment_link_id = "plink_MOCK_" + order_id[-6:]
    mock_payment_url = f"https://rzp.io/i/{mock_payment_link_id}"

    with patch("app.services.payment_service.client") as mock_client:
        mock_client.order.create.return_value = {
            "id": mock_razorpay_order_id,
        }
        mock_client.payment_link.create.return_value = {
            "id": mock_payment_link_id,
            "short_url": mock_payment_url,
        }

        with get_session() as session:

            order = session.get(Order, order_id)

            assert order is not None

            payment_service = PaymentService(session)

            result = payment_service.create_payment(
                order=order,
                product_name="Air Runner Black",
            )

            print("\nRAZORPAY PAYMENT (MOCKED)")
            print("--------------------")
            print("Local Order ID:", result["order_id"])
            print("Razorpay Order ID:", result["razorpay_order_id"])
            print("Payment Link ID:", result["payment_link_id"])
            print("Payment URL:", result["payment_url"])
            print("Amount:", result["amount"])
            print("Currency:", result["currency"])
            print("Status:", result["status"])

            data.update({
                "razorpay_order_id": result["razorpay_order_id"],
                "payment_link_id": result["payment_link_id"],
                "payment_url": result["payment_url"],
            })

            TEST_DATA_FILE.write_text(
                json.dumps(data, indent=4),
                encoding="utf-8"
            )

            assert result["razorpay_order_id"] == mock_razorpay_order_id
            assert result["payment_link_id"] == mock_payment_link_id
            assert result["payment_url"] == mock_payment_url
            assert result["amount"] == order.amount
            assert result["currency"] == order.currency
            assert result["status"] == "pending_payment"
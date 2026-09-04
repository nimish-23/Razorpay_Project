import json
from pathlib import Path
from unittest.mock import patch

from app.razorpay_client import client


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_get_payment_link_status():

    data = json.loads(
        TEST_DATA_FILE.read_text(encoding="utf-8")
    )

    payment_link_id = data["payment_link_id"]

    mock_payment_link = {
        "id": payment_link_id,
        "status": "created",
        "amount": int(data["amount"] * 100),
        "amount_paid": 0,
        "payments": [],
    }

    with patch.object(client.payment_link, "fetch", return_value=mock_payment_link):
        payment_link = client.payment_link.fetch(
            payment_link_id
        )

        print("\nPAYMENT LINK STATUS (MOCKED)")
        print("--------------------")
        print("Payment Link ID:", payment_link["id"])
        print("Status:", payment_link["status"])
        print(
            "Amount:",
            payment_link["amount"] / 100
        )
        print(
            "Amount Paid:",
            payment_link.get("amount_paid", 0) / 100
        )
        print("Payments:", payment_link.get("payments"))

        assert payment_link["id"] == payment_link_id
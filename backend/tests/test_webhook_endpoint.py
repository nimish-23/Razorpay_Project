import os
import hmac
import json
import uuid
import hashlib

from fastapi.testclient import TestClient

from app.main import app


def test_razorpay_webhook_endpoint():

    webhook_event = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_TXgIuRlVW8cDL9",
                    "amount": 439800,
                    "amount_paid": 439800,
                    "status": "paid",
                    "payments": [
                        {
                            "payment_id": "pay_ENDPOINT_TEST_123"
                        }
                    ],
                }
            }
        },
    }

    body = json.dumps(webhook_event).encode("utf-8")

    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    assert secret is not None

    signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    event_id = f"evt_ENDPOINT_TEST_{uuid.uuid4().hex}"

    client = TestClient(app)

    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id,
            "Content-Type": "application/json",
        },
    )

    print("\nWEBHOOK ENDPOINT TEST")
    print("-------------------------")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 200

    result = response.json()

    assert result["success"] is True
    assert result["processed"] is True
    assert result["event"] == "payment_link.paid"
    assert result["order_id"] == "ORD-BBEEB736DE74"
    assert result["status"] == "paid"
    assert result["payment_id"] == "pay_ENDPOINT_TEST_123"
    assert result["amount_paid"] == 4398.0

    duplicate_response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id,
            "Content-Type": "application/json",
        },
    )

    print("\nDUPLICATE WEBHOOK TEST")
    print("-------------------------")
    print("Status Code:", duplicate_response.status_code)
    print("Response:", duplicate_response.json())

    assert duplicate_response.status_code == 200

    duplicate_result = duplicate_response.json()

    assert duplicate_result["success"] is True
    assert duplicate_result["processed"] is False
    assert duplicate_result["duplicate"] is True
    assert duplicate_result["event_id"] == event_id
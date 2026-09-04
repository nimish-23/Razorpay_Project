from unittest.mock import patch

from app.db import get_session
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


def test_payment_service_create_payment():
    mock_order_id = "order_mock_12345"
    mock_payment_link_id = "plink_mock_12345"
    mock_payment_url = "https://rzp.io/i/mock123"

    with patch("app.services.payment_service.client") as mock_client:
        mock_client.order.create.return_value = {
            "id": mock_order_id,
        }
        mock_client.payment_link.create.return_value = {
            "id": mock_payment_link_id,
            "short_url": mock_payment_url,
        }

        with get_session() as session:
            order_service = OrderService(session)
            order = order_service.create_order(
                item_id="shoe_001",
                qty=2,
                selected_attributes={
                    "size": 9
                }
            )

            assert order.order_id is not None
            assert order.status == "pending_payment"

            payment_service = PaymentService(session)
            result = payment_service.create_payment(
                order=order,
                product_name="Air Runner Black"
            )

            # Verify returned response
            assert result["order_id"] == order.order_id
            assert result["razorpay_order_id"] == mock_order_id
            assert result["payment_link_id"] == mock_payment_link_id
            assert result["payment_url"] == mock_payment_url
            assert result["amount"] == 4398.0
            assert result["currency"] == "INR"
            assert result["status"] == "pending_payment"

            # Verify stored order attributes in session
            session.refresh(order)
            assert order.razorpay_order_id == mock_order_id
            assert order.razorpay_payment_link_id == mock_payment_link_id
            assert order.status == "pending_payment"
            assert order.amount == 4398.0
            assert order.currency == "INR"

            # Verify client was called with expected mock
            mock_client.order.create.assert_called_once()
            mock_client.payment_link.create.assert_called_once()
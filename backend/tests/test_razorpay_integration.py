import pytest
from app.db import get_session, create_db_and_tables
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.catalog_service import CatalogService

@pytest.mark.integration
def test_real_razorpay_payment():

    # Create database tables
    create_db_and_tables()

    with get_session() as session:

        # Seed catalog
        catalog_service = CatalogService(session)

        catalog_service.seed_catalog(
            "data/catalog.json"
        )

        # Create local order
        order_service = OrderService(session)

        order = order_service.create_order(
            item_id="shoe_001",
            qty=2,
            selected_attributes={
                "size": 9
            },
        )

        print("\nLOCAL ORDER")
        print("--------------------")
        print("Order ID:", order.order_id)
        print("Product:", order.item_id)
        print("Quantity:", order.qty)
        print("Attributes:", order.selected_attributes)
        print("Amount:", order.amount)
        print("Status:", order.status)

        # Create real Razorpay payment
        payment_service = PaymentService(session)

        result = payment_service.create_payment(
            order=order,
            product_name="Air Runner Black",
        )

        print("\nRAZORPAY PAYMENT")
        print("--------------------")
        print("Razorpay Order ID:", result["razorpay_order_id"])
        print("Payment Link ID:", result["payment_link_id"])
        print("Payment URL:", result["payment_url"])
        print("Amount:", result["amount"])
        print("Currency:", result["currency"])
        print("Status:", result["status"])

        assert result["razorpay_order_id"]
        assert result["payment_link_id"]
        assert result["payment_url"]
import json
from pathlib import Path

from app.db import get_session, create_db_and_tables
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService


TEST_DATA_FILE = Path("tests/test_payment_data.json")


def test_create_order():

    create_db_and_tables()

    with get_session() as session:

        catalog_service = CatalogService(session)

        catalog_service.seed_catalog(
            "data/catalog.json"
        )

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
        print("Currency:", order.currency)
        print("Status:", order.status)

        data = {
            "order_id": order.order_id,
            "amount": order.amount,
            "currency": order.currency,
        }

        TEST_DATA_FILE.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8"
        )

        assert order.order_id
        assert order.status == "pending_payment"
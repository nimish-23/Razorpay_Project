from typing import Optional, Any

from mcp.server.mcpserver import MCPServer
from uuid import uuid4
from app.db import get_session
from app.models.order import Order
from app.models.product import Product
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


server = MCPServer(
    name="Rohan's Merchant",
    version="1.0.0"
)

SESSION_ID = f"sess_{uuid4().hex[:12].upper()}"

@server.tool(
    name="search_catalog",
    description=(
        "Search products in the merchant catalog. "
        "You can filter by text, category, maximum price, "
        "or any product attributes."
    )
)
def search_catalog(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> dict:

    with get_session() as session:

        catalog_service = CatalogService(
            session,
            SESSION_ID
        )

        products = catalog_service.search_catalog(
            query=query,
            max_price=max_price,
            category=category,
            attributes=attributes,
        )

        return {
            "count": len(products),
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "currency": product.currency,
                    "stock": product.stock,
                    "attributes": product.attributes,
                }
                for product in products
            ],
        }


@server.tool(
    name="create_order",
    description=(
        "Create an order for a product. "
        "Quantity and optional product attributes can be provided."
    )
)
def create_order(
    item_id: str,
    qty: int = 1,
    selected_attributes: Optional[dict[str, Any]] = None,
) -> dict:

    try:

        with get_session() as session:

            order_service = OrderService(
            session,
            SESSION_ID
        )

            order = order_service.create_order(
                item_id=item_id,
                qty=qty,
                selected_attributes=selected_attributes,
            )

            return {
                "success": True,
                "order": {
                    "order_id": order.order_id,
                    "item_id": order.item_id,
                    "qty": order.qty,
                    "selected_attributes": order.selected_attributes,
                    "amount": order.amount,
                    "currency": order.currency,
                    "status": order.status,
                },
            }

    except ValueError as e:

        return {
            "success": False,
            "error": str(e),
        }


@server.tool(
    name="get_order_status",
    description=(
        "Get the current payment status of an order. "
        "Use the local order_id returned by create_order."
    )
)
def get_order_status(order_id: str) -> dict:
    try:
        with get_session() as session:
            order_service = OrderService(session)

            result = order_service.sync_payment_status(
                order_id=order_id
            )

            return {
                "success": True,
                "order": result,
            }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


@server.tool(
    name="create_payment",
    description=(
        "Create a Razorpay payment link for an existing order. "
        "Use the local order_id returned by create_order. "
        "Returns a payment URL that can be given to the customer."
    )
)
def create_payment(order_id: str) -> dict:

    try:
        with get_session() as session:

            order = session.get(
                Order,
                order_id
            )

            if order is None:
                return {
                    "success": False,
                    "error": f"Order '{order_id}' was not found.",
                }

            product = session.get(
                Product,
                order.item_id
            )

            if product is None:
                return {
                    "success": False,
                    "error": (
                        f"Product '{order.item_id}' "
                        "was not found."
                    ),
                }

            payment_service = PaymentService(session)

            result = payment_service.create_payment(
                order=order,
                product_name=product.name,
            )

            return {
                "success": True,
                "payment": result,
            }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }

if __name__ == "__main__":
    server.run("stdio")
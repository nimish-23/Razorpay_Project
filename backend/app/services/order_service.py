from typing import Any, Optional
from uuid import uuid4

from sqlmodel import Session

from app.models.order import Order
from app.models.product import Product
from app.services.audit_service import AuditService
from app.services.payment_service import PaymentService

class OrderService:

    def __init__(
        self,
        session: Session,
        session_id: str = ""
    ):
        self.session = session
        self.session_id = session_id
        self.audit_service = AuditService(
            session,
            session_id
        )

    def create_order(
        self,
        item_id: str,
        qty: int = 1,
        selected_attributes: Optional[dict[str, Any]] = None,
    ) -> Order:

        # 1. Find product
        product = self.session.get(Product, item_id)

        if product is None:
            raise ValueError(
                f"Product '{item_id}' was not found."
            )

        # 2. Validate quantity
        if qty <= 0:
            raise ValueError(
                "Quantity must be greater than 0."
            )

        # 3. Check stock
        if product.stock < qty:
            raise ValueError(
                f"Insufficient stock for '{product.name}'. "
                f"Requested: {qty}, available: {product.stock}."
            )

        # 4. Optional attributes
        selected_attributes = selected_attributes or {}

        # 5. Validate supplied attributes
        self._validate_attributes(
            product,
            selected_attributes
        )

        # 6. Calculate amount
        amount = product.price * qty

        # 7. Create order
        order = Order(
            order_id=f"ORD-{uuid4().hex[:12].upper()}",
            session_id=self.session_id,
            item_id=product.id,
            qty=qty,
            selected_attributes=selected_attributes,
            amount=amount,
            currency=product.currency,
            status="pending_payment",
        )
        
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        self.audit_service.log_order_created(order)

        return order

    def _validate_attributes(
        self,
        product: Product,
        selected_attributes: dict[str, Any],
    ):

        product_attributes = product.attributes or {}

        for attribute_name, requested_value in selected_attributes.items():

            # Attribute doesn't exist
            if attribute_name not in product_attributes:
                raise ValueError(
                    f"Attribute '{attribute_name}' "
                    f"is not available for '{product.name}'."
                )

            available_value = product_attributes[attribute_name]

            # Attribute contains multiple allowed values
            if isinstance(available_value, list):

                if requested_value not in available_value:
                    raise ValueError(
                        f"Invalid value '{requested_value}' "
                        f"for attribute '{attribute_name}'. "
                        f"Available values: {available_value}"
                    )

            # Attribute has a single value
            else:

                if requested_value != available_value:
                    raise ValueError(
                        f"Invalid value '{requested_value}' "
                        f"for attribute '{attribute_name}'."
                    )

    def sync_payment_status(self, order_id: str) -> dict:
        order = self.session.get(Order, order_id)

        if order is None:
            raise ValueError(
                f"Order '{order_id}' was not found."
            )

        if self.session_id and order.session_id != self.session_id:
            raise ValueError(
                f"Order '{order_id}' was not found."
            )

        payment_service = PaymentService(self.session)

        return payment_service.get_payment_status(order)
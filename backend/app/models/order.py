from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    order_id: str = Field(primary_key=True)

    item_id: str = Field(index=True)

    size: int
    qty: int = Field(default=1)

    amount: float
    currency: str = "INR"

    status: str = Field(
        default="pending_payment",
        index=True
    )

    razorpay_order_id: Optional[str] = Field(
        default=None,
        index=True
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
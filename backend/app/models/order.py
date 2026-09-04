from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    order_id: str = Field(primary_key=True)

    session_id: str = Field(default="", index=True)

    item_id: str = Field(index=True)

    qty: int = Field(default=1)

    selected_attributes: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )

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

    razorpay_payment_link_id: Optional[str] = Field(
        default=None,
        index=True
    )

    razorpay_payment_id: Optional[str] = Field(
        default=None,
        index=True
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
from typing import Any

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: str = Field(primary_key=True)

    name: str

    category: str

    price: float

    currency: str = "INR"

    stock: int = 0

    attributes: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
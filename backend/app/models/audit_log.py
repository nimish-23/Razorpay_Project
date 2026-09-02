from datetime import datetime
from typing import Any

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(
        default=None,
        primary_key=True
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        index=True
    )

    tool_name: str = Field(index=True)

    input: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )

    decision: str

    reason: str

    result: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
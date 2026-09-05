from datetime import datetime

from sqlmodel import Field, SQLModel


class AgentAuthorization(SQLModel, table=True):
    __tablename__ = "agent_authorizations"

    agent_id: str = Field(primary_key=True)
    authorization_token_hash: str = Field(index=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True, index=True)

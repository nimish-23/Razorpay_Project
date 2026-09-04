from sqlmodel import Field, SQLModel


class AgentPolicy(SQLModel, table=True):
    __tablename__ = "agent_policies"

    session_id: str = Field(primary_key=True)
    agent_id: str = Field(index=True)
    maximum_transaction_amount: float = 5000.0
    approval_threshold: float = 3000.0
    payment_verification_required: bool = True

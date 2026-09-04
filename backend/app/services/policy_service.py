from typing import Optional

from sqlmodel import Session, select

from app.models.agent_authorization import AgentAuthorization
from app.models.agent_policy import AgentPolicy


DEFAULT_MAXIMUM_TRANSACTION_AMOUNT = 5000.0
DEFAULT_APPROVAL_THRESHOLD = 3000.0
DEFAULT_PAYMENT_VERIFICATION_REQUIRED = True


class PolicyService:

    def __init__(self, session: Session):
        self.session = session

    def get(self, session_id: str) -> Optional[AgentPolicy]:
        return self.session.get(AgentPolicy, session_id)

    def get_or_create(
        self,
        authorization: AgentAuthorization,
    ) -> AgentPolicy:
        policy = self.get(authorization.session_id)
        if policy:
            return policy

        policy = AgentPolicy(
            session_id=authorization.session_id,
            agent_id=authorization.agent_id,
            maximum_transaction_amount=DEFAULT_MAXIMUM_TRANSACTION_AMOUNT,
            approval_threshold=DEFAULT_APPROVAL_THRESHOLD,
            payment_verification_required=DEFAULT_PAYMENT_VERIFICATION_REQUIRED,
        )
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def update(
        self,
        authorization: AgentAuthorization,
        maximum_transaction_amount: float,
        approval_threshold: float,
        payment_verification_required: bool,
    ) -> AgentPolicy:
        self._validate_values(
            maximum_transaction_amount,
            approval_threshold,
        )
        policy = self.get_or_create(authorization)
        policy.maximum_transaction_amount = maximum_transaction_amount
        policy.approval_threshold = approval_threshold
        policy.payment_verification_required = payment_verification_required
        policy.agent_id = authorization.agent_id
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def evaluate(
        self,
        policy: AgentPolicy,
        amount: float,
    ) -> dict[str, object]:
        if amount > policy.maximum_transaction_amount:
            return {
                "allowed": False,
                "approval_required": False,
                "reason": (
                    "Transaction amount exceeds AgentPay maximum transaction limit."
                ),
            }

        if amount > policy.approval_threshold:
            return {
                "allowed": True,
                "approval_required": True,
                "reason": (
                    "Transaction is within the maximum limit but requires user approval."
                ),
            }

        return {
            "allowed": True,
            "approval_required": False,
            "reason": "Transaction is within the configured policy.",
        }

    @staticmethod
    def _validate_values(
        maximum_transaction_amount: float,
        approval_threshold: float,
    ) -> None:
        if maximum_transaction_amount <= 0:
            raise ValueError(
                "maximum_transaction_amount must be positive."
            )
        if approval_threshold <= 0:
            raise ValueError("approval_threshold must be positive.")
        if approval_threshold > maximum_transaction_amount:
            raise ValueError(
                "approval_threshold must be less than or equal to "
                "maximum_transaction_amount."
            )

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.authorization_service import AuthorizationService
from app.services.policy_service import PolicyService

router = APIRouter()


def _get_session():
    from app.main import get_session

    return get_session()


class PolicyRequest(BaseModel):
    maximum_transaction_amount: float = Field(gt=0)
    approval_threshold: float = Field(gt=0)
    payment_verification_required: bool


def policy_response(policy):
    return {
        "session_id": policy.session_id,
        "agent_id": policy.agent_id,
        "maximum_transaction_amount": policy.maximum_transaction_amount,
        "approval_threshold": policy.approval_threshold,
        "payment_verification_required": policy.payment_verification_required,
    }


def _active_session_id():
    from app.main import get_active_session_id

    return get_active_session_id()


def _active_authorization(session):
    session_id = _active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Not authorized: no active MCP session.",
        )
    authorization = AuthorizationService(session).get_active(session_id)
    if not authorization:
        raise HTTPException(
            status_code=404,
            detail="Not authorized for the current session.",
        )
    return authorization


@router.get("/policy/active")
def get_active_policy():
    with _get_session() as session:
        authorization = _active_authorization(session)
        policy = PolicyService(session).get_or_create(authorization)
        return policy_response(policy)


@router.post("/policy")
def update_policy(policy_request: PolicyRequest):
    with _get_session() as session:
        authorization = _active_authorization(session)
        try:
            policy = PolicyService(session).update(
                authorization=authorization,
                maximum_transaction_amount=policy_request.maximum_transaction_amount,
                approval_threshold=policy_request.approval_threshold,
                payment_verification_required=policy_request.payment_verification_required,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return policy_response(policy)

from contextlib import contextmanager
from unittest.mock import patch

from sqlmodel import Session, SQLModel, create_engine, select

from app.mcp import server as mcp_server
from app.models.agent_authorization import AgentAuthorization
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.product import Product
from app.services.authorization_service import AuthorizationService
from app.services.policy_service import PolicyService


def test_mcp_policy_blocks_and_requires_approval_before_order_creation():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session_id = "sess_mcp_policy_order"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(session_id)
        PolicyService(session).update(authorization, 5000, 3000, True)
        session.add_all([
            Product(
                id="shoe_policy_approval",
                name="Approval Runner",
                category="shoes",
                price=3500,
                currency="INR",
                stock=5,
                attributes={},
            ),
            Product(
                id="shoe_policy_blocked",
                name="Blocked Runner",
                category="shoes",
                price=7000,
                currency="INR",
                stock=5,
                attributes={},
            ),
        ])
        session.commit()

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ):
        approval = mcp_server.create_order(
            item_id="shoe_policy_approval",
            authorization_token=token,
        )
        assert approval == {
            "allowed": True,
            "approval_required": True,
            "error": "approval_required",
            "message": "User approval is required before this transaction can proceed.",
            "reason": "Transaction is within the maximum limit but requires user approval.",
        }

        blocked = mcp_server.create_order(
            item_id="shoe_policy_blocked",
            authorization_token=token,
        )
        assert blocked["allowed"] is False
        assert blocked["error"] == "policy_violation"

    with Session(engine) as session:
        assert session.exec(select(Order)).first() is None
        events = session.exec(
            select(AuditLog).where(
                AuditLog.tool_name.in_([
                    "policy_approval_required",
                    "policy_check_failed",
                ])
            )
        ).all()
        assert len(events) == 2
        assert all(token not in str(event.input) for event in events)
        assert all(token not in str(event.result) for event in events)


def test_mcp_policy_blocks_payment_before_razorpay():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session_id = "sess_mcp_policy_payment"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(session_id)
        PolicyService(session).update(authorization, 5000, 3000, True)
        session.add(Order(
            order_id="ORD-POLICY-BLOCKED",
            session_id=session_id,
            item_id="missing-product",
            qty=1,
            amount=7000,
            currency="INR",
            status="pending_payment",
        ))
        session.commit()

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ), patch("app.services.payment_service.client") as mock_client:
        result = mcp_server.create_payment(
            "ORD-POLICY-BLOCKED",
            authorization_token=token,
        )

        assert result["allowed"] is False
        assert result["error"] == "policy_violation"
        mock_client.order.create.assert_not_called()
        mock_client.payment_link.create.assert_not_called()

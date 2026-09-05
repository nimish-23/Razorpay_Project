from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.mcp import server as mcp_server
from app.models.agent_authorization import AgentAuthorization
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.product import Product
from app.services.authorization_service import AuthorizationService


def create_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_approve_transaction_approves_current_order_without_razorpay():
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    session_id = "sess_approve_transaction"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(session_id)
        session.add(Order(
            order_id="ORD-APPROVE-MCP",
            session_id=session_id,
            item_id="shoe-approve",
            amount=4398,
            currency="INR",
            status="approval_required",
        ))
        session.add(Product(
            id="shoe-approve",
            name="Approval Runner",
            category="shoes",
            price=2199,
            stock=2,
            attributes={},
        ))
        session.commit()

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ), patch("app.services.payment_service.client") as mock_client:
        result = mcp_server.approve_transaction("ORD-APPROVE-MCP")

        assert result == {
            "success": True,
            "approved": True,
            "order_id": "ORD-APPROVE-MCP",
            "status": "approved",
            "message": (
                "Transaction approved. The order is now approved and "
                "payment can be initiated."
            ),
        }
        mock_client.order.create.assert_not_called()
        mock_client.payment_link.create.assert_not_called()

        mock_client.order.create.return_value = {"id": "order_approve_001"}
        mock_client.payment_link.create.return_value = {
            "id": "plink_approve_001",
            "short_url": "https://rzp.io/i/plink_approve_001",
        }
        payment_result = mcp_server.create_payment("ORD-APPROVE-MCP")
        assert payment_result["success"] is True
        assert payment_result["payment"]["payment_link_id"] == "plink_approve_001"
        mock_client.payment_link.create.assert_called_once()

        with Session(engine) as session:
            order = session.get(Order, "ORD-APPROVE-MCP")
            assert order.status == "approved"
            assert order.razorpay_payment_link_id == "plink_approve_001"
            approval_event = session.exec(
                select(AuditLog).where(
                    AuditLog.tool_name == "transaction_approved"
                )
            ).first()
            assert approval_event is not None
            assert token not in str(approval_event.input)
            assert token not in str(approval_event.result)


def test_approve_transaction_rejects_unauthorized_and_invalid_orders():
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    session_id = "sess_approve_rejections"

    with Session(engine) as session:
        AuthorizationService(session).generate(session_id)
        session.add_all([
            Order(
                order_id="ORD-APPROVED-MCP",
                session_id=session_id,
                item_id="item",
                amount=4000,
                status="approved",
            ),
            Order(
                order_id="ORD-PAID-MCP",
                session_id=session_id,
                item_id="item",
                amount=4000,
                status="paid",
            ),
            Order(
                order_id="ORD-OTHER-MCP",
                session_id="other-session",
                item_id="item",
                amount=4000,
                status="approval_required",
            ),
        ])
        session.commit()

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", "sess_no_approval_auth"
    ):
        missing_auth = mcp_server.approve_transaction("ORD-APPROVED-MCP")
        assert missing_auth["authorized"] is False

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ):

        invalid_order = mcp_server.approve_transaction("ORD-NOT-FOUND")
        assert invalid_order["error"] == "order_not_found"

        already_approved = mcp_server.approve_transaction("ORD-APPROVED-MCP")
        assert already_approved["error"] == "approval_required"

        already_paid = mcp_server.approve_transaction("ORD-PAID-MCP")
        assert already_paid["error"] == "approval_required"

        other_session = mcp_server.approve_transaction("ORD-OTHER-MCP")
        assert other_session["error"] == "order_not_found"

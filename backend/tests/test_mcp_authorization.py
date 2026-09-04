from contextlib import contextmanager
from unittest.mock import patch

from sqlmodel import Session, SQLModel, create_engine, select

from app.mcp import server as mcp_server
from app.models.agent_authorization import AgentAuthorization
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.product import Product
from app.services.authorization_service import AuthorizationService


def create_test_engine():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def seed_product(engine):
    with Session(engine) as session:
        session.add(Product(
            id="shoe_auth_001",
            name="Auth Runner Black",
            category="shoes",
            price=2199,
            currency="INR",
            stock=5,
            attributes={"color": "black", "size": [9]},
        ))
        session.commit()


def test_mcp_transaction_authorization_and_read_only_tools():
    engine = create_test_engine()
    seed_product(engine)
    session_id = "sess_mcp_authorized"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(session_id)

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ):
        unauthorized = mcp_server.create_order(
            item_id="shoe_auth_001",
            selected_attributes={"size": 9},
        )
        assert unauthorized["authorized"] is False
        assert unauthorized["error"] == "agent_not_authorized"

        with Session(engine) as session:
            assert session.exec(select(Order)).first() is None
            failure = session.exec(
                select(AuditLog).where(
                    AuditLog.tool_name == "agent_authorization_failed"
                )
            ).first()
            assert failure is not None
            assert token not in str(failure.input)
            assert token not in str(failure.result)

        authorized = mcp_server.create_order(
            item_id="shoe_auth_001",
            selected_attributes={"size": 9},
            authorization_token=token,
        )
        assert authorized["success"] is True
        order_id = authorized["order"]["order_id"]

        discovery = mcp_server.search_catalog(query="black shoes")
        assert discovery["count"] == 1

        status = mcp_server.get_order_status("ORD-NOT-FOUND")
        assert status["success"] is False

        unauthorized_payment = mcp_server.create_payment(order_id)
        assert unauthorized_payment["authorized"] is False


def test_mcp_rejects_invalid_inactive_and_old_session_tokens():
    engine = create_test_engine()
    seed_product(engine)
    original_session = "sess_mcp_original"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(original_session)
        authorization.active = False
        session.add(authorization)
        session.commit()
        inactive_result = AuthorizationService(session).validate(token, original_session)
        assert inactive_result[1] == "inactive_token"
        assert AuthorizationService(session).validate("ap_demo_invalid", original_session)[1] == "invalid_token"

        authorization.active = True
        session.add(authorization)
        session.commit()
        assert AuthorizationService(session).validate(token, "sess_mcp_new")[1] == "wrong_session"

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", "sess_mcp_new"
    ):
        old_session = mcp_server.create_order(
            item_id="shoe_auth_001",
            authorization_token=token,
        )
        assert old_session["authorized"] is False
        assert old_session["reason"] == "wrong_session"


def test_authorized_mcp_create_payment_preserves_existing_flow():
    engine = create_test_engine()
    seed_product(engine)
    session_id = "sess_mcp_payment"

    with Session(engine) as session:
        _, token = AuthorizationService(session).generate(session_id)

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ), patch("app.services.payment_service.client") as mock_client:
        mock_client.order.create.return_value = {"id": "order_auth_001"}
        mock_client.payment_link.create.return_value = {
            "id": "plink_auth_001",
            "short_url": "https://rzp.io/i/plink_auth_001",
        }

        order_result = mcp_server.create_order(
            item_id="shoe_auth_001",
            authorization_token=token,
        )
        order_id = order_result["order"]["order_id"]

        payment_result = mcp_server.create_payment(
            order_id,
            authorization_token=token,
        )
        assert payment_result["success"] is True
        assert payment_result["payment"]["payment_link_id"] == "plink_auth_001"
        mock_client.payment_link.create.assert_called_once()

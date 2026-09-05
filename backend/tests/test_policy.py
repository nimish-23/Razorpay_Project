from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.main import app
from app.models.audit_log import AuditLog
from app.models.agent_authorization import AgentAuthorization
from app.models.order import Order
from app.models.product import Product
from app.services.authorization_service import AuthorizationService
from app.services.policy_service import PolicyService


def test_default_policy_and_amount_boundaries():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        authorization = AgentAuthorization(
            agent_id="agent_policy_default",
            authorization_token_hash="hash",
            session_id="sess_policy_default",
        )
        session.add(authorization)
        session.commit()

        service = PolicyService(session)
        policy = service.get_or_create(authorization)
        assert policy.maximum_transaction_amount == 5000
        assert policy.approval_threshold == 3000
        assert policy.payment_verification_required is True
        assert service.evaluate(policy, 3000) == {
            "allowed": True,
            "approval_required": False,
            "reason": "Transaction is within the configured policy.",
        }
        assert service.evaluate(policy, 3001)["approval_required"] is True
        assert service.evaluate(policy, 5000)["allowed"] is True
        assert service.evaluate(policy, 5001) == {
            "allowed": False,
            "approval_required": False,
            "reason": "Transaction amount exceeds AgentPay maximum transaction limit.",
        }


def test_policy_update_and_validation():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        authorization = AgentAuthorization(
            agent_id="agent_policy_update",
            authorization_token_hash="hash",
            session_id="sess_policy_update",
        )
        session.add(authorization)
        session.commit()

        service = PolicyService(session)
        updated = service.update(authorization, 9000, 4500, False)
        assert updated.maximum_transaction_amount == 9000
        assert updated.approval_threshold == 4500
        assert updated.payment_verification_required is False
        assert service.get(authorization.session_id).agent_id == authorization.agent_id

        try:
            service.update(authorization, 3000, 3001, True)
            assert False
        except ValueError as error:
            assert "less than or equal" in str(error)

        try:
            service.update(authorization, 0, 0, True)
            assert False
        except ValueError as error:
            assert "positive" in str(error)


def test_policy_endpoints_are_session_scoped(monkeypatch, tmp_path: Path):
    session_id = f"sess_policy_api_{uuid4().hex}"
    other_session_id = f"sess_policy_other_{uuid4().hex}"
    active_session_path = tmp_path / "active_session.txt"
    active_session_path.write_text(session_id, encoding="utf-8")
    monkeypatch.setattr("app.main.ACTIVE_SESSION_PATH", active_session_path)

    with TestClient(app) as client:
        authorization = client.post("/authorization/generate")
        assert authorization.status_code == 200

        default = client.get("/policy/active")
        assert default.status_code == 200
        assert default.json()["maximum_transaction_amount"] == 5000
        assert default.json()["approval_threshold"] == 3000
        assert default.json()["payment_verification_required"] is True

        updated = client.post("/policy", json={
            "maximum_transaction_amount": 8000,
            "approval_threshold": 2500,
            "payment_verification_required": False,
        })
        assert updated.status_code == 200
        assert updated.json()["maximum_transaction_amount"] == 8000
        assert updated.json()["payment_verification_required"] is False

        invalid = client.post("/policy", json={
            "maximum_transaction_amount": 1000,
            "approval_threshold": 1001,
            "payment_verification_required": True,
        })
        assert invalid.status_code == 422

        active_session_path.write_text(other_session_id, encoding="utf-8")
        missing = client.get("/policy/active")
        assert missing.status_code == 404


def test_approval_endpoint_approves_only_waiting_current_session_order(
    monkeypatch,
    tmp_path: Path,
):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session_id = f"sess_approval_api_{uuid4().hex}"
    active_session_path = tmp_path / "active_session.txt"
    active_session_path.write_text(session_id, encoding="utf-8")
    monkeypatch.setattr("app.main.ACTIVE_SESSION_PATH", active_session_path)

    with Session(engine) as session:
        authorization = AgentAuthorization(
            agent_id="agent_approval_api",
            authorization_token_hash="hash",
            session_id=session_id,
        )
        session.add(Order(
            order_id="ORD-APPROVAL-API",
            session_id=session_id,
            item_id="approval-product",
            amount=4000,
            status="approval_required",
        ))
        session.add(Product(
            id="approval-product",
            name="Approval Product",
            category="shoes",
            price=4000,
            stock=1,
            attributes={},
        ))
        session.add(Order(
            order_id="ORD-PAID-API",
            session_id=session_id,
            item_id="approval-product",
            amount=4000,
            status="paid",
        ))
        session.add(Order(
            order_id="ORD-OTHER-API",
            session_id=f"other_{session_id}",
            item_id="approval-product",
            amount=4000,
            status="approval_required",
        ))
        session.add(authorization)
        session.commit()

    @contextmanager
    def isolated_session():
        with Session(engine) as session:
            yield session

    with patch("app.main.get_session", isolated_session):
        with TestClient(app) as client:
            approved = client.post("/orders/ORD-APPROVAL-API/approve")
            assert approved.status_code == 200
            assert approved.json()["status"] == "approved"

            already_approved = client.post("/orders/ORD-APPROVAL-API/approve")
            assert already_approved.status_code == 409

            already_paid = client.post("/orders/ORD-PAID-API/approve")
            assert already_paid.status_code == 409

            other_session = client.post("/orders/ORD-OTHER-API/approve")
            assert other_session.status_code == 404

    with Session(engine) as session:
        order = session.get(Order, "ORD-APPROVAL-API")
        assert order.status == "approved"
        assert session.exec(
            select(AuditLog).where(
                AuditLog.tool_name == "transaction_approved"
            )
        ).first() is not None

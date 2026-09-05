from contextlib import contextmanager
from unittest.mock import patch

from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from app.mcp import server as mcp_server
from app.models.agent_authorization import AgentAuthorization
from app.models.audit_log import AuditLog
from app.services.authorization_service import AuthorizationService


def create_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_get_agent_authorization_returns_current_session_identity_without_secrets():
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    session_id = "sess_authorization_lookup"

    with Session(engine) as session:
        authorization, token = AuthorizationService(session).generate(session_id)
        token_hash = authorization.authorization_token_hash

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ):
        result = mcp_server.get_agent_authorization()

    assert result == {
        "authorized": True,
        "agent_id": authorization.agent_id,
        "session_id": session_id,
        "status": "authorized",
    }
    assert token not in str(result)
    assert token_hash not in str(result)

    with Session(engine) as session:
        assert session.exec(select(AuditLog)).first() is None


def test_get_agent_authorization_returns_not_authorized_without_creating_state():
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    session_id = "sess_authorization_missing"

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", session_id
    ):
        result = mcp_server.get_agent_authorization()

    assert result == {
        "authorized": False,
        "agent_id": None,
        "session_id": session_id,
        "status": "not_authorized",
        "message": "No active AgentPay authorization exists for this MCP session.",
    }

    with Session(engine) as session:
        assert session.exec(select(AgentAuthorization)).first() is None
        assert session.exec(select(AuditLog)).first() is None


def test_get_agent_authorization_rejects_authorization_from_another_session():
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    original_session = "sess_authorization_original"
    current_session = "sess_authorization_current"

    with Session(engine) as session:
        AuthorizationService(session).generate(original_session)

    @contextmanager
    def session_context():
        with Session(engine) as session:
            yield session

    with patch.object(mcp_server, "get_session", session_context), patch.object(
        mcp_server, "SESSION_ID", current_session
    ):
        result = mcp_server.get_agent_authorization()

    assert result["authorized"] is False
    assert result["agent_id"] is None
    assert result["session_id"] == current_session
    assert result["status"] == "not_authorized"

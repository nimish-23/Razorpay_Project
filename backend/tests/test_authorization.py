from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.main import app
from app.models.agent_authorization import AgentAuthorization
from app.services.authorization_service import AuthorizationService


def test_authorization_generation_is_secure_and_session_scoped():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        service = AuthorizationService(session)
        authorization, token = service.generate("sess_authorization_a")

        assert authorization.agent_id.startswith("agent_")
        assert token.startswith("ap_demo_")
        assert len(token) > len("ap_demo_")
        assert authorization.authorization_token_hash != token
        assert authorization.session_id == "sess_authorization_a"
        assert authorization.active is True

        other_authorization, other_token = service.generate("sess_authorization_b")
        assert other_authorization.agent_id != authorization.agent_id
        assert other_token != token


def test_authorization_service_rejects_second_active_authorization():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        service = AuthorizationService(session)
        service.generate("sess_duplicate")

        try:
            service.generate("sess_duplicate")
            assert False
        except ValueError as error:
            assert str(error) == (
                "An active agent authorization already exists for this session."
            )


def test_authorization_endpoints_use_active_session(monkeypatch, tmp_path: Path):
    session_id = f"sess_endpoint_{uuid4().hex}"
    active_session_path = tmp_path / "active_session.txt"
    active_session_path.write_text(session_id, encoding="utf-8")
    monkeypatch.setattr("app.main.ACTIVE_SESSION_PATH", active_session_path)

    with TestClient(app) as client:
        generated = client.post("/authorization/generate")
        assert generated.status_code == 200
        payload = generated.json()
        assert payload["agent_id"].startswith("agent_")
        assert payload["authorization_token"].startswith("ap_demo_")
        assert payload["status"] == "authorized"
        assert payload["session_id"] == session_id

        active = client.get("/authorization/active")
        assert active.status_code == 200
        assert active.json() == {
            "agent_id": payload["agent_id"],
            "status": "authorized",
            "session_id": session_id,
        }

        duplicate = client.post("/authorization/generate")
        assert duplicate.status_code == 409
        assert "already exists" in duplicate.json()["detail"]


def test_active_authorization_is_not_found_for_unrecognized_session(
    monkeypatch,
    tmp_path: Path,
):
    active_session_path = tmp_path / "active_session.txt"
    active_session_path.write_text("sess_missing", encoding="utf-8")
    monkeypatch.setattr("app.main.ACTIVE_SESSION_PATH", active_session_path)

    with TestClient(app) as client:
        response = client.get("/authorization/active")
        assert response.status_code == 404
        assert "Not authorized" in response.json()["detail"]

import hashlib
import secrets
from typing import Optional

from sqlmodel import Session, select

from app.models.agent_authorization import AgentAuthorization


class AuthorizationService:

    def __init__(self, session: Session):
        self.session = session

    def generate(self, session_id: str) -> tuple[AgentAuthorization, str]:
        existing = self.get_active(session_id)
        if existing:
            raise ValueError(
                "An active agent authorization already exists for this session."
            )

        authorization_token = f"ap_demo_{secrets.token_urlsafe(32)}"
        authorization = AgentAuthorization(
            agent_id=f"agent_{secrets.token_hex(8)}",
            authorization_token_hash=self._hash_token(authorization_token),
            session_id=session_id,
            active=True,
        )
        self.session.add(authorization)
        self.session.commit()
        self.session.refresh(authorization)
        return authorization, authorization_token

    def get_active(self, session_id: str) -> Optional[AgentAuthorization]:
        statement = select(AgentAuthorization).where(
            AgentAuthorization.session_id == session_id,
            AgentAuthorization.active.is_(True),
        )
        return self.session.exec(statement).first()

    def validate(
        self,
        authorization_token: Optional[str],
        session_id: str,
    ) -> tuple[Optional[AgentAuthorization], str]:
        if not authorization_token:
            return None, "missing_token"

        token_hash = self._hash_token(authorization_token)
        statement = select(AgentAuthorization).where(
            AgentAuthorization.authorization_token_hash == token_hash,
        )
        authorization = self.session.exec(statement).first()

        if not authorization:
            return None, "invalid_token"
        if not authorization.active:
            return None, "inactive_token"
        if authorization.session_id != session_id:
            return None, "wrong_session"

        return authorization, "authorized"

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

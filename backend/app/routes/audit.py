from fastapi import APIRouter

from app.services.audit_service import AuditService

router = APIRouter()


def _get_session():
    from app.main import get_session

    return get_session()


def _active_session_id():
    from app.main import get_active_session_id

    return get_active_session_id()


@router.get("/audit/recent")
def get_recent_audit(limit: int = 50, session_id: str | None = None):
    session_id = session_id or _active_session_id()
    with _get_session() as session:
        logs = AuditService(session).get_recent_logs(
            limit=limit,
            session_id=session_id,
        )
        return [
            {
                "id": log.id,
                "session_id": log.session_id,
                "order_id": log.order_id,
                "tool_name": log.tool_name,
                "decision": log.decision,
                "reason": log.reason,
                "input": log.input,
                "result": log.result,
                "event_id": log.event_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]

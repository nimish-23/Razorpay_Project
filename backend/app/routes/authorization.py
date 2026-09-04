from fastapi import APIRouter, HTTPException

from app.services.authorization_service import AuthorizationService

router = APIRouter()


def _get_session():
    from app.main import get_session

    return get_session()


@router.post("/authorization/generate")
def generate_authorization():
    from app.main import get_active_session_id

    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=503,
            detail="No active MCP session is available.",
        )

    with _get_session() as session:
        service = AuthorizationService(session)
        try:
            authorization, token = service.generate(session_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error))

        return {
            "agent_id": authorization.agent_id,
            "authorization_token": token,
            "status": "authorized",
            "session_id": authorization.session_id,
        }


@router.get("/authorization/active")
def get_active_authorization():
    from app.main import get_active_session_id

    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Not authorized: no active MCP session.",
        )

    with _get_session() as session:
        authorization = AuthorizationService(session).get_active(session_id)
        if not authorization:
            raise HTTPException(
                status_code=404,
                detail="Not authorized for the current session.",
            )

        return {
            "agent_id": authorization.agent_id,
            "status": "authorized",
            "session_id": authorization.session_id,
        }

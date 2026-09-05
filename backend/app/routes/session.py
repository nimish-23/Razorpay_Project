from fastapi import APIRouter

router = APIRouter()


@router.get("/session/active")
def get_active_session():
    from app.main import get_active_session_id

    return {"session_id": get_active_session_id()}

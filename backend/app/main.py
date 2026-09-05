from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import RAZORPAY_WEBHOOK_SECRET
from app.db import create_db_and_tables, get_session
from app.services.catalog_service import CatalogService


if not RAZORPAY_WEBHOOK_SECRET:
    raise RuntimeError(
        "RAZORPAY_WEBHOOK_SECRET must be set in the environment."
    )


app = FastAPI(
    title="Rohan's Sneaker Store",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
ACTIVE_SESSION_PATH = BASE_DIR / "active_session.txt"


def get_active_session_id() -> str | None:
    try:
        session_id = ACTIVE_SESSION_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return session_id or None


@app.on_event("startup")
def startup():
    create_db_and_tables()

    catalog_path = BASE_DIR / "data" / "catalog.json"
    with get_session() as session:
        CatalogService(session).seed_catalog(str(catalog_path))


from app.routes.audit import router as audit_router
from app.routes.authorization import router as authorization_router
from app.routes.frontend import router as frontend_router
from app.routes.health import router as health_router
from app.routes.orders import router as orders_router
from app.routes.policy import router as policy_router
from app.routes.session import router as session_router
from app.routes.webhooks import router as webhooks_router


app.include_router(health_router)
app.include_router(session_router)
app.include_router(authorization_router)
app.include_router(policy_router)
app.include_router(orders_router)
app.include_router(audit_router)
app.include_router(webhooks_router)
app.include_router(frontend_router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
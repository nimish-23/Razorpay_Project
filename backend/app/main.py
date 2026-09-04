from pathlib import Path
import os
import hmac
import hashlib
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import select

from app.db import create_db_and_tables, get_session
from app.models.order import Order
from app.models.product import Product
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService
from app.services.policy_service import PolicyService
from app.services.webhook_service import WebhookService

load_dotenv()

RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

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


class PolicyRequest(BaseModel):
    maximum_transaction_amount: float = Field(gt=0)
    approval_threshold: float = Field(gt=0)
    payment_verification_required: bool


def get_active_session_id() -> str | None:
    try:
        session_id = ACTIVE_SESSION_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return session_id or None


@app.on_event("startup")
def startup():
    # Create database and tables
    create_db_and_tables()

    # Seed catalog
    catalog_path = BASE_DIR / "data" / "catalog.json"

    with get_session() as session:
        service = CatalogService(session)
        service.seed_catalog(str(catalog_path))


@app.get("/session/active")
def get_active_session():
    return {"session_id": get_active_session_id()}


@app.post("/authorization/generate")
def generate_authorization():
    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=503,
            detail="No active MCP session is available.",
        )

    with get_session() as session:
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


@app.get("/authorization/active")
def get_active_authorization():
    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Not authorized: no active MCP session.",
        )

    with get_session() as session:
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


def policy_response(policy):
    return {
        "session_id": policy.session_id,
        "agent_id": policy.agent_id,
        "maximum_transaction_amount": policy.maximum_transaction_amount,
        "approval_threshold": policy.approval_threshold,
        "payment_verification_required": policy.payment_verification_required,
    }


@app.get("/policy/active")
def get_active_policy():
    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Not authorized: no active MCP session.",
        )

    with get_session() as session:
        authorization = AuthorizationService(session).get_active(session_id)
        if not authorization:
            raise HTTPException(
                status_code=404,
                detail="Not authorized for the current session.",
            )
        policy = PolicyService(session).get_or_create(authorization)
        return policy_response(policy)


@app.post("/policy")
def update_policy(policy_request: PolicyRequest):
    session_id = get_active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Not authorized: no active MCP session.",
        )

    with get_session() as session:
        authorization = AuthorizationService(session).get_active(session_id)
        if not authorization:
            raise HTTPException(
                status_code=404,
                detail="Not authorized for the current session.",
            )
        try:
            policy = PolicyService(session).update(
                authorization=authorization,
                maximum_transaction_amount=policy_request.maximum_transaction_amount,
                approval_threshold=policy_request.approval_threshold,
                payment_verification_required=policy_request.payment_verification_required,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return policy_response(policy)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Merchant backend is running"
    }


@app.get("/orders/latest")
def get_latest_order(session_id: str | None = None):
    session_id = session_id or get_active_session_id()
    with get_session() as session:
        statement = select(Order).order_by(Order.created_at.desc())
        if session_id:
            statement = statement.where(Order.session_id == session_id)
        order = session.exec(statement).first()

        if not order:
            return None

        product = session.get(Product, order.item_id)

        return {
            "order_id": order.order_id,
            "session_id": order.session_id,
            "item_id": order.item_id,
            "product_name": product.name if product else order.item_id,
            "qty": order.qty,
            "amount": order.amount,
            "currency": order.currency,
            "status": order.status,
            "selected_attributes": order.selected_attributes,
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_link_id": order.razorpay_payment_link_id,
            "razorpay_payment_id": order.razorpay_payment_id,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }


@app.get("/orders")
def list_orders(limit: int = 20, session_id: str | None = None):
    session_id = session_id or get_active_session_id()
    with get_session() as session:
        statement = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if session_id:
            statement = statement.where(Order.session_id == session_id)
        orders = session.exec(statement).all()

        results = []
        for order in orders:
            product = session.get(Product, order.item_id)
            results.append({
                "order_id": order.order_id,
                "session_id": order.session_id,
                "item_id": order.item_id,
                "product_name": product.name if product else order.item_id,
                "qty": order.qty,
                "amount": order.amount,
                "currency": order.currency,
                "status": order.status,
                "selected_attributes": order.selected_attributes,
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_link_id": order.razorpay_payment_link_id,
                "razorpay_payment_id": order.razorpay_payment_id,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            })
        return results


@app.get("/orders/{order_id}/status")
def get_order_status(order_id: str):
    with get_session() as session:
        service = OrderService(session)

        try:
            return service.sync_payment_status(order_id)
        except ValueError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )


@app.get("/orders/{order_id}/history")
def get_order_history(order_id: str):
    with get_session() as session:
        order = session.get(Order, order_id)
        active_session_id = get_active_session_id()
        if not order or (
            active_session_id and order.session_id != active_session_id
        ):
            raise HTTPException(status_code=404, detail="Order not found")
        audit_service = AuditService(session, order.session_id)
        history = audit_service.get_order_history(order_id)
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
            for log in history
        ]


@app.get("/audit/recent")
def get_recent_audit(
    limit: int = 50,
    session_id: str | None = None
):
    session_id = session_id or get_active_session_id()
    with get_session() as session:
        audit_service = AuditService(session)

        logs = audit_service.get_recent_logs(
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
                "timestamp": (
                    log.timestamp.isoformat()
                    if log.timestamp
                    else None
                ),
            }
            for log in logs
        ]


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()

    signature = request.headers.get("X-Razorpay-Signature")
    event_id = request.headers.get("X-Razorpay-Event-Id")

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        )

    if event_id:
        event["event_id"] = event_id

    with get_session() as session:
        service = WebhookService(session)

        result = service.process_razorpay_event(event)

    return result


# Serve frontend UI directly
@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend not found"}


@app.get("/style.css")
def serve_css():
    css_path = FRONTEND_DIR / "style.css"
    if css_path.exists():
        return FileResponse(str(css_path), media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js")
def serve_js():
    js_path = FRONTEND_DIR / "app.js"
    if js_path.exists():
        return FileResponse(str(js_path), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
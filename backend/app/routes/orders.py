from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.models.order import Order
from app.models.product import Product
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.order_service import OrderService

router = APIRouter()


def _get_session():
    from app.main import get_session

    return get_session()


def _active_session_id():
    from app.main import get_active_session_id

    return get_active_session_id()


def _order_response(session, order):
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


@router.post("/orders/{order_id}/approve")
def approve_order(order_id: str):
    session_id = _active_session_id()
    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="Approval failed: no active MCP session.",
        )

    with _get_session() as session:
        order = session.get(Order, order_id)
        authorization = AuthorizationService(session).get_active(session_id)
        approved_order, result = ApprovalService(session).approve(
            order,
            authorization,
            session_id,
        )

        if result == "order_not_found":
            raise HTTPException(
                status_code=404,
                detail="Approval failed: order not found for the current session.",
            )
        if result == "not_awaiting_approval":
            raise HTTPException(
                status_code=409,
                detail="Approval failed: order is not waiting for approval.",
            )
        if result == "not_authorized":
            raise HTTPException(
                status_code=403,
                detail="Approval failed: current session is not authorized.",
            )

        return {
            "order_id": approved_order.order_id,
            "session_id": approved_order.session_id,
            "status": approved_order.status,
            "amount": approved_order.amount,
            "currency": approved_order.currency,
        }


@router.get("/orders/latest")
def get_latest_order(session_id: str | None = None):
    session_id = session_id or _active_session_id()
    with _get_session() as session:
        statement = select(Order).order_by(Order.created_at.desc())
        if session_id:
            statement = statement.where(Order.session_id == session_id)
        order = session.exec(statement).first()
        return _order_response(session, order) if order else None


@router.get("/orders")
def list_orders(limit: int = 20, session_id: str | None = None):
    session_id = session_id or _active_session_id()
    with _get_session() as session:
        statement = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if session_id:
            statement = statement.where(Order.session_id == session_id)
        return [_order_response(session, order) for order in session.exec(statement).all()]


@router.get("/orders/{order_id}/status")
def get_order_status(order_id: str):
    with _get_session() as session:
        service = OrderService(session)
        try:
            return service.sync_payment_status(order_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error))


@router.get("/orders/{order_id}/history")
def get_order_history(order_id: str):
    with _get_session() as session:
        order = session.get(Order, order_id)
        active_session_id = _active_session_id()
        if not order or (active_session_id and order.session_id != active_session_id):
            raise HTTPException(status_code=404, detail="Order not found")
        history = AuditService(session, order.session_id).get_order_history(order_id)
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

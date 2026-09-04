from typing import Optional, Any
from pathlib import Path

from mcp.server.mcpserver import Context, MCPServer
from razorpay.errors import BadRequestError, GatewayError, ServerError
from uuid import uuid4
from app.db import get_session
from app.models.order import Order
from app.models.product import Product
from app.models.agent_authorization import AgentAuthorization
from app.services.catalog_service import CatalogService
from app.services.audit_service import AuditService
from app.services.authorization_service import AuthorizationService
from app.services.order_service import OrderService
from app.services.policy_service import PolicyService
from app.services.payment_service import PaymentService


server = MCPServer(
    name="Rohan's Merchant",
    version="1.0.0"
)

SESSION_ID = f"sess_{uuid4().hex[:12].upper()}"
ACTIVE_SESSION_PATH = Path(__file__).resolve().parents[2] / "active_session.txt"


def write_active_session():
    ACTIVE_SESSION_PATH.write_text(SESSION_ID, encoding="utf-8")


def format_razorpay_error(error: Exception) -> str:
    details = [
        str(error),
        getattr(error, "code", None),
        getattr(error, "description", None),
    ]
    return "Razorpay error: " + "; ".join(
        detail for detail in details if detail
    )


def _token_from_request(
    authorization_token: Optional[str],
    ctx: Optional[Context],
) -> tuple[Optional[str], bool]:
    if authorization_token:
        return authorization_token, True
    if ctx is None:
        return None, False

    try:
        headers = ctx.headers
    except ValueError:
        return None, False

    if headers is None:
        return None, False

    bearer = headers.get("authorization") or headers.get("Authorization")
    if bearer and bearer.lower().startswith("bearer "):
        return bearer[7:].strip() or None, True
    return headers.get("x-agent-authorization"), True


def _authorize_transaction(
    session,
    tool_name: str,
    authorization_token: Optional[str],
    ctx: Optional[Context],
) -> tuple[Optional[AgentAuthorization], Optional[dict]]:
    token, token_transport_available = _token_from_request(
        authorization_token,
        ctx,
    )
    authorization_service = AuthorizationService(session)
    if token_transport_available:
        authorization, result = authorization_service.validate(
            token,
            SESSION_ID,
        )
    else:
        authorization, result = (
            authorization_service.validate_current_session_authorization(
                SESSION_ID
            )
        )
    if authorization:
        return authorization, None

    agent_id = authorization.agent_id if authorization else None
    AuditService(session, SESSION_ID).log_event(
        tool_name="agent_authorization_failed",
        decision="denied",
        reason=f"Agent authorization failed: {result}.",
        input_data={
            "agent_id": agent_id,
            "session_id": SESSION_ID,
            "authorization_result": result,
        },
        result_data={
            "authorized": False,
            "failure_reason": result,
        },
    )
    return authorization, {
        "authorized": False,
        "error": "agent_not_authorized",
        "message": (
            "Agent authorization is required before performing this transaction."
        ),
        "reason": result,
    }


def _evaluate_transaction_policy(
    session,
    authorization: AgentAuthorization,
    amount: float,
    approval_granted: bool = False,
) -> tuple[dict[str, object], object]:
    policy = PolicyService(session).get_or_create(authorization)
    decision = PolicyService(session).evaluate(
        policy,
        amount,
        approval_granted=approval_granted,
    )
    return decision, policy


def _audit_policy_decision(
    session,
    authorization: AgentAuthorization,
    policy,
    decision: dict[str, object],
    amount: float,
    order_id: Optional[str] = None,
) -> None:
    audit_service = AuditService(session, SESSION_ID)
    audit_data = {
        "agent_id": authorization.agent_id,
        "session_id": SESSION_ID,
        "order_id": order_id,
        "transaction_amount": amount,
        "maximum_transaction_amount": policy.maximum_transaction_amount,
        "approval_threshold": policy.approval_threshold,
        "decision": decision,
    }

    if not decision["allowed"]:
        audit_service.log_event(
            tool_name="policy_check_failed",
            decision="blocked",
            reason=str(decision["reason"]),
            input_data=audit_data,
            result_data=decision,
            order_id=order_id,
        )
    elif decision["approval_required"]:
        audit_service.log_event(
            tool_name="policy_approval_required",
            decision="approval_required",
            reason=str(decision["reason"]),
            input_data=audit_data,
            result_data=decision,
            order_id=order_id,
        )
    else:
        audit_service.log_event(
            tool_name="policy_check_passed",
            decision="allowed",
            reason=str(decision["reason"]),
            input_data=audit_data,
            result_data=decision,
            order_id=order_id,
        )


@server.tool(
    name="get_agent_authorization",
    description=(
        "Read the authorization status and agent identity for the current "
        "MCP session. Does not return or generate an authorization token."
    ),
)
def get_agent_authorization() -> dict:
    with get_session() as session:
        authorization = AuthorizationService(session).get_active(SESSION_ID)

        if not authorization:
            return {
                "authorized": False,
                "agent_id": None,
                "session_id": SESSION_ID,
                "status": "not_authorized",
                "message": (
                    "No active AgentPay authorization exists for this MCP session."
                ),
            }

        return {
            "authorized": True,
            "agent_id": authorization.agent_id,
            "session_id": SESSION_ID,
            "status": "authorized",
        }


@server.tool(
    name="search_catalog",
    description=(
        "Search products in the merchant catalog. "
        "You can filter by text, category, maximum price, "
        "or any product attributes."
    )
)
def search_catalog(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> dict:

    with get_session() as session:

        catalog_service = CatalogService(
            session,
            SESSION_ID
        )

        products = catalog_service.search_catalog(
            query=query,
            max_price=max_price,
            category=category,
            attributes=attributes,
        )

        return {
            "count": len(products),
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "currency": product.currency,
                    "stock": product.stock,
                    "attributes": product.attributes,
                }
                for product in products
            ],
        }


@server.tool(
    name="create_order",
    description=(
        "Create an order for a product. "
        "Quantity and optional product attributes can be provided. "
        "Pass the authorization_token from AgentPay to authorize the transaction."
    )
)
def create_order(
    item_id: str,
    qty: int = 1,
    selected_attributes: Optional[dict[str, Any]] = None,
    authorization_token: Optional[str] = None,
    ctx: Context = None,
) -> dict:

    try:

        with get_session() as session:

            authorization, authorization_failure = _authorize_transaction(
                session,
                "create_order",
                authorization_token,
                ctx,
            )
            if authorization_failure:
                return authorization_failure

            product = session.get(Product, item_id)
            if product is not None and qty > 0:
                decision, policy = _evaluate_transaction_policy(
                    session,
                    authorization,
                    product.price * qty,
                )
                if not decision["allowed"]:
                    _audit_policy_decision(
                        session, authorization, policy, decision,
                        product.price * qty,
                    )
                    return {
                        "success": False,
                        "policy_violation": True,
                        "allowed": False,
                        "error": "policy_violation",
                        "message": "Transaction blocked by AgentPay policy.",
                        "reason": decision["reason"],
                    }

            order_service = OrderService(
            session,
            SESSION_ID
        )

            order = order_service.create_order(
                item_id=item_id,
                qty=qty,
                selected_attributes=selected_attributes,
            )

            if product is not None and qty > 0 and decision["approval_required"]:
                order.status = "approval_required"
                session.add(order)
                session.commit()
                session.refresh(order)
                _audit_policy_decision(
                    session, authorization, policy, decision,
                    order.amount, order.order_id,
                )
                return {
                    "success": False,
                    "approval_required": True,
                    "order_id": order.order_id,
                    "message": (
                        "User approval is required before payment can proceed."
                    ),
                }

            if product is not None and qty > 0:
                _audit_policy_decision(
                    session, authorization, policy, decision,
                    order.amount, order.order_id,
                )

            return {
                "success": True,
                "order": {
                    "order_id": order.order_id,
                    "item_id": order.item_id,
                    "qty": order.qty,
                    "selected_attributes": order.selected_attributes,
                    "amount": order.amount,
                    "currency": order.currency,
                    "status": order.status,
                },
            }

    except ValueError as e:

        return {
            "success": False,
            "error": str(e),
        }


@server.tool(
    name="get_order_status",
    description=(
        "Get the current payment status of an order. "
        "Use the local order_id returned by create_order."
    )
)
def get_order_status(order_id: str) -> dict:
    try:
        with get_session() as session:
            order_service = OrderService(session, SESSION_ID)

            result = order_service.sync_payment_status(
                order_id=order_id
            )

            return {
                "success": True,
                "order": result,
            }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


@server.tool(
    name="create_payment",
    description=(
        "Create a Razorpay payment link for an existing order. "
        "Use the local order_id returned by create_order. "
        "Returns a payment URL that can be given to the customer. "
        "Pass the authorization_token from AgentPay to authorize the transaction."
    )
)
def create_payment(
    order_id: str,
    authorization_token: Optional[str] = None,
    ctx: Context = None,
) -> dict:

    try:
        with get_session() as session:

            authorization, authorization_failure = _authorize_transaction(
                session,
                "create_payment",
                authorization_token,
                ctx,
            )
            if authorization_failure:
                return authorization_failure

            order = session.get(Order, order_id)

            if order is not None and order.session_id != SESSION_ID:
                order = None

            if order is None:
                return {
                    "success": False,
                    "error": f"Order '{order_id}' was not found.",
                }

            decision, policy = _evaluate_transaction_policy(
                session,
                authorization,
                order.amount,
                approval_granted=order.status == "approved",
            )
            if not decision["allowed"]:
                _audit_policy_decision(
                    session, authorization, policy, decision,
                    order.amount, order.order_id,
                )
                return {
                    "success": False,
                    "policy_violation": True,
                    "allowed": False,
                    "error": "policy_violation",
                    "message": "Transaction blocked by AgentPay policy.",
                    "reason": decision["reason"],
                }
            if decision["approval_required"]:
                _audit_policy_decision(
                    session, authorization, policy, decision,
                    order.amount, order.order_id,
                )
                return {
                    "success": False,
                    "approval_required": True,
                    "order_id": order.order_id,
                    "message": (
                        "User approval is required before payment can proceed."
                    ),
                }
            _audit_policy_decision(
                session, authorization, policy, decision,
                order.amount, order.order_id,
            )

            product = session.get(
                Product,
                order.item_id
            )

            if product is None:
                return {
                    "success": False,
                    "error": (
                        f"Product '{order.item_id}' "
                        "was not found."
                    ),
                }

            payment_service = PaymentService(session, SESSION_ID)

            result = payment_service.create_payment(
                order=order,
                product_name=product.name,
            )

            return {
                "success": True,
                "payment": result,
            }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }
    except (BadRequestError, GatewayError, ServerError) as e:
        return {
            "success": False,
            "error": format_razorpay_error(e),
        }

if __name__ == "__main__":
    write_active_session()
    server.run("stdio")
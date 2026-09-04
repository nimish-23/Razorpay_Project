import uuid
from app.db import get_session
from app.models.order import Order
from app.services.audit_service import AuditService
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService


def test_create_audit_event():
    with get_session() as session:
        service = AuditService(session)
        log = service.log_event(
            tool_name="test_tool",
            decision="success",
            reason="Testing audit event creation",
            input_data={"param": "value"},
            result_data={"output": 123},
        )
        assert log.id is not None
        assert log.tool_name == "test_tool"
        assert log.decision == "success"
        assert log.reason == "Testing audit event creation"
        assert log.input == {"param": "value"}
        assert log.result == {"output": 123}
        assert log.order_id is None


def test_audit_event_associated_with_order_id():
    test_order_id = f"ORD-TEST-{uuid.uuid4().hex[:8].upper()}"
    with get_session() as session:
        service = AuditService(session)
        log = service.log_event(
            tool_name="test_order_event",
            decision="success",
            reason="Testing order_id association",
            order_id=test_order_id,
        )
        assert log.id is not None
        assert log.order_id == test_order_id


def test_order_lifecycle_audit_trail_and_chronology():
    test_order_id = f"ORD-AUDIT-{uuid.uuid4().hex[:8].upper()}"

    with get_session() as session:
        audit_service = AuditService(session)

        # 1. Catalog search (order_id is None because order doesn't exist yet)
        catalog_log = audit_service.log_catalog_search(
            query="runner",
            product_ids=["shoe_001"],
        )
        assert catalog_log.tool_name == "catalog_search"
        assert catalog_log.order_id is None

        # 2. Order created
        order = Order(
            order_id=test_order_id,
            item_id="shoe_001",
            qty=1,
            amount=2199.0,
            currency="INR",
            status="pending_payment",
            selected_attributes={"size": 9},
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        order_log = audit_service.log_order_created(order)
        assert order_log.order_id == test_order_id
        assert order_log.tool_name == "order_created"

        # 3. Payment initiated
        pay_init_log = audit_service.log_payment_initiated(
            order_id=test_order_id,
            razorpay_order_id="order_dummy_123",
            payment_link_id="plink_dummy_123",
            amount=2199.0,
            currency="INR",
        )
        assert pay_init_log.order_id == test_order_id
        assert pay_init_log.tool_name == "payment_initiated"

        # 4. Payment status changed
        pay_status_log = audit_service.log_payment_status_changed(
            order_id=test_order_id,
            status="paid",
            razorpay_status="paid",
            payment_id="pay_dummy_123",
            amount_paid=2199.0,
            event_id=f"evt_{uuid.uuid4().hex}",
            event_name="payment_link.paid",
        )
        assert pay_status_log.order_id == test_order_id
        assert pay_status_log.tool_name == "payment_status_changed"

        # 5. Payment finished
        pay_finished_log = audit_service.log_payment_finished(
            order_id=test_order_id,
            payment_id="pay_dummy_123",
            amount_paid=2199.0,
        )
        assert pay_finished_log.order_id == test_order_id
        assert pay_finished_log.tool_name == "payment_finished"
        assert pay_finished_log.result["payment_id"] == "pay_dummy_123"

        # 6. Order placed / completed
        order_placed_log = audit_service.log_order_placed(
            order_id=test_order_id,
            status="paid",
        )
        assert order_placed_log.order_id == test_order_id
        assert order_placed_log.tool_name == "order_placed"

        # Retrieve order history chronologically
        history = audit_service.get_order_history(test_order_id)

        assert len(history) == 5
        event_names = [log.tool_name for log in history]
        expected_names = [
            "order_created",
            "payment_initiated",
            "payment_status_changed",
            "payment_finished",
            "order_placed",
        ]
        assert event_names == expected_names

        # Verify clear distinction between payment_finished and order_placed
        payment_finished_event = next(e for e in history if e.tool_name == "payment_finished")
        order_placed_event = next(e for e in history if e.tool_name == "order_placed")

        assert payment_finished_event.tool_name != order_placed_event.tool_name
        assert "payment_id" in payment_finished_event.result
        assert "status" in order_placed_event.result


def test_order_service_and_catalog_service_audit_integration():
    with get_session() as session:
        catalog_service = CatalogService(session)
        search_results = catalog_service.search_catalog(query="runner")
        assert len(search_results) > 0

        order_service = OrderService(session)
        order = order_service.create_order(
            item_id="shoe_001",
            qty=1,
            selected_attributes={"size": 9},
        )
        assert order.order_id is not None

        audit_service = AuditService(session)
        history = audit_service.get_order_history(order.order_id)
        assert len(history) >= 1
        assert history[0].tool_name == "order_created"
        assert history[0].order_id == order.order_id

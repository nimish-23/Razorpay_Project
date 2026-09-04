from fastapi import APIRouter, HTTPException, Request

from app.services.webhook_service import WebhookService

router = APIRouter()


def _get_session():
    from app.main import get_session

    return get_session()


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    await request.body()
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

    with _get_session() as session:
        result = WebhookService(session).process_razorpay_event(event)

    return result

from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["Payments"])

# TODO: POST /payments/execute
# TODO: POST /payments/webhook (optional)

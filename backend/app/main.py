from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db import create_db_and_tables
from app.merchant.routes import router as merchant_router
from app.agent.routes import router as agent_router
from app.policy.routes import router as policy_router
from app.payments.routes import router as payments_router
from app.audit.routes import router as audit_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Agentic Trust Layer API", lifespan=lifespan)

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(merchant_router)
app.include_router(agent_router)
app.include_router(policy_router)
app.include_router(payments_router)
app.include_router(audit_router)

@app.get("/")
def health_check():
    return {"status": "ok"}

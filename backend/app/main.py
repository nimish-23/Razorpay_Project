from fastapi import FastAPI

from app.db import create_db_and_tables


app = FastAPI(
    title="Rohan's Sneaker Store",
    version="1.0.0"
)


@app.on_event("startup")
def startup():
    create_db_and_tables()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Merchant backend is running"
    }
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo import MongoClient

from services.customer.repository import MongoProfileRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MongoClient(
        os.environ.get("MONGODB_URL", "mongodb://localhost:27017/retail_profiles"),
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
        database = client[os.environ.get("MONGODB_DATABASE", "retail_profiles")]
        app.state.repository = MongoProfileRepository(database.customer_profiles)
        yield
    finally:
        client.close()


app = FastAPI(title="Retail Customer Profile Service", lifespan=lifespan)


class CustomerProfileInput(BaseModel):
    preferences: list[str] = Field(default_factory=list, max_length=20)


def get_repository(request: Request) -> MongoProfileRepository:
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="Customer profile database is not ready.")
    return repository


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(request: Request) -> dict[str, str]:
    if getattr(request.app.state, "repository", None) is None:
        raise HTTPException(status_code=503, detail="Customer profile database is not ready.")
    return {"status": "ready"}


@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str, request: Request) -> dict[str, object]:
    profile = get_repository(request).get_profile(customer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return profile


@app.put("/api/v1/customers/{customer_id}")
def save_customer(
    customer_id: str,
    profile: CustomerProfileInput,
    request: Request,
) -> dict[str, object]:
    if not customer_id.strip() or len(customer_id) > 100:
        raise HTTPException(status_code=422, detail="Customer ID must contain 1 to 100 characters.")
    stored = {
        "customer_id": customer_id,
        "preferences": [value.strip() for value in profile.preferences if value.strip()],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return get_repository(request).save_profile(stored)

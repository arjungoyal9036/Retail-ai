import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.shared import request_json

app = FastAPI(
    title="Retail Recommendation & Shopping Assistant API Gateway",
    description="Web storefront and API gateway for the retail microservices.",
    version="2.0.0",
)

WEB_INDEX = Path(__file__).parent / "static" / "index.html"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    max_price: float | None = Field(default=None, gt=0)
    limit: int = Field(default=3, ge=1, le=10)
    user_id: str | None = Field(default=None, max_length=100)


class CustomerProfileInput(BaseModel):
    preferences: list[str] = Field(default_factory=list, max_length=20)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_INDEX)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    for service_url in (
        os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000"),
        os.environ.get(
            "RECOMMENDATION_SERVICE_URL",
            "http://recommendation-service:8000",
        ),
        os.environ.get("CHATBOT_SERVICE_URL", "http://chatbot-service:8000"),
        os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
    ):
        await request_json(service_url, "GET", "/health/ready")
    return {"status": "ready"}


@app.get("/api/v1/products", tags=["products"])
async def list_products(
    query: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=50),
    max_price: Annotated[float | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    return await request_json(
        os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000"),
        "GET",
        "/api/v1/products",
        params={
            key: value
            for key, value in {
                "query": query,
                "category": category,
                "max_price": max_price,
                "limit": limit,
            }.items()
            if value is not None
        },
    )


@app.get("/api/v1/products/{product_id}", tags=["products"])
async def get_product(product_id: str) -> dict[str, object]:
    return await request_json(
        os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000"),
        "GET",
        f"/api/v1/products/{product_id}",
    )


@app.get("/api/v1/recommendations", tags=["recommendations"])
async def get_recommendations(
    product_id: str | None = None,
    category: str | None = Query(default=None, max_length=50),
    preferences: Annotated[list[str] | None, Query()] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    user_id: str | None = Query(default=None, max_length=100),
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict[str, object]:
    params: dict[str, object] = {
        key: value
        for key, value in {
            "product_id": product_id,
            "category": category,
            "preferences": preferences,
            "max_price": max_price,
            "user_id": user_id,
            "limit": limit,
        }.items()
        if value is not None
    }
    return await request_json(
        os.environ.get("RECOMMENDATION_SERVICE_URL", "http://recommendation-service:8000"),
        "GET",
        "/api/v1/recommendations",
        params=params,
    )


@app.post("/api/v1/chat", tags=["chat"])
async def chat(request: ChatRequest) -> dict[str, object]:
    return await request_json(
        os.environ.get("CHATBOT_SERVICE_URL", "http://chatbot-service:8000"),
        "POST",
        "/api/v1/chat",
        json_body=request.model_dump(exclude_none=True),
    )


@app.get("/api/v1/customers/{customer_id}", tags=["customers"])
async def get_customer(customer_id: str) -> dict[str, object]:
    return await request_json(
        os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
        "GET",
        f"/api/v1/customers/{customer_id}",
    )


@app.put("/api/v1/customers/{customer_id}", tags=["customers"])
async def save_customer(
    customer_id: str,
    profile: CustomerProfileInput,
) -> dict[str, object]:
    return await request_json(
        os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
        "PUT",
        f"/api/v1/customers/{customer_id}",
        json_body=profile.model_dump(),
    )

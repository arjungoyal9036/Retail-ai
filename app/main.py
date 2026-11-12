from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.catalog import PRODUCT_BY_ID, PRODUCTS, product_as_dict, search_products
from app.chat import respond_to_message
from app.recommendations import recommend_products

app = FastAPI(
    title="Retail Recommendation & Shopping Assistant",
    description="A lightweight retail product recommendation and chatbot API.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    max_price: float | None = Field(default=None, gt=0)
    limit: int = Field(default=3, ge=1, le=10)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/api/v1/products", tags=["products"])
def list_products(
    query: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=50),
    max_price: Annotated[float | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    products = search_products(query, limit=50) if query else list(PRODUCTS)
    if category:
        products = [item for item in products if item.category.casefold() == category.casefold()]
    if max_price is not None:
        products = [item for item in products if item.price <= max_price]
    return {"items": [product_as_dict(item) for item in products[:limit]], "count": min(len(products), limit)}


@app.get("/api/v1/products/{product_id}", tags=["products"])
def get_product(product_id: str) -> dict[str, object]:
    product = PRODUCT_BY_ID.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_as_dict(product)


@app.get("/api/v1/recommendations", tags=["recommendations"])
def get_recommendations(
    product_id: str | None = None,
    category: str | None = Query(default=None, max_length=50),
    preferences: Annotated[list[str] | None, Query()] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict[str, object]:
    if product_id and product_id not in PRODUCT_BY_ID:
        raise HTTPException(status_code=404, detail="Product not found")
    products = recommend_products(
        product_id=product_id,
        category=category,
        preferences=preferences,
        max_price=max_price,
        limit=limit,
    )
    return {"items": [product_as_dict(item) for item in products], "count": len(products)}


@app.post("/api/v1/chat", tags=["chat"])
def chat(request: ChatRequest) -> dict[str, object]:
    reply, products = respond_to_message(
        request.message,
        max_price=request.max_price,
        limit=request.limit,
    )
    return {
        "reply": reply,
        "recommendations": [product_as_dict(item) for item in products],
    }

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from app.catalog import product_from_dict, product_as_dict
from app.gemini import GeminiServiceError, gemini_is_configured
from app.recommendations import recommend_products, recommend_products_with_gemini
from services.shared import request_json

app = FastAPI(title="Retail Recommendation Service")


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    await request_json(
        os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000"),
        "GET",
        "/health/ready",
    )
    await request_json(
        os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
        "GET",
        "/health/ready",
    )
    return {"status": "ready"}


@app.get("/api/v1/recommendations")
async def get_recommendations(
    product_id: str | None = None,
    category: str | None = Query(default=None, max_length=50),
    preferences: Annotated[list[str] | None, Query()] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    user_id: str | None = Query(default=None, max_length=100),
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict[str, object]:
    catalog_url = os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000")
    catalog_response = await request_json(
        catalog_url,
        "GET",
        "/api/v1/products",
        params={"limit": 50},
    )
    raw_products = catalog_response.get("items")
    if not isinstance(raw_products, list):
        raise HTTPException(status_code=502, detail="Catalog service returned invalid products.")
    products = [product_from_dict(item) for item in raw_products if isinstance(item, dict)]

    customer_preferences: list[str] = []
    if user_id:
        profile_response = await request_json(
            os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
            "GET",
            f"/api/v1/customers/{user_id}",
        )
        stored_preferences = profile_response.get("preferences", [])
        if isinstance(stored_preferences, list):
            customer_preferences = [str(item) for item in stored_preferences]

    combined_preferences = customer_preferences + (preferences or [])
    if product_id and not any(product.id == product_id for product in products):
        raise HTTPException(status_code=404, detail="Product not found")
    recommender = recommend_products_with_gemini if gemini_is_configured() else recommend_products
    try:
        recommendations = recommender(
            product_id=product_id,
            category=category,
            preferences=combined_preferences,
            max_price=max_price,
            limit=limit,
            products=products,
        )
    except GeminiServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "items": [product_as_dict(product) for product in recommendations],
        "count": len(recommendations),
    }

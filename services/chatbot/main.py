import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.chat import _extract_budget, _find_category
from app.gemini import (
    GeminiChatResponse,
    GeminiServiceError,
    catalog_data,
    generate_structured_response,
    gemini_is_configured,
    select_catalog_products,
)
from app.catalog import product_as_dict, product_from_dict
from services.shared import request_json

app = FastAPI(title="Retail Shopping Assistant Service")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    max_price: float | None = Field(default=None, gt=0)
    limit: int = Field(default=3, ge=1, le=10)
    user_id: str | None = Field(default=None, max_length=100)


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
        os.environ.get(
            "RECOMMENDATION_SERVICE_URL",
            "http://recommendation-service:8000",
        ),
        "GET",
        "/health/ready",
    )
    return {"status": "ready"}


@app.post("/api/v1/chat")
async def chat(request: ChatRequest) -> dict[str, object]:
    budget = request.max_price
    if budget is None:
        budget = _extract_budget(request.message.casefold())
    catalog_url = os.environ.get("CATALOG_SERVICE_URL", "http://catalog-service:8000")
    recommendation_url = os.environ.get(
        "RECOMMENDATION_SERVICE_URL",
        "http://recommendation-service:8000",
    )
    catalog_response = await request_json(
        catalog_url,
        "GET",
        "/api/v1/products",
        params={"limit": 50},
    )
    raw_products = catalog_response.get("items")
    if not isinstance(raw_products, list):
        raise HTTPException(status_code=502, detail="Catalog service returned invalid products.")
    catalog_products = [
        product_from_dict(item) for item in raw_products if isinstance(item, dict)
    ]

    recommendation_params: dict[str, object] = {
        "preferences": [request.message],
        "limit": min(10, max(request.limit, 5)),
    }
    if budget is not None:
        recommendation_params["max_price"] = budget
    if request.user_id:
        recommendation_params["user_id"] = request.user_id
    category = _find_category(request.message.casefold(), catalog_products)
    if category:
        recommendation_params["category"] = category
    recommendation_response = await request_json(
        recommendation_url,
        "GET",
        "/api/v1/recommendations",
        params=recommendation_params,
    )
    raw_recommendations = recommendation_response.get("items")
    if not isinstance(raw_recommendations, list):
        raise HTTPException(
            status_code=502,
            detail="Recommendation service returned invalid products.",
        )
    candidates = [
        product_from_dict(item)
        for item in raw_recommendations
        if isinstance(item, dict)
    ]

    if gemini_is_configured():
        try:
            response = generate_structured_response(
                json.dumps(
                    {
                        "customer_message": request.message,
                        "max_price": budget,
                        "candidate_products": catalog_data(candidates),
                    },
                    ensure_ascii=True,
                ),
                GeminiChatResponse,
                system_instruction=(
                    "You are a helpful retail shopping assistant. Answer concisely using "
                    "only the supplied catalog. Select product IDs only from "
                    "candidate_products. If there are no suitable products, return an "
                    "empty product_ids list. Never invent product details or prices."
                ),
            )
        except GeminiServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        products = select_catalog_products(response.product_ids, candidates, limit=request.limit)
        reply = response.reply
    elif candidates:
        products = candidates[:request.limit]
        reply = "Here are a few options that might be a good fit."
    else:
        products = []
        reply = (
            "I can help you find products by category, describe what you need, "
            "or tell me your budget."
        )

    return {
        "reply": reply,
        "recommendations": [product_as_dict(product) for product in products],
    }

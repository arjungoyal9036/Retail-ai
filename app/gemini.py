import os
from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

from app.catalog import Product

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
T = TypeVar("T", bound=BaseModel)

load_dotenv()


class GeminiServiceError(RuntimeError):
    """Gemini request or response could not be completed safely."""


class GeminiChatResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=500)
    product_ids: list[str] = Field(default_factory=list, max_length=10)


class GeminiRecommendationResponse(BaseModel):
    product_ids: list[str] = Field(default_factory=list, max_length=10)


def gemini_is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def generate_structured_response(
    prompt: str,
    response_schema: type[T],
    *,
    system_instruction: str,
) -> T:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiServiceError("Gemini is not configured.")

    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    if not model:
        raise GeminiServiceError("GEMINI_MODEL must not be empty.")

    try:
        response = _get_client(api_key).models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.3,
            ),
        )
    except errors.APIError as exc:
        status = f" (HTTP {exc.code})" if exc.code else ""
        raise GeminiServiceError(f"Gemini API request failed{status}.") from exc
    except ValueError as exc:
        raise GeminiServiceError("Gemini API request failed.") from exc

    try:
        parsed = response.parsed
        if isinstance(parsed, response_schema):
            return parsed
        if isinstance(parsed, dict):
            return response_schema.model_validate(parsed)
        if response.text:
            return response_schema.model_validate_json(response.text)
    except (ValidationError, TypeError, ValueError) as exc:
        raise GeminiServiceError("Gemini returned an invalid response.") from exc

    raise GeminiServiceError("Gemini returned an empty response.")


def select_catalog_products(
    product_ids: list[str],
    candidates: list[Product],
    *,
    limit: int,
) -> list[Product]:
    candidates_by_id = {product.id: product for product in candidates}
    selected: list[Product] = []
    seen: set[str] = set()
    for product_id in product_ids:
        if product_id in candidates_by_id and product_id not in seen:
            selected.append(candidates_by_id[product_id])
            seen.add(product_id)
            if len(selected) == limit:
                break
    return selected


@lru_cache(maxsize=2)
def _get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def catalog_data(candidates: list[Product]) -> list[dict[str, object]]:
    return [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "price": product.price,
            "tags": product.tags,
        }
        for product in candidates
    ]

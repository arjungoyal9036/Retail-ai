import json

from app.catalog import PRODUCTS, PRODUCT_BY_ID, Product, search_products
from app.gemini import (
    GeminiChatResponse,
    catalog_data,
    generate_structured_response,
    gemini_is_configured,
    select_catalog_products,
)
from app.recommendations import recommend_products


def respond_to_message(
    message: str,
    *,
    max_price: float | None = None,
    limit: int = 3,
) -> tuple[str, list[Product]]:
    normalized = message.casefold()
    budget = max_price

    if budget is None:
        budget = _extract_budget(normalized)

    if gemini_is_configured():
        return _respond_with_gemini(message, budget=budget, limit=limit)

    if any(
        phrase in normalized
        for phrase in ("recommend", "suggest", "looking for", "shop for", "need", "want", "find")
    ):
        category = _find_category(normalized)
        products = recommend_products(
            category=category,
            preferences=[normalized],
            max_price=budget,
            limit=limit,
        )
        if products:
            return "Here are a few options that might be a good fit.", products
        return "I couldn't find a match. Try a different category or a higher budget.", []

    matches = search_products(normalized, limit=limit)
    if budget is not None:
        matches = [product for product in matches if product.price <= budget]
    if matches:
        return "I found these products that match your message.", matches

    return (
        "I can help you find products, compare options, or suggest items by category and budget. "
        "What are you shopping for?",
        [],
    )


def _respond_with_gemini(
    message: str,
    *,
    budget: float | None,
    limit: int,
) -> tuple[str, list[Product]]:
    candidates = [
        product for product in PRODUCTS if budget is None or product.price <= budget
    ]
    response = generate_structured_response(
        json.dumps(
            {
                "customer_message": message,
                "max_price": budget,
                "candidate_products": catalog_data(candidates),
            },
            ensure_ascii=True,
        ),
        GeminiChatResponse,
        system_instruction=(
            "You are a helpful retail shopping assistant. Answer the customer's request "
            "concisely using only the supplied catalog. Select product IDs only from "
            "candidate_products, and only recommend products that satisfy max_price when "
            "it is provided. If there are no suitable products, return an empty product_ids "
            "list and say so. Do not invent prices, product details, stock, or policies."
        ),
    )
    return response.reply, select_catalog_products(
        response.product_ids,
        candidates,
        limit=limit,
    )


def _extract_budget(message: str) -> float | None:
    tokens = message.replace("$", " ").replace(",", " ").split()
    for index, token in enumerate(tokens):
        if token in {"under", "below", "less"} and index + 1 < len(tokens):
            candidate = tokens[index + 1].removeprefix("$")
            try:
                return float(candidate)
            except ValueError:
                continue
    return None


def _find_category(
    message: str,
    products: list[Product] | tuple[Product, ...] | None = None,
) -> str | None:
    categories = {
        product.category
        for product in (products if products is not None else PRODUCT_BY_ID.values())
    }
    aliases = {"bag": "bags", "backpack": "bags", "apparel": "clothing"}
    for alias, category in aliases.items():
        if alias in message:
            return category
    return next((category for category in sorted(categories) if category in message), None)

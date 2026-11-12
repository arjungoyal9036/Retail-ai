import json

from app.catalog import PRODUCTS, PRODUCT_BY_ID, Product
from app.gemini import (
    GeminiRecommendationResponse,
    catalog_data,
    generate_structured_response,
    select_catalog_products,
)


def recommend_products(
    *,
    product_id: str | None = None,
    category: str | None = None,
    preferences: list[str] | None = None,
    max_price: float | None = None,
    exclude_ids: list[str] | None = None,
    limit: int = 5,
    products: tuple[Product, ...] | list[Product] = PRODUCTS,
) -> list[Product]:
    """Rank the in-memory catalog by preference and product similarity."""
    excluded = set(exclude_ids or [])
    if product_id:
        excluded.add(product_id)

    source = (
        next((product for product in products if product.id == product_id), None)
        if product_id
        else None
    )
    if source is None and product_id:
        source = PRODUCT_BY_ID.get(product_id)
    preference_terms = {
        term.casefold() for preference in (preferences or []) for term in preference.split()
    }
    source_tags = set(source.tags) if source else set()
    source_category = source.category if source else None
    requested_category = category.casefold() if category else None

    ranked: list[tuple[float, Product]] = []
    for product in products:
        if product.id in excluded:
            continue
        if max_price is not None and product.price > max_price:
            continue
        if requested_category and product.category.casefold() != requested_category:
            continue

        product_text = " ".join(
            (product.name, product.category, product.description, *product.tags)
        ).casefold()
        score = product.popularity / 100
        score += len(source_tags.intersection(product.tags)) * 2
        if source_category and product.category == source_category:
            score += 1.5
        score += sum(term in product_text for term in preference_terms) * 2
        ranked.append((score, product))

    ranked.sort(key=lambda result: (result[0], result[1].popularity), reverse=True)
    return [product for _, product in ranked[:limit]]


def recommend_products_with_gemini(
    *,
    product_id: str | None = None,
    category: str | None = None,
    preferences: list[str] | None = None,
    max_price: float | None = None,
    exclude_ids: list[str] | None = None,
    limit: int = 5,
    products: tuple[Product, ...] | list[Product] = PRODUCTS,
) -> list[Product]:
    candidates = recommend_products(
        product_id=product_id,
        category=category,
        preferences=preferences,
        max_price=max_price,
        exclude_ids=exclude_ids,
        limit=len(products),
        products=products,
    )
    if not candidates:
        return []

    response = generate_structured_response(
        json.dumps(
            {
                "product_id_to_similar_to": product_id,
                "category": category,
                "preferences": preferences or [],
                "max_price": max_price,
                "candidate_products": catalog_data(candidates),
            },
            ensure_ascii=True,
        ),
        GeminiRecommendationResponse,
        system_instruction=(
            "You are a retail product recommendation ranker. Return the best matching "
            "candidate product IDs in recommendation order. Only use IDs from "
            "candidate_products and respect the provided category, preferences, and "
            "max_price. Do not invent products or return the source product."
        ),
    )
    return select_catalog_products(response.product_ids, candidates, limit=limit)

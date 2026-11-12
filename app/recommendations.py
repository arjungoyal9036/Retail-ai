from app.catalog import PRODUCTS, PRODUCT_BY_ID, Product


def recommend_products(
    *,
    product_id: str | None = None,
    category: str | None = None,
    preferences: list[str] | None = None,
    max_price: float | None = None,
    exclude_ids: list[str] | None = None,
    limit: int = 5,
) -> list[Product]:
    """Rank the in-memory catalog by preference and product similarity."""
    excluded = set(exclude_ids or [])
    if product_id:
        excluded.add(product_id)

    source = PRODUCT_BY_ID.get(product_id) if product_id else None
    preference_terms = {
        term.casefold() for preference in (preferences or []) for term in preference.split()
    }
    source_tags = set(source.tags) if source else set()
    source_category = source.category if source else None
    requested_category = category.casefold() if category else None

    ranked: list[tuple[float, Product]] = []
    for product in PRODUCTS:
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

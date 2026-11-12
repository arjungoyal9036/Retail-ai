import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from pymongo import MongoClient

from app.catalog import PRODUCTS, product_as_dict, product_from_dict, search_products
from services.catalog.repository import CatalogRepository, MongoCatalogRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MongoClient(
        os.environ.get("MONGODB_URL", "mongodb://localhost:27017/retail_catalog"),
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
        database = client[os.environ.get("MONGODB_DATABASE", "retail_catalog")]
        repository = MongoCatalogRepository(database.products)
        repository.seed_if_missing(product_as_dict(product) for product in PRODUCTS)
        app.state.repository = repository
        yield
    finally:
        client.close()


app = FastAPI(title="Retail Catalog Service", lifespan=lifespan)


def get_repository(request: Request) -> CatalogRepository:
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="Catalog database is not ready.")
    return repository


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(request: Request) -> dict[str, str]:
    if getattr(request.app.state, "repository", None) is None:
        raise HTTPException(status_code=503, detail="Catalog database is not ready.")
    return {"status": "ready"}


@app.get("/api/v1/products")
def list_products(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=50),
    max_price: Annotated[float | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    repository = get_repository(request)
    products = [product_from_dict(item) for item in repository.list_products()]
    if query:
        products = search_products(query, limit=50, products=products)
    if category:
        products = [item for item in products if item.category.casefold() == category.casefold()]
    if max_price is not None:
        products = [item for item in products if item.price <= max_price]
    return {
        "items": [product_as_dict(item) for item in products[:limit]],
        "count": min(len(products), limit),
    }


@app.get("/api/v1/products/{product_id}")
def get_product(product_id: str, request: Request) -> dict[str, object]:
    product = get_repository(request).get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

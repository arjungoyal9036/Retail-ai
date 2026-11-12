from collections.abc import Iterable
from typing import Protocol

from pymongo.collection import Collection


class CatalogRepository(Protocol):
    def list_products(self) -> list[dict[str, object]]: ...

    def get_product(self, product_id: str) -> dict[str, object] | None: ...


class MongoCatalogRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._collection.create_index("id", unique=True)

    def seed_if_missing(self, products: Iterable[dict[str, object]]) -> None:
        for product in products:
            self._collection.update_one(
                {"id": product["id"]},
                {"$setOnInsert": product},
                upsert=True,
            )

    def list_products(self) -> list[dict[str, object]]:
        return [
            {key: value for key, value in document.items() if key != "_id"}
            for document in self._collection.find({}, {"_id": False}).sort("id", 1)
        ]

    def get_product(self, product_id: str) -> dict[str, object] | None:
        document = self._collection.find_one({"id": product_id}, {"_id": False})
        return document

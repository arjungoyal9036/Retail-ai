from fastapi.testclient import TestClient

from app.catalog import PRODUCTS, product_as_dict
from services.catalog.main import app as catalog_app
from services.customer.main import app as customer_app
from services.recommendation.main import app as recommendation_app
from services.chatbot.main import app as chatbot_app


class FakeCatalogRepository:
    def __init__(self) -> None:
        self.products = [product_as_dict(product) for product in PRODUCTS]

    def list_products(self) -> list[dict[str, object]]:
        return self.products

    def get_product(self, product_id: str) -> dict[str, object] | None:
        return next((product for product in self.products if product["id"] == product_id), None)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.profiles: dict[str, dict[str, object]] = {}

    def get_profile(self, customer_id: str) -> dict[str, object] | None:
        return self.profiles.get(customer_id)

    def save_profile(self, profile: dict[str, object]) -> dict[str, object]:
        self.profiles[str(profile["customer_id"])] = profile
        return profile


def test_catalog_service_reads_products_from_repository() -> None:
    catalog_app.state.repository = FakeCatalogRepository()
    response = TestClient(catalog_app).get(
        "/api/v1/products",
        params={"category": "home", "max_price": 60},
    )

    assert response.status_code == 200
    products = response.json()["items"]
    assert products
    assert all(product["category"] == "home" and product["price"] <= 60 for product in products)


def test_customer_service_persists_preferences_through_repository() -> None:
    customer_app.state.repository = FakeCustomerRepository()
    client = TestClient(customer_app)

    saved = client.put(
        "/api/v1/customers/customer-1",
        json={"preferences": ["travel", "home"]},
    )
    loaded = client.get("/api/v1/customers/customer-1")

    assert saved.status_code == 200
    assert loaded.json()["preferences"] == ["travel", "home"]


def test_recommendation_service_fetches_catalog_and_profile(monkeypatch) -> None:
    async def fake_request_json(base_url, method, path, *, params=None, json_body=None):
        if path == "/api/v1/products":
            return {"items": [product_as_dict(product) for product in PRODUCTS], "count": len(PRODUCTS)}
        if path == "/api/v1/customers/customer-1":
            return {"customer_id": "customer-1", "preferences": ["coffee"]}
        raise AssertionError(f"Unexpected downstream path: {path}")

    monkeypatch.setattr("services.recommendation.main.request_json", fake_request_json)
    response = TestClient(recommendation_app).get(
        "/api/v1/recommendations",
        params={"user_id": "customer-1", "max_price": 60, "limit": 10},
    )

    assert response.status_code == 200
    products = response.json()["items"]
    assert products
    assert all(product["price"] <= 60 for product in products)
    assert any("coffee" in product["tags"] for product in products)


def test_chatbot_service_uses_recommendation_service_without_gemini(monkeypatch) -> None:
    requested_paths = []
    recommendation_params = {}

    async def fake_request_json(base_url, method, path, *, params=None, json_body=None):
        requested_paths.append(path)
        if path == "/api/v1/products":
            return {"items": [product_as_dict(PRODUCTS[0])], "count": 1}
        if path == "/api/v1/recommendations":
            recommendation_params.update(params)
            return {"items": [product_as_dict(PRODUCTS[0])], "count": 1}
        raise AssertionError(f"Unexpected downstream path: {path}")

    monkeypatch.setattr("services.chatbot.main.request_json", fake_request_json)
    monkeypatch.setattr("services.chatbot.main.gemini_is_configured", lambda: False)
    response = TestClient(chatbot_app).post(
        "/api/v1/chat",
        json={"message": "I need a travel bag under 60"},
    )

    assert response.status_code == 200
    assert requested_paths == ["/api/v1/products", "/api/v1/recommendations"]
    assert recommendation_params["category"] == "bags"
    assert recommendation_params["max_price"] == 60
    assert response.json()["recommendations"][0]["id"] == "p-1001"


def test_mongo_catalog_repository_seeds_and_reads_by_product_id() -> None:
    from services.catalog.repository import MongoCatalogRepository

    class Cursor(list):
        def sort(self, key: str, direction: int):
            return Cursor(sorted(self, key=lambda item: item[key], reverse=direction < 0))

    class Collection:
        def __init__(self):
            self.documents = {}

        def create_index(self, key, unique):
            assert unique

        def update_one(self, query, update, upsert):
            self.documents.setdefault(query["id"], update["$setOnInsert"])

        def find(self, query, projection):
            return Cursor(self.documents.values())

        def find_one(self, query, projection):
            return self.documents.get(query["id"])

    collection = Collection()
    repository = MongoCatalogRepository(collection)
    products = [product_as_dict(PRODUCTS[0])]

    repository.seed_if_missing(products)
    repository.seed_if_missing(products)

    assert repository.get_product("p-1001")["name"] == PRODUCTS[0].name
    assert repository.list_products() == products


def test_mongo_profile_repository_saves_and_reads_customer_preferences() -> None:
    from services.customer.repository import MongoProfileRepository

    class Collection:
        def __init__(self):
            self.profiles = {}

        def create_index(self, key, unique):
            assert key == "customer_id"
            assert unique

        def replace_one(self, query, profile, upsert):
            assert upsert
            self.profiles[query["customer_id"]] = profile

        def find_one(self, query, projection):
            return self.profiles.get(query["customer_id"])

    repository = MongoProfileRepository(Collection())
    profile = {"customer_id": "customer-1", "preferences": ["travel"]}

    repository.save_profile(profile)

    assert repository.get_profile("customer-1") == profile

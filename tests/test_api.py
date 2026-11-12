from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_product_listing_supports_category_and_price_filters() -> None:
    response = client.get("/api/v1/products", params={"category": "home", "max_price": 60})

    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["category"] == "home" and item["price"] <= 60 for item in items)


def test_recommendations_exclude_source_and_respect_budget() -> None:
    response = client.get(
        "/api/v1/recommendations",
        params={"product_id": "p-1001", "max_price": 60, "limit": 10},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["id"] != "p-1001" and item["price"] <= 60 for item in items)


def test_recommendations_return_not_found_for_unknown_product() -> None:
    response = client.get("/api/v1/recommendations", params={"product_id": "missing"})

    assert response.status_code == 404


def test_chat_recommends_items_for_budget_request() -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "Recommend something for travel under 60", "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"]
    assert payload["recommendations"]
    assert all(item["price"] <= 60 for item in payload["recommendations"])


def test_chat_understands_a_casual_product_request() -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "I need a travel bag under 100"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert all(item["category"] == "bags" and item["price"] <= 100 for item in payload["recommendations"])


def test_chat_rejects_empty_message() -> None:
    response = client.post("/api/v1/chat", json={"message": ""})

    assert response.status_code == 422


def test_health_endpoints() -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}

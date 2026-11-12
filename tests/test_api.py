from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage_serves_retail_web_interface() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "field&amp;form" in response.text or "field&form" in response.text
    assert "/api/v1/products" in response.text


def test_gateway_proxies_product_filters(monkeypatch) -> None:
    captured = {}

    async def fake_request_json(base_url, method, path, *, params=None, json_body=None):
        captured.update(base_url=base_url, method=method, path=path, params=params)
        return {"items": [], "count": 0}

    monkeypatch.setattr("app.main.request_json", fake_request_json)
    response = client.get(
        "/api/v1/products",
        params={"query": "coffee", "category": "home", "max_price": 60},
    )

    assert response.status_code == 200
    assert captured["path"] == "/api/v1/products"
    assert captured["params"]["category"] == "home"
    assert captured["params"]["max_price"] == 60


def test_gateway_proxies_chat_body(monkeypatch) -> None:
    captured = {}

    async def fake_request_json(base_url, method, path, *, params=None, json_body=None):
        captured.update(base_url=base_url, method=method, path=path, json_body=json_body)
        return {"reply": "Hello!", "recommendations": []}

    monkeypatch.setattr("app.main.request_json", fake_request_json)
    response = client.post(
        "/api/v1/chat",
        json={"message": "I need a travel bag", "user_id": "customer-1"},
    )

    assert response.status_code == 200
    assert captured["json_body"]["user_id"] == "customer-1"
    assert captured["json_body"]["message"] == "I need a travel bag"


def test_health_endpoints(monkeypatch) -> None:
    async def fake_request_json(*args, **kwargs):
        return {"status": "ready"}

    monkeypatch.setattr("app.main.request_json", fake_request_json)
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}

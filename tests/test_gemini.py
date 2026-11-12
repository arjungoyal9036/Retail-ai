from types import SimpleNamespace

import pytest
from google.genai import errors

from app import gemini
from app.gemini import GeminiChatResponse, GeminiServiceError


def test_generate_structured_response_uses_configured_model_and_schema(monkeypatch) -> None:
    call = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            call.update(kwargs)
            return SimpleNamespace(
                parsed={"reply": "Here is an option.", "product_ids": ["p-1001"]},
                text=None,
            )

    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(gemini, "_get_client", lambda api_key: SimpleNamespace(models=FakeModels()))

    result = gemini.generate_structured_response(
        '{"customer_message":"find a bag"}',
        GeminiChatResponse,
        system_instruction="Only use the supplied products.",
    )

    assert result == GeminiChatResponse(reply="Here is an option.", product_ids=["p-1001"])
    assert call["model"] == "test-model"
    assert call["config"].response_schema is GeminiChatResponse
    assert call["config"].response_mime_type == "application/json"


def test_generate_structured_response_reports_api_status_without_leaking_key(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            raise errors.APIError(429, {"error": {"message": "quota"}})

    monkeypatch.setenv("GEMINI_API_KEY", "do-not-leak-this")
    monkeypatch.setattr(gemini, "_get_client", lambda api_key: SimpleNamespace(models=FakeModels()))

    with pytest.raises(GeminiServiceError, match="HTTP 429") as error:
        gemini.generate_structured_response(
            "{}",
            GeminiChatResponse,
            system_instruction="Use only supplied products.",
        )

    assert "do-not-leak-this" not in str(error.value)


def test_generate_structured_response_sanitizes_malformed_sdk_errors(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            raise ValueError("malformed provider payload")

    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(gemini, "_get_client", lambda api_key: SimpleNamespace(models=FakeModels()))

    with pytest.raises(GeminiServiceError, match="Gemini API request failed"):
        gemini.generate_structured_response(
            "{}",
            GeminiChatResponse,
            system_instruction="Use only supplied products.",
        )


def test_generate_structured_response_rejects_malformed_response(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(parsed=None, text="not json")

    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(gemini, "_get_client", lambda api_key: SimpleNamespace(models=FakeModels()))

    with pytest.raises(GeminiServiceError, match="invalid response"):
        gemini.generate_structured_response(
            "{}",
            GeminiChatResponse,
            system_instruction="Use only supplied products.",
        )

"""Unit tests for graphrag_service provider resolution."""

import os


def test_resolve_provider_kwargs_prefers_azure(monkeypatch):
    from app.services.graphrag_service import resolve_provider_kwargs
    from app.config import settings

    # Ensure settings don't override env
    monkeypatch.setattr(settings, "ngr_use_gemini", None, raising=False)
    monkeypatch.setattr(settings, "ngr_use_azure_openai", None, raising=False)

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "e")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert resolve_provider_kwargs() == {"using_azure_openai": True}


def test_resolve_provider_kwargs_uses_gemini(monkeypatch):
    from app.services.graphrag_service import resolve_provider_kwargs
    from app.config import settings

    monkeypatch.setattr(settings, "ngr_use_gemini", None, raising=False)
    monkeypatch.setattr(settings, "ngr_use_azure_openai", None, raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)

    monkeypatch.setenv("GEMINI_API_KEY", "k")

    assert resolve_provider_kwargs() == {"using_gemini": True}


def test_resolve_provider_kwargs_defaults_to_openai(monkeypatch):
    from app.services.graphrag_service import resolve_provider_kwargs
    from app.config import settings

    monkeypatch.setattr(settings, "ngr_use_gemini", None, raising=False)
    monkeypatch.setattr(settings, "ngr_use_azure_openai", None, raising=False)

    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert resolve_provider_kwargs() == {}

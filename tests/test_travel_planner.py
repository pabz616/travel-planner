import pytest
import importlib
import json
import sys
from pathlib import Path

# TODO REFACTOR THIS TEST FILE TO USE PYTEST FIXTURES AND PARAMETRIZATION

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_data.payload import payload


class FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload)


class FakeModels:
    def __init__(self, payload):
        self.payload = payload

    def generate_content(self, model, contents):
        return FakeResponse(self.payload)


class DiscoverableFakeModel:
    def __init__(self, name, supported_actions=None):
        self.name = name
        self.supported_actions = supported_actions


class DiscoverableFakeModels(FakeModels):
    def __init__(self, payload, available_models):
        super().__init__(payload)
        self.available_models = available_models
        self.requested_models = []

    def list(self):
        return self.available_models

    def generate_content(self, model, contents):
        self.requested_models.append(model)
        return super().generate_content(model, contents)


class FakeClient:
    def __init__(self, payload):
        self.models = FakeModels(payload)


def load_planner():
    sys.modules.pop("travel_planner", None)
    return importlib.import_module("travel_planner")

# TODO ADD MORE TESTS FOR THE TRAVEL PLANNER MODULE


def test_create_travel_plan_returns_json(monkeypatch):
    planner = load_planner()
    monkeypatch.setattr(planner, "client", FakeClient(payload))

    result = planner.create_travel_plan("France", 3, 1500, "food")

    assert result["country"] == "France"
    assert result["budget"]["total"] == "$1000"


def test_create_travel_plan_rejects_negative_days(monkeypatch):
    planner = load_planner()

    monkeypatch.setattr(planner, "client", FakeClient(payload))

    with pytest.raises(ValueError, match="positive"):
        planner.create_travel_plan("France", -3, 2000, "food")


def test_create_travel_plan_rejects_unsupported_models(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "unsupported-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "also-unsupported")
    monkeypatch.setattr(
        planner,
        "client",
        FakeClient(payload),
    )
    planner.client.models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel("gemini-2.5-flash", ["generateContent"]),
    ])

    with pytest.raises(planner.ModelAvailabilityError, match="None of the configured"):
        planner.create_travel_plan("France", 3, 1500, "food")


def test_create_travel_plan_uses_available_fallback(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "unsupported-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
    models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel("models/gemini-2.5-flash", ["generateContent"]),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)

    result = planner.create_travel_plan("France", 3, 1500, "food")

    assert result["country"] == "France"
    assert models.requested_models == ["gemini-2.5-flash"]


def test_get_place_image_returns_none_when_no_thumbnail_exists(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def json(self):
            return {"query": {"pages": {"123": {"title": "Paris"}}}}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert planner.get_place_image("Paris", "France") is None


def test_validate_travel_plan_rejects_missing_required_field():
    planner = load_planner()

    with pytest.raises(planner.PlanValidationError, match="missing required field 'overview'"):
        planner.validate_travel_plan({
            "country": "France",
            "famous_places": [],
            "itinerary": [],
            "food": [],
            "budget": {},
            "tips": [],
        })


def test_get_place_image_handles_http_errors(monkeypatch):
    planner = load_planner()

    def raise_error(*args, **kwargs):
        raise OSError("forced network failure")

    monkeypatch.setattr(planner.requests, "get", raise_error)

    assert planner.get_place_image("Paris", "France") is None

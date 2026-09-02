import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload)


class FakeModels:
    def __init__(self, payload):
        self.payload = payload

    def generate_content(self, model, contents):
        return FakeResponse(self.payload)


class FakeClient:
    def __init__(self, payload):
        self.models = FakeModels(payload)


def load_planner():
    sys.modules.pop("planner", None)
    return importlib.import_module("planner")


def test_create_travel_plan_returns_json(monkeypatch):
    planner = load_planner()
    payload = {
        "country": "France",
        "overview": "A classic trip.",
        "famous_places": [],
        "itinerary": [],
        "food": [],
        "budget": {"total": "$1200"},
        "tips": [],
    }
    monkeypatch.setattr(planner, "client", FakeClient(payload))

    result = planner.create_travel_plan("France", 3, 1500, "food")

    assert result["country"] == "France"
    assert result["budget"]["total"] == "$1200"


@pytest.mark.xfail(reason="Current planner does not validate invalid day counts before calling the API.", strict=True)
def test_create_travel_plan_rejects_negative_days(monkeypatch):
    planner = load_planner()
    payload = {
        "country": "France",
        "overview": "A classic trip.",
        "famous_places": [],
        "itinerary": [],
        "food": [],
        "budget": {"total": "$1200"},
        "tips": [],
    }
    monkeypatch.setattr(planner, "client", FakeClient(payload))

    with pytest.raises(ValueError, match="positive"):
        planner.create_travel_plan("France", -3, 2000, "food")


def test_get_place_image_returns_none_when_no_thumbnail_exists(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def json(self):
            return {"query": {"pages": {"123": {"title": "Paris"}}}}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert planner.get_place_image("Paris", "France") is None


def test_get_place_image_handles_http_errors(monkeypatch):
    planner = load_planner()

    def raise_error(*args, **kwargs):
        raise OSError("forced network failure")

    monkeypatch.setattr(planner.requests, "get", raise_error)

    assert planner.get_place_image("Paris", "France") is None

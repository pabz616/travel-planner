import builtins
import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



def load_planner(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    sys.modules.pop("planner", None)
    return importlib.import_module("planner")


def test_import_does_not_trigger_cli(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")

    original_input = builtins.input

    def fail_input(*args, **kwargs):
        raise AssertionError("input() should not run during import")

    monkeypatch.setattr(builtins, "input", fail_input)
    sys.modules.pop("planner", None)

    planner = importlib.import_module("planner")

    monkeypatch.setattr(builtins, "input", original_input)
    assert hasattr(planner, "create_travel_plan")


def test_validate_plan_input_rejects_invalid_values(monkeypatch):
    planner = load_planner(monkeypatch)

    with pytest.raises(ValueError, match="positive integer"):
        planner.validate_plan_input("France", 0, 1000, "food")

    with pytest.raises(ValueError, match="positive"):
        planner.validate_plan_input("France", 5, -1, "food")


def test_parse_response_text_strips_markdown_and_parses_json(monkeypatch):
    planner = load_planner(monkeypatch)

    payload = {
        "country": "France",
        "overview": "A charming trip.",
        "famous_places": [],
        "itinerary": [],
        "food": [],
        "budget": {"total": "$1200"},
        "tips": []
    }
    raw = "```json\n" + json.dumps(payload) + "\n```"

    assert planner.parse_response_text(raw) == payload


def test_build_interactive_map_adds_markers(monkeypatch):
    planner = load_planner(monkeypatch)

    places = [
        {
            "name": "Paris",
            "description": "A major city.",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "best_time": "Spring",
            "cost": "$100",
            "activities": ["Museum"],
        }
    ]

    travel_map = planner.build_interactive_map(places)

    assert travel_map is not None
    assert len(travel_map._children) > 0

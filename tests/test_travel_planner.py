import pytest
import importlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

test_data = importlib.import_module("test_data.data")
FALLBACK_MODEL = test_data.FALLBACK_MODEL
COUNTRY = test_data.COUNTRY
DAYS = test_data.DAYS
BUDGET = test_data.BUDGET
INTERESTS = test_data.INTERESTS
payload = importlib.import_module("test_data.payload").payload


class FakeResponse:
    def __init__(self, payload, parsed=None):
        self.text = json.dumps(payload)
        self.parsed = parsed

    def raise_for_status(self):
        pass


class FakeModels:
    def __init__(self, payload):
        self.payload = payload

    def generate_content(self, model, contents, config=None):
        return FakeResponse(self.payload)


class ParsedFakeModels(FakeModels):
    def __init__(self, payload, parsed):
        super().__init__(payload)
        self.parsed = parsed

    def generate_content(self, model, contents, config=None):
        return FakeResponse(self.payload, parsed=self.parsed)


class SequencedFakeModels(FakeModels):
    def __init__(self, responses):
        super().__init__({})
        self.responses = iter(responses)
        self.calls = []

    def generate_content(self, model, contents, config=None):
        self.calls.append(model)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


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

    def generate_content(self, model, contents, config=None):
        self.requested_models.append(model)
        return super().generate_content(model, contents, config=config)


class FakeClient:
    def __init__(self, payload):
        self.models = FakeModels(payload)


def load_planner():
    sys.modules.pop("travel_planner", None)
    return importlib.import_module("travel_planner")


# TESTS FOR MODEL SELECTION AND FALLBACK BEHAVIOR
def test_create_travel_plan_rejects_unsupported_models(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "unsupported-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "also-unsupported")
    monkeypatch.setattr(planner, "client", FakeClient(payload),)
    planner.client.models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel(FALLBACK_MODEL, ["generateContent"]),
    ])

    with pytest.raises(planner.ModelAvailabilityError, match="None of the configured"):
        planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)


def test_create_travel_plan_uses_available_fallback(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "unsupported-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", FALLBACK_MODEL)
    models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel(FALLBACK_MODEL, ["generateContent"]),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert result.country == COUNTRY
    assert models.requested_models == [FALLBACK_MODEL]


def test_create_travel_plan_returns_json(monkeypatch):
    planner = load_planner()
    monkeypatch.setattr(planner, "client", FakeClient(payload))

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert isinstance(result, planner.TravelPlan)
    assert result.country == COUNTRY
    assert result.budget.total == f"${BUDGET:,}"


def test_create_travel_plan_returns_sdk_parsed_plan(monkeypatch):
    planner = load_planner()
    parsed_plan = planner.TravelPlan.model_validate(payload)
    client = FakeClient(payload)
    client.models = ParsedFakeModels({}, parsed_plan)
    monkeypatch.setattr(planner, "client", client)

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert result is parsed_plan


@pytest.mark.parametrize("itinerary_length", [2, 4])
def test_create_travel_plan_rejects_wrong_itinerary_length(monkeypatch, itinerary_length):
    planner = load_planner()
    itinerary = payload["itinerary"][:itinerary_length]
    if itinerary_length > len(payload["itinerary"]):
        itinerary.append(dict(payload["itinerary"][-1], day=itinerary_length))
    response_payload = dict(payload, itinerary=itinerary)
    client = FakeClient(response_payload)
    monkeypatch.setattr(planner, "client", client)

    with pytest.raises(planner.TravelPlanGenerationError) as error:
        planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert f"Expected {DAYS} itinerary days" in str(error.value.__cause__)


def test_itinerary_length_validator_accepts_requested_day_count():
    planner = load_planner()
    plan = planner.TravelPlan.model_validate(payload)

    assert planner._validate_itinerary_length(plan, DAYS) is plan


def test_create_travel_plan_prompt_does_not_include_api_key(monkeypatch):
    planner = load_planner()
    secret = "test-secret-api-key"
    captured = {}

    class PromptCapturingModels(FakeModels):
        def generate_content(self, model, contents, config=None):
            captured["prompt"] = contents
            return super().generate_content(model, contents, config=config)

    client = FakeClient(payload)
    client.models = PromptCapturingModels(payload)
    monkeypatch.setattr(planner, "client", client)
    monkeypatch.setattr(planner, "API_KEY", secret)

    planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert secret not in captured["prompt"]


def test_model_discovery_ignores_models_without_generation_support(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "supported")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "fallback")
    models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel("supported", ["embedContent"]),
        DiscoverableFakeModel("fallback", ["generate_content"]),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert result.country == COUNTRY
    assert models.requested_models == ["fallback"]


def test_model_discovery_is_cached_for_process_lifetime(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", FALLBACK_MODEL)
    models = DiscoverableFakeModels(payload, [
        DiscoverableFakeModel(FALLBACK_MODEL, ["generateContent"]),
    ])
    list_calls = 0

    def list_models():
        nonlocal list_calls
        list_calls += 1
        return models.available_models

    models.list = list_models
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)

    planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)
    planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert list_calls == 1


def test_create_travel_plan_wraps_model_listing_failure(monkeypatch):
    planner = load_planner()
    client = FakeClient(payload)

    def fail_to_list():
        raise planner.requests.RequestException("network unavailable")

    client.models.list = fail_to_list
    monkeypatch.setattr(planner, "client", client)

    with pytest.raises(planner.ModelAvailabilityError, match="Unable to check Gemini model availability"):
        planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)


def test_create_travel_plan_retries_retryable_failure(monkeypatch):
    planner = load_planner()
    models = SequencedFakeModels([
        RuntimeError("503 service unavailable"),
        FakeResponse(payload),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)
    monkeypatch.setattr(planner.time, "sleep", lambda _: None)

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert result.country == COUNTRY
    assert len(models.calls) == 2


def test_create_travel_plan_stops_after_retry_exhaustion(monkeypatch):
    planner = load_planner()
    models = SequencedFakeModels([
        RuntimeError("503 service unavailable"),
        RuntimeError("503 service unavailable"),
        RuntimeError("503 service unavailable"),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)
    monkeypatch.setattr(planner, "_available_configured_models", lambda: ("primary",))
    sleeps = []
    monkeypatch.setattr(planner.time, "sleep", sleeps.append)

    with pytest.raises(planner.TravelPlanGenerationError):
        planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert models.calls == ["primary"] * planner.MAX_ATTEMPTS_PER_MODEL
    assert sleeps == [planner.RETRY_DELAY_SECONDS] * (planner.MAX_ATTEMPTS_PER_MODEL - 1)


def test_create_travel_plan_does_not_retry_nonretryable_failure(monkeypatch):
    planner = load_planner()
    models = SequencedFakeModels([RuntimeError("invalid request")])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)

    with pytest.raises(planner.TravelPlanGenerationError):
        planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert models.calls == [test_data.CURRENT_MODEL, FALLBACK_MODEL]


def test_create_travel_plan_uses_next_model_after_schema_failure(monkeypatch):
    planner = load_planner()
    monkeypatch.setenv("GEMINI_MODEL", "primary")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "fallback")
    models = SequencedFakeModels([
        FakeResponse({"invalid": True}),
        FakeResponse(payload),
    ])
    client = FakeClient(payload)
    client.models = models
    monkeypatch.setattr(planner, "client", client)
    monkeypatch.setattr(
        planner,
        "_available_configured_models",
        lambda: ("primary", "fallback"),
    )

    result = planner.create_travel_plan(COUNTRY, DAYS, BUDGET, INTERESTS)

    assert result.country == COUNTRY
    assert models.calls == ["primary", "fallback"]


# TESTS FOR COUNTRY INPUT VALIDATION
def test_create_travel_plan_validate_country_exists(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"name": "France", "country": "France"}]}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    planner._validate_country_exists("France")


def test_create_travel_plan_validate_country_accepts_territory_name(monkeypatch):
    planner = load_planner()

    monkeypatch.setattr(
        planner.requests,
        "get",
        lambda *args, **kwargs: pytest.fail("Known countries should use the local list"),
    )

    planner._validate_country_exists("Puerto Rico")


def test_create_travel_plan_validate_country_rejects_unknown_country(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(planner.InputValidationError, match="was not found"):
        planner._validate_country_exists("Atlantis")


def test_create_travel_plan_validate_country_rejects_empty_value():
    planner = load_planner()

    with pytest.raises(planner.InputValidationError, match="Please enter a valid country name"):
        planner._validate_text_input("", "country name", 50)


def test_create_travel_plan_validate_country_rejects_values_over_max_length():
    planner = load_planner()
    with pytest.raises(planner.InputValidationError, match="Country Name must be 50 characters or fewer"):
        planner._validate_text_input("F" * 51, "country name", 50)


def test_create_travel_plan_validate_country_rejects_illegal_characters():
    planner = load_planner()

    with pytest.raises(planner.InputValidationError, match="Country Name must contain letters and common separators only"):
        planner._validate_text_input("<h1>", "country name", 50)


def test_create_travel_plan_validate_country_accepts_quoted_alias():
    planner = load_planner()

    planner._validate_text_input('Eswatini (fmr. "Swaziland")', "country name", 50)


@pytest.mark.parametrize("value", ["line\nfeed", "null\x00byte", "\x1b[31mred"])
def test_create_travel_plan_validate_country_rejects_control_characters(value):
    planner = load_planner()

    with pytest.raises(planner.InputValidationError):
        planner._validate_text_input(value, "country name", 50)


def test_create_travel_plan_validate_country_accepts_supported_separators_and_unicode_letters():
    planner = load_planner()

    planner._validate_text_input("Côte d'Ivoire (West)", "country name", 50)


def test_create_travel_plan_validate_country_accepts_exact_maximum_length():
    planner = load_planner()

    planner._validate_text_input("A" * 50, "country name", 50)


def test_create_travel_plan_validate_days_accepts_positive_digits():
    planner = load_planner()

    planner._validate_numeric_input("7", "number of days", 2)


def test_create_travel_plan_validate_days_accepts_365_days():
    planner = load_planner()

    planner._validate_numeric_input("365", "number of days", 3)


@pytest.mark.parametrize("value, expected_message", [
    ("", "Please enter a valid number of days"),
    ("0", "Please enter a positive number of days"),
    ("-3", "Number Of Days must contain digits only"),
    ("not-a-number", "Number Of Days must contain 2 digits or fewer"),
])
def test_create_travel_plan_validate_days_rejects_invalid_values(value, expected_message):
    planner = load_planner()

    with pytest.raises(planner.InputValidationError, match=expected_message):
        planner._validate_numeric_input(value, "number of days", 2)


def test_create_travel_plan_validate_budget_rejects_values_over_max_length():
    planner = load_planner()

    with pytest.raises(planner.InputValidationError, match="Budget must contain 6 digits or fewer"):
        planner._validate_numeric_input("1000000", "budget", 6)


def test_create_travel_plan_validate_budget_accepts_exact_maximum_length():
    planner = load_planner()
    planner._validate_numeric_input("999999", "budget", 6)


# TESTS FOR DAYS INPUT
@pytest.mark.parametrize("days", [0, -3])
def test_create_travel_plan_rejects_nonpositive_days(monkeypatch, days):
    planner = load_planner()
    monkeypatch.setattr(planner, "client", FakeClient(payload))

    with pytest.raises(ValueError, match="positive"):
        planner.create_travel_plan(COUNTRY, days, BUDGET, INTERESTS)


# TESTS FOR BUDGET CONSISTENCY
def test_create_travel_plan_check_budget_consistency_returns_no_warnings_for_consistent_budget():
    planner = load_planner()
    plan = planner.TravelPlan.model_validate(payload)

    assert planner.check_budget_consistency(plan, BUDGET) == []


def test_create_travel_plan_check_budget_consistency_reports_line_item_mismatch():
    planner = load_planner()
    plan_data = dict(payload)
    plan_data["budget"] = dict(payload["budget"], total="$900")
    plan = planner.TravelPlan.model_validate(plan_data)

    warnings = planner.check_budget_consistency(plan, 1500)

    assert len(warnings) == 1
    assert f"line items sum to ${BUDGET:,.2f}" in warnings[0]


def test_create_travel_plan_check_budget_consistency_reports_total_over_stated_budget():
    planner = load_planner()
    plan = planner.TravelPlan.model_validate(payload)

    stated_budget = BUDGET - 1
    warnings = planner.check_budget_consistency(plan, stated_budget)

    assert warnings == [
        f"The plan's total (${BUDGET:,}) exceeds your stated budget (${stated_budget:,.2f})."
    ]


def test_create_travel_plan_check_budget_consistency_reports_unparseable_amount():
    planner = load_planner()
    plan_data = dict(payload)
    plan_data["budget"] = dict(payload["budget"], food="unknown")
    plan = planner.TravelPlan.model_validate(plan_data)

    assert planner.check_budget_consistency(plan, 1500) == [
        "Could not parse one or more budget figures for a consistency check."
    ]


# TESTS FOR GENERATED PLAN: RESPONSE
def test_travel_plan_generated_rejects_missing_required_field():
    planner = load_planner()

    with pytest.raises(planner.ValidationError):
        planner.TravelPlan.model_validate({
            "country": "France",
            "famous_places": [],
            "itinerary": [],
            "food": [],
            "budget": {},
            "tips": [],
        })


@pytest.mark.parametrize("field, value", [
    ("latitude", 91),
    ("longitude", 181),
])
def test_create_travel_plan_rejects_out_of_range_coordinates(field, value):
    planner = load_planner()
    place = dict(payload["famous_places"][0], **{field: value})
    plan_data = dict(payload, famous_places=[place, *payload["famous_places"][1:]])

    with pytest.raises(planner.ValidationError):
        planner.TravelPlan.model_validate(plan_data)


@pytest.mark.parametrize("rating", [-0.1, 5.1])
def test_create_travel_plan_rejects_out_of_range_food_rating(rating):
    planner = load_planner()
    food = dict(payload["food"][0], rating=rating)
    plan_data = dict(payload, food=[food])

    with pytest.raises(planner.ValidationError):
        planner.TravelPlan.model_validate(plan_data)


# TESTS FOR GENERATED PLAN: MAP ELEMENT
def test_create_travel_plan_get_place_image_returns_none_when_no_thumbnail_exists(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def json(self):
            return {"query": {"pages": {"123": {"title": "Paris"}}}}

        def raise_for_status(self):
            pass

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert planner.get_place_image("Paris", "France") is None


def test_create_travel_plan_get_place_image_handles_http_errors(monkeypatch):
    planner = load_planner()

    def raise_error(*args, **kwargs):
        raise planner.requests.RequestException("forced network failure")

    monkeypatch.setattr(planner.requests, "get", raise_error)

    assert planner.get_place_image("Paris", "France") is None


def test_create_travel_plan_get_place_image_returns_thumbnail_url(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"query": {"pages": {"123": {
                "thumbnail": {"source": "https://example.com/paris.jpg"},
            }}}}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert planner.get_place_image("Paris", "France") == "https://example.com/paris.jpg"


def test_get_place_image_uses_https_and_timeout(monkeypatch):
    planner = load_planner()
    request = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"query": {"pages": {}}}

    def fake_get(url, **kwargs):
        request["url"] = url
        request["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(planner.requests, "get", fake_get)

    planner.get_place_image("Paris", "France")

    assert request["url"].startswith("https://")
    assert request["kwargs"]["timeout"] == 10


def test_create_travel_plan_get_place_image_handles_malformed_response(monkeypatch):
    planner = load_planner()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"query": {"pages": {"123": {"thumbnail": {}}}}}

    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert planner.get_place_image("Paris", "France") is None


# TESTS FOR GENERATED PLAN: WEATHER ELEMENT
def test_create_travel_plan_get_location_weather_returns_local_time_and_temperature(monkeypatch):
    planner = load_planner()
    responses = iter([
        FakeJsonResponse({"results": [{"latitude": 48.8566, "longitude": 2.3522}]}),
        FakeJsonResponse({
            "timezone": "Europe/Paris",
            "current": {
                "time": "2026-09-03T14:30",
                "temperature_2m": 22.4,
                "weather_code": 1,
            },
        }),
    ])
    requests = []

    def fake_get(url, **kwargs):
        requests.append((url, kwargs["params"]))
        return next(responses)

    monkeypatch.setattr(planner.requests, "get", fake_get)

    assert planner.get_location_weather("France") == {
        "local_time": "2026-09-03 14:30",
        "temperature_c": 22.4,
        "weather_code": 1,
        "timezone": "Europe/Paris",
    }
    assert requests[0][1]["name"] == "France"
    assert requests[1][1]["latitude"] == 48.8566


def test_create_travel_plan_get_location_weather_returns_none_when_location_is_not_found(monkeypatch):
    planner = load_planner()
    monkeypatch.setattr(
        planner.requests,
        "get",
        lambda *args, **kwargs: FakeJsonResponse({"results": []}),
    )

    assert planner.get_location_weather("Unknown location") is None


def test_create_travel_plan_get_location_weather_returns_none_on_request_failure(monkeypatch):
    planner = load_planner()

    def fail_to_get(*args, **kwargs):
        raise planner.requests.Timeout("weather timeout")

    monkeypatch.setattr(planner.requests, "get", fail_to_get)

    assert planner.get_location_weather("France") is None


def test_create_travel_plan_get_location_weather_returns_none_on_incomplete_forecast(monkeypatch):
    planner = load_planner()
    responses = iter([
        FakeJsonResponse({"results": [{"latitude": 48.8566, "longitude": 2.3522}]}),
        FakeJsonResponse({"current": {"time": "2026-09-03T14:30"}}),
    ])
    monkeypatch.setattr(planner.requests, "get", lambda *args, **kwargs: next(responses))

    assert planner.get_location_weather("France") is None


def test_create_travel_plan_get_location_weather_returns_none_when_forecast_request_fails(monkeypatch):
    planner = load_planner()
    geocoding_response = FakeJsonResponse(
        {"results": [{"latitude": 48.8566, "longitude": 2.3522}]}
    )
    first_request = True

    def fake_get(*args, **kwargs):
        nonlocal first_request
        if first_request:
            first_request = False
            return geocoding_response
        raise planner.requests.RequestException("forecast unavailable")

    monkeypatch.setattr(planner.requests, "get", fake_get)

    assert planner.get_location_weather("France") is None


def test_create_travel_plan_get_location_weather_uses_https_and_timeouts(monkeypatch):
    planner = load_planner()
    requests = []
    responses = iter([
        FakeJsonResponse({"results": [{"latitude": 48.8566, "longitude": 2.3522}]}),
        FakeJsonResponse({
            "timezone": "Europe/Paris",
            "current": {"time": "2026-09-03T14:30", "temperature_2m": 22.4, "weather_code": 1},
        }),
    ])

    def fake_get(url, **kwargs):
        requests.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr(planner.requests, "get", fake_get)

    planner.get_location_weather("France")

    assert all(url.startswith("https://") for url, _ in requests)
    assert all(kwargs["timeout"] == 10 for _, kwargs in requests)


class FakeJsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


def test_create_travel_plan_adds_weather_to_prompt(monkeypatch):
    planner = load_planner()
    captured = {}

    class PromptCapturingModels(FakeModels):
        def generate_content(self, model, contents, config=None):
            captured["prompt"] = contents
            return super().generate_content(model, contents, config=config)

    client = FakeClient(payload)
    client.models = PromptCapturingModels(payload)
    monkeypatch.setattr(planner, "client", client)

    planner.create_travel_plan(
        COUNTRY,
        DAYS,
        BUDGET,
        INTERESTS,
        {
            "local_time": "2026-09-03 14:30",
            "temperature_c": 22.4,
            "weather_code": 1,
            "timezone": "Europe/Paris",
        },
    )

    assert "Local time: 2026-09-03 14:30" in captured["prompt"]
    assert "temperature: 22.4 °C" in captured["prompt"]


def test_create_travel_plan_build_map_escapes_model_generated_html(tmp_path):
    planner = load_planner()
    plan_data = dict(payload)
    plan_data["famous_places"] = [dict(place) for place in payload["famous_places"]]
    plan_data["famous_places"][0] = dict(
        plan_data["famous_places"][0],
        name="<script>alert('xss')</script>",
        description="<img src=x onerror=alert(1)>",
        best_time="<svg onload=alert(1)>",
        cost="<iframe src=evil>",
        activities=["<b>unsafe</b>"],
    )
    plan = planner.TravelPlan.model_validate(plan_data)
    output_path = tmp_path / "travel_map.html"

    assert planner.build_map(plan, str(output_path)) == str(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "&lt;svg onload=alert(1)&gt;" in html
    assert "&lt;iframe src=evil&gt;" in html
    assert "<script>alert('xss')</script>" not in html


def test_create_travel_plan_build_map_propagates_output_write_failure(tmp_path):
    planner = load_planner()
    plan = planner.TravelPlan.model_validate(payload)
    output_path = tmp_path / "missing-directory" / "travel_map.html"

    with pytest.raises(OSError):
        planner.build_map(plan, str(output_path))


def test_main_returns_cleanly_for_invalid_input(monkeypatch, capsys):
    planner = load_planner()
    monkeypatch.setattr("builtins.input", lambda _: "")

    planner.main()

    assert "Please enter a valid country name" in capsys.readouterr().out


def test_main_continues_when_weather_is_unavailable(monkeypatch, capsys):
    planner = load_planner()
    answers = iter([COUNTRY, str(DAYS), str(BUDGET), INTERESTS])
    received = {}
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(planner, "_validate_country_exists", lambda _: None)
    monkeypatch.setattr(planner, "get_location_weather", lambda _: None)

    def fake_create(country, days, budget, interests, weather):
        received["weather"] = weather
        return planner.TravelPlan.model_validate(payload)

    monkeypatch.setattr(planner, "create_travel_plan", fake_create)
    monkeypatch.setattr(planner, "get_place_image", lambda *_: None)
    monkeypatch.setattr(planner, "build_map", lambda _: "travel_map.html")

    planner.main()

    output = capsys.readouterr().out
    assert received["weather"] is None
    assert "Weather data is currently unavailable." in output
    assert "TRAVEL PLAN COMPLETE" in output


def test_main_reports_generation_failure_without_traceback(monkeypatch, capsys):
    planner = load_planner()
    answers = iter([COUNTRY, str(DAYS), str(BUDGET), INTERESTS])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(planner, "_validate_country_exists", lambda _: None)
    monkeypatch.setattr(planner, "get_location_weather", lambda _: None)
    monkeypatch.setattr(
        planner,
        "create_travel_plan",
        lambda *args: (_ for _ in ()).throw(
            planner.TravelPlanGenerationError("service unavailable")
        ),
    )

    planner.main()

    output = capsys.readouterr().out
    assert "Could not generate a travel plan: service unavailable" in output
    assert "Traceback" not in output

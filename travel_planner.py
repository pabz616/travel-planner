"""
AI TRAVEL PLANNER (revised)
"""

from __future__ import annotations

import html
import logging
import os
import time
from functools import lru_cache
from typing import Optional

import folium
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("travel_planner")

load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set. Add it to your environment or .env file.")

client = genai.Client(api_key=API_KEY)

GEMINI_TIMEOUT_MS = 60_000
MAX_OUTPUT_TOKENS = 8192
MAX_ATTEMPTS_PER_MODEL = 3
RETRY_DELAY_SECONDS = 3


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

class TravelPlannerError(Exception):
    """Base class for errors raised by this module."""


class InputValidationError(TravelPlannerError):
    """Raised when user-supplied input fails validation."""


class ModelAvailabilityError(TravelPlannerError):
    """Raised when no configured Gemini model is available."""


class TravelPlanGenerationError(TravelPlannerError):
    """Raised when available Gemini models cannot produce a valid plan."""


# --------------------------------------------------------------------------
# Schema (doubles as the Gemini response_schema and our validator)
# --------------------------------------------------------------------------

class FamousPlace(BaseModel):
    name: str
    description: str
    latitude: float
    longitude: float
    activities: list[str]
    best_time: str
    cost: str


class ItineraryDay(BaseModel):
    day: int
    title: str
    morning: str
    afternoon: str
    evening: str
    food: str
    transportation: str
    cost: str


class FoodRecommendation(BaseModel):
    name: str
    cuisine: str
    address: str
    rating: float
    cost: str


class Budget(BaseModel):
    hotel: str
    food: str
    transportation: str
    activities: str
    shopping: str
    emergencies: str
    souvenirs: str
    total: str
    remaining_budget: str


class TravelPlan(BaseModel):
    country: str
    overview: str
    famous_places: list[FamousPlace] = Field(min_length=8)
    itinerary: list[ItineraryDay]
    food: list[FoodRecommendation]
    budget: Budget
    tips: list[str]


# --------------------------------------------------------------------------
# Model availability (cached — no need to re-list on every call)
# --------------------------------------------------------------------------

def _model_name(model) -> str:
    name = getattr(model, "name", model)
    return str(name).removeprefix("models/")


def _supports_content_generation(model) -> bool:
    supported_actions = getattr(model, "supported_actions", None)
    if supported_actions is None:
        return True
    return any(action in supported_actions for action in ("generateContent", "generate_content"))


def _configured_models() -> list[str]:
    configured = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    return list(dict.fromkeys(m.strip() for m in (configured, fallback) if m.strip()))


@lru_cache(maxsize=1)
def _available_configured_models() -> tuple[str, ...]:
    """Filter configured models against what the Gemini API currently exposes.

    Cached for the process lifetime: this is a network call, and the set of
    available models does not change mid-run.
    """
    configured = _configured_models()
    list_models = getattr(client.models, "list", None)
    if list_models is None:
        return tuple(configured)

    available = {
        _model_name(model)
        for model in list_models()
        if _supports_content_generation(model)
    }
    return tuple(model for model in configured if model in available)


# --------------------------------------------------------------------------
# Budget sanity check
# --------------------------------------------------------------------------

def _parse_money(value: str) -> Optional[float]:
    """Best-effort parse of a '$1,234.50'-style string. Returns None if unparsable."""
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch == ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def check_budget_consistency(plan: TravelPlan, stated_budget: float) -> list[str]:
    """Return a list of human-readable warnings about the budget, if any."""
    warnings: list[str] = []
    b = plan.budget
    parts = {
        "hotel": _parse_money(b.hotel),
        "food": _parse_money(b.food),
        "transportation": _parse_money(b.transportation),
        "activities": _parse_money(b.activities),
        "shopping": _parse_money(b.shopping),
        "emergencies": _parse_money(b.emergencies),
        "souvenirs": _parse_money(b.souvenirs),
    }
    total_claimed = _parse_money(b.total)

    if any(value is None for value in parts.values()) or total_claimed is None:
        warnings.append("Could not parse one or more budget figures for a consistency check.")
        return warnings

    computed_total = sum(parts.values())  # type: ignore[arg-type]
    if abs(computed_total - total_claimed) > 1.0:
        warnings.append(
            f"Budget line items sum to ${computed_total:,.2f}, "
            f"but the plan's stated total is {b.total}."
        )

    if total_claimed > stated_budget:
        warnings.append(
            f"The plan's total ({b.total}) exceeds your stated budget (${stated_budget:,.2f})."
        )

    return warnings


# --------------------------------------------------------------------------
# Plan generation
# --------------------------------------------------------------------------

_RETRYABLE_ERROR_MARKERS = (
    "429", "500", "502", "503", "504", "timeout", "timed out",
    "unavailable", "internal", "rate limit", "deadline",
)


def _is_retryable(error: Exception) -> bool:
    text = str(error).lower()
    return any(marker in text for marker in _RETRYABLE_ERROR_MARKERS)


def create_travel_plan(
    country: str,
    days: int,
    budget: float,
    interests: str,
    weather: Optional[dict] = None,
) -> TravelPlan:
    """Generate a validated TravelPlan using Gemini structured output."""
    if days <= 0:
        raise ValueError("Number of days must be positive.")

    weather_context = "Current weather data is unavailable."
    if weather:
        weather_context = (
            f"Local time: {weather['local_time']}; "
            f"temperature: {weather['temperature_c']} °C; "
            f"weather code: {weather['weather_code']}; "
            f"timezone: {weather['timezone']}."
        )

    prompt = f"""Create a travel plan for:
        Country: {country}
        Number of Days: {days}
        Travel Budget: ${budget:,.2f}
        Interests: {interests}
        Live destination context (use this only for practical planning advice):
        {weather_context}

        Requirements:
        1. Create exactly {days} itinerary days, numbered 1 through {days}.
        2. Give at least 8 famous places with accurate or closely-approximated
           latitude/longitude.
        3. Famous places must be real, relevant to the country and interests given.
        4. Include historical sites, cultural experiences, and natural wonders
           where relevant to the interests.
        5. Include local food recommendations with cuisine type, address, rating (0-5),
           and estimated cost.
        6. Each itinerary day needs morning/afternoon/evening plans, a food note,
           and transportation guidance.
        7. Provide a budget breakdown (hotel, food, transportation, activities,
           shopping, emergencies, souvenirs) whose line items sum to the total,
           and keep the total within the stated travel budget where realistic.
        """

    try:
        models = _available_configured_models()
    except Exception as error:
        raise ModelAvailabilityError(
            "Unable to check Gemini model availability. Verify API_KEY, network access, "
            "and the Google GenAI client configuration."
        ) from error

    if not models:
        configured = ", ".join(_configured_models())
        raise ModelAvailabilityError(
            f"None of the configured Gemini models are available: {configured}. "
            "Set GEMINI_MODEL to a model returned by the Gemini API and optionally "
            "set GEMINI_FALLBACK_MODEL to a second supported model."
        )

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TravelPlan,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
    )

    last_error: Optional[Exception] = None
    for model in models:
        for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
            try:
                logger.info("Requesting plan from %s (attempt %d)", model, attempt)
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )

                # The SDK parses response.parsed for us when response_schema
                # is a pydantic model; fall back to manual parsing if needed.
                parsed = getattr(response, "parsed", None)
                if isinstance(parsed, TravelPlan):
                    return parsed
                return TravelPlan.model_validate_json(response.text)

            except ValidationError as error:
                # Schema violation from the model output — retrying the same
                # model with the same prompt rarely helps, but a different
                # model might do better, so don't burn all attempts here.
                last_error = error
                logger.warning("Response from %s failed schema validation: %s", model, error)
                break

            except Exception as error:
                last_error = error
                if not _is_retryable(error) or attempt == MAX_ATTEMPTS_PER_MODEL:
                    logger.warning("Non-retryable (or exhausted) error from %s: %s", model, error)
                    break
                logger.warning("Retryable error from %s (attempt %d): %s", model, attempt, error)
                time.sleep(RETRY_DELAY_SECONDS)

    raise TravelPlanGenerationError(
        "Gemini could not generate a valid travel plan with the available models "
        f"({', '.join(models)}). Check your API quota and connection, then try again; "
        "if the response format is rejected, choose another model with GEMINI_MODEL."
    ) from last_error


# --------------------------------------------------------------------------
# External data (weather, images)
# --------------------------------------------------------------------------

def get_location_weather(location: str) -> Optional[dict]:
    """Return local time and current temperature for a location using Open-Meteo."""
    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    forecast_url = "https://api.open-meteo.com/v1/forecast"

    try:
        geocoding_response = requests.get(
            geocoding_url,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geocoding_response.raise_for_status()
        results = geocoding_response.json().get("results", [])
        if not results:
            return None

        match = results[0]
        forecast_response = requests.get(
            forecast_url,
            params={
                "latitude": match["latitude"],
                "longitude": match["longitude"],
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            },
            timeout=10,
        )
        forecast_response.raise_for_status()
        forecast = forecast_response.json()
        current = forecast["current"]
        return {
            "local_time": current["time"].replace("T", " "),
            "temperature_c": current["temperature_2m"],
            "weather_code": current["weather_code"],
            "timezone": forecast.get("timezone", match.get("timezone", "local time")),
        }
    except (KeyError, TypeError, ValueError, requests.RequestException) as error:
        logger.warning("Weather lookup failed: %s", error)
        return None


def get_place_image(place: str, country: str) -> Optional[str]:
    """Look up a thumbnail image for a place via the Wikipedia search API."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{place}, {country}",
        "gsrlimit": 1,
        "prop": "pageimages|info",
        "inprop": "url",
        "pithumbsize": 500,
    }
    headers = {"User-Agent": "AI-Travel-Planner/1.0 (contact: set-your-contact-here)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumbnail = page.get("thumbnail", {})
            if thumbnail:
                return thumbnail["source"]
    except (requests.RequestException, ValueError, KeyError) as error:
        logger.warning("Image lookup for %r failed: %s", place, error)

    return None


# --------------------------------------------------------------------------
# Input validation (raises real exceptions, not `assert`)
# --------------------------------------------------------------------------

def _validate_text_input(value: str, field_name: str, max_length: int) -> None:
    allowed_characters = set(" -&,.'()")
    if not value:
        raise InputValidationError(f"Please enter a valid {field_name}.")
    if len(value) > max_length:
        raise InputValidationError(f"{field_name.title()} must be {max_length} characters or fewer.")
    if not all(ch.isalpha() or ch in allowed_characters for ch in value):
        raise InputValidationError(f"{field_name.title()} must contain letters and common separators only.")


def _validate_numeric_input(value: str, field_name: str, max_length: int) -> None:
    if not value:
        raise InputValidationError(f"Please enter a valid {field_name}.")
    if len(value) > max_length:
        raise InputValidationError(f"{field_name.title()} must contain {max_length} digits or fewer.")
    if not value.isdigit():
        raise InputValidationError(f"{field_name.title()} must contain digits only.")
    if int(value) <= 0:
        raise InputValidationError(f"Please enter a positive {field_name}.")


# --------------------------------------------------------------------------
# Map rendering
# --------------------------------------------------------------------------

def build_map(plan: TravelPlan, output_path: str = "travel_map.html") -> str:
    """Build the Folium map, save it to disk, and return the file path."""
    places = plan.famous_places
    avg_lat = sum(place.latitude for place in places) / len(places)
    avg_lon = sum(place.longitude for place in places) / len(places)
    travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="OpenStreetMap")

    for index, place in enumerate(places, 1):
        # Escape everything the model generated before it goes into HTML.
        safe_name = html.escape(place.name)
        safe_description = html.escape(place.description)
        safe_best_time = html.escape(place.best_time)
        safe_cost = html.escape(place.cost)
        safe_activities = "".join(f"<li>{html.escape(a)}</li>" for a in place.activities)

        popup_content = f"""
        <div style="width: 300px;">
          <h3>📍 {safe_name}</h3>
          <p>{safe_description}</p>
          <p><b>Cost:</b> {safe_cost}</p>
          <p><b>Best Time to Visit:</b> {safe_best_time}</p>
          <p><b>Activities:</b></p>
          <ul>{safe_activities}</ul>
        </div>
        """
        folium.Marker(
            location=[place.latitude, place.longitude],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"📍 {index}. {safe_name}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(travel_map)

    travel_map.save(output_path)
    return output_path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    print("=" * 70)
    print(" ✈️ AI TRAVEL PLANNER")
    print("=" * 70)

    try:
        country = input("Please enter the country you want to visit: ").strip()
        _validate_text_input(country, "country name", 50)

        days_input = input("How many days will you be traveling for? ").strip()
        _validate_numeric_input(days_input, "number of days", 2)
        days = int(days_input)

        budget_input = input("What is your travel budget? ").strip()
        _validate_numeric_input(budget_input, "budget", 6)
        budget = float(budget_input)

        interests = input("What are your interests (e.g., history, nature, food)? ").strip()
        _validate_text_input(interests, "interests", 100)
    except InputValidationError as error:
        print(f"\n❌ {error}")
        return

    _print_header("GENERATING TRAVEL PLAN...")

    weather = get_location_weather(country)

    try:
        plan = create_travel_plan(country, days, budget, interests, weather)
    except TravelPlannerError as error:
        print(f"\n❌ Could not generate a travel plan: {error}")
        return

    _print_header(f" 🌏 {country.upper()}")
    print("\n 📝 OVERVIEW:")
    print(plan.overview)

    print("\nℹ️ LOCAL TIME & TEMPERATURE:")
    if weather:
        print(f" 🕒 Local time: {weather['local_time']} ({weather['timezone']})")
        print(f" 🌡️ Temperature: {weather['temperature_c']} °C")
        print(f" 🌤️ Weather code: {weather['weather_code']}")
    else:
        print(" Weather data is currently unavailable.")

    _print_header("📍 FAMOUS PLACES")
    for index, place in enumerate(plan.famous_places, 1):
        image_url = get_place_image(place.name, country)
        print(f"\n {index}. 📍 {place.name}")
        if image_url:
            print(f"    Image: {image_url}")
        print(f"    Cost: {place.cost}")
        print(f"    Description: {place.description}")
        print(f"    Latitude: {place.latitude}, Longitude: {place.longitude}")
        print(f"    Best Time to Visit: {place.best_time}")
        print("    Activities:")
        for activity in place.activities:
            print(f"        - {activity}")

    _print_header("🗺️ GENERATING INTERACTIVE MAP")
    map_path = build_map(plan)
    print(f" Map saved to: {map_path}")

    _print_header("📅 COMPLETE DAY-BY-DAY ITINERARY")
    for day in plan.itinerary:
        print(f"\n--- DAY {day.day}: {day.title} ---")
        print(f"\n🌄 MORNING\n{day.morning}")
        print(f"\n☀️ AFTERNOON\n{day.afternoon}")
        print(f"\n🌇 EVENING\n{day.evening}")
        print(f"\n🍽️ FOOD\n{day.food}")
        print(f"\n🚌 TRANSPORTATION\n{day.transportation}")
        print(f"\n💰 COST\n{day.cost}")

    _print_header("🥣 MUST-TRY FOOD")
    for food in plan.food:
        print(f"🍴 {food.name} ({food.cuisine}) — {food.address}")
        print(f"    Rating: {food.rating}/5 | Cost: {food.cost}")

    _print_header("💰 TRAVEL BUDGET BREAKDOWN")
    b = plan.budget
    for category in ("hotel", "food", "transportation", "activities", "shopping", "emergencies", "souvenirs"):
        print(f" {category.upper()}: {getattr(b, category)}")
    print(f"\n TOTAL: {b.total}")
    print(f" REMAINING BUDGET: {b.remaining_budget}")

    warnings = check_budget_consistency(plan, budget)
    if warnings:
        print("\n⚠️ BUDGET WARNINGS:")
        for warning in warnings:
            print(f" - {warning}")

    _print_header("💡 TRAVEL TIPS")
    for tip in plan.tips:
        print(f"✔️ {tip}")

    _print_header("🎉 TRAVEL PLAN COMPLETE!")


if __name__ == "__main__":
    main()
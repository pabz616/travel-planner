"""
Live smoke test for travel_planner.create_travel_plan().

This makes a REAL call to the Gemini API (uses your API_KEY / .env), so it
costs quota/tokens. Run it once after any change to the prompt, schema, or
SDK config to confirm structured output still behaves as expected.

Usage:
    python3 test_generation.py
    python3 test_generation.py --country "Japan" --days 5 --budget 3000 --interests "history, food"

Exit code is 0 if all checks pass, 1 otherwise — safe to wire into CI or a
pre-deploy check.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from travel_planner import TravelPlan, create_travel_plan


def run_checks(plan: TravelPlan, expected_days: int) -> list[str]:
    """Return a list of failure messages. Empty list means everything passed."""
    failures: list[str] = []

    if not isinstance(plan, TravelPlan):
        failures.append(f"Expected a TravelPlan instance, got {type(plan)}.")
        return failures  # nothing else is safe to check

    if len(plan.famous_places) < 8:
        failures.append(f"Expected >= 8 famous places, got {len(plan.famous_places)}.")

    if len(plan.itinerary) != expected_days:
        failures.append(
            f"Expected {expected_days} itinerary days, got {len(plan.itinerary)}."
        )

    day_numbers = sorted(day.day for day in plan.itinerary)
    if day_numbers != list(range(1, expected_days + 1)):
        failures.append(f"Itinerary day numbers are not 1..{expected_days}: got {day_numbers}.")

    if not plan.food:
        failures.append("Expected at least one food recommendation, got none.")

    if not plan.tips:
        failures.append("Expected at least one tip, got none.")

    for place in plan.famous_places:
        if not (-90 <= place.latitude <= 90):
            failures.append(f"Place '{place.name}' has an out-of-range latitude: {place.latitude}.")
        if not (-180 <= place.longitude <= 180):
            failures.append(f"Place '{place.name}' has an out-of-range longitude: {place.longitude}.")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test live travel plan generation.")
    parser.add_argument("--country", default="Japan")
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--budget", type=float, default=3000)
    parser.add_argument("--interests", default="history, food")
    args = parser.parse_args()

    print(f"Requesting a {args.days}-day plan for {args.country} "
          f"(budget ${args.budget:,.0f}, interests: {args.interests})...")

    start = time.monotonic()
    try:
        plan = create_travel_plan(args.country, args.days, args.budget, args.interests)
    except Exception as error:
        print(f"\n❌ create_travel_plan raised an exception: {error}")
        return 1
    elapsed = time.monotonic() - start

    print(f"Response received in {elapsed:.1f}s.\n")

    failures = run_checks(plan, args.days)

    if failures:
        print("❌ FAILED — issues found:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("✅ PASSED — response matches the expected schema and shape.")
    print(f"   Places: {len(plan.famous_places)} | Itinerary days: {len(plan.itinerary)} "
          f"| Food recs: {len(plan.food)} | Tips: {len(plan.tips)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
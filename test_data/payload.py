from .data import BUDGET, COUNTRY, DAYS


def _format_budget(amount):
    return f"${amount:,.0f}"


budget_parts = {
    "hotel": round(BUDGET * 0.40),
    "food": round(BUDGET * 0.20),
    "transportation": round(BUDGET * 0.10),
    "activities": round(BUDGET * 0.15),
    "shopping": round(BUDGET * 0.05),
    "emergencies": round(BUDGET * 0.05),
}
budget_parts["souvenirs"] = BUDGET - sum(budget_parts.values())

payload = {
    "country": COUNTRY,
    "overview": "A classic trip.",
    "famous_places": [
        {
            "name": f"Place {index}",
            "description": "A notable destination.",
            "latitude": 48.0 + index / 10,
            "longitude": 2.0 + index / 10,
            "activities": ["Sightseeing"],
            "best_time": "Spring",
            "cost": "$10",
        }
        for index in range(1, 9)
    ],
    "itinerary": [
        {
            "day": day,
            "title": f"Explore {COUNTRY} - day {day}",
            "morning": "Visit a landmark.",
            "afternoon": "Explore the city.",
            "evening": "Enjoy a local meal.",
            "food": "Local cuisine",
            "transportation": "Walk or use public transit.",
            "cost": "$100",
        }
        for day in range(1, DAYS + 1)
    ],
    "food": [
        {
            "name": "Local dish",
            "cuisine": "French",
            "address": f"Central market, {COUNTRY}",
            "rating": 4.5,
            "cost": "$20",
        }
    ],
    "budget": {
        **{category: _format_budget(amount) for category, amount in budget_parts.items()},
        "total": _format_budget(BUDGET),
        "remaining_budget": "$0",
    },
    "tips": [],
}

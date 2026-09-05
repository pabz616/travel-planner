payload = {
    "country": "France",
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
            "title": f"Explore France - day {day}",
            "morning": "Visit a landmark.",
            "afternoon": "Explore the city.",
            "evening": "Enjoy a local meal.",
            "food": "Local cuisine",
            "transportation": "Walk or use public transit.",
            "cost": "$100",
        }
        for day in range(1, 4)
    ],
    "food": [
        {
            "name": "Local dish",
            "cuisine": "French",
            "address": "Paris, France",
            "rating": 4.5,
            "cost": "$20",
        }
    ],
    "budget": {
        "hotel": "$400",
        "food": "$200",
        "transportation": "$100",
        "activities": "$150",
        "shopping": "$50",
        "emergencies": "$50",
        "souvenirs": "$50",
        "total": "$1000",
        "remaining_budget": "$500",
    },
    "tips": [],
}

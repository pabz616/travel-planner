from google import genai
import requests
import json
import time
import folium
import os
from dotenv import load_dotenv
from IPython.display import display, Image, HTML

"""
    TRAVEL PLANNER
"""

load_dotenv()
API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY)


def create_travel_plan(country, days,  budget, interests):
    """GETS THE TRAVEL PLAN USING GEMINI API"""
    
    prompt = f"""Create a travel plan for: 
        Country: {country} 
        Number of Days: {days} 
        Travel Budget: {budget} 
        Interests: {interests}.
        
        Return only valid JSON with the following structure:{{
            "country": "{country}",
            "overview": "A brief overview or description of the travel plan, highlighting key attractions and experiences.",
            "famous_places": 
            [
                {{
                    "name": "Famous Place",
                    "description": "Detailed description",
                    "latitude": 0,
                    "longitude": 0,
                    "activities":[
                        "Activity 1",
                        "Activity 2"
                    ],
                    
                    "best_time': "Best time",
                    "cost": "$50";
                    
                }}
            
            "itinerary": [
            {{
               "day": 1,
               "title": "Day 1 Title",
               "morning": "Morning plan",
               "afternoon": "Afternoon plan",
               "evening": "Evening plan",
               "food": "Food recommendations",
               "transportation": "Transportation recommendations",
               "cost": "$200"
            }}
        ],
        
            "food": 
            [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Cuisine Type",
                    "address": "Restaurant Address",
                    "rating": 4.5,
                    "cost": "$30"
                }}
            ],
            
            "budget": 
            {{
                "hotel": "$1000",
                "food": "$300",
                "transportation": "$200",
                "activities": "$400",
                "shopping": "$150",
                "emergencies": "$100",
                "souvenirs": "$100",
                "total": "$2150",
                "remaining_budget": "$850"
            }}
            
            "tips": 
            [
                "Tip 1",
                "Tip 2",
                "Tip 3",
                "Tip 4",
                "Tip 5"
            ]
        }}
        
        IMPORTANT:
        1. Ensure that the JSON is valid and properly formatted.
        2. Create exactly {days} days.
        3. Give at least 8 famous places with their details.
        4. Famous places should be relevant to the country and interests provided, and must exist.
        5. Latitude and longitude should be accurate for each famous place, or close approximation.
        6. Include famous tourist attractions, historical sites, cultural experiences, and natural wonders.
        7. Include local food recommendations with cuisine type, address, rating, and cost.
        8. Provide best places to visit for each day, including morning, afternoon, and evening plans, along with transportation.
        10. Provide a budget breakdown for the entire trip, including hotel, food, transportation, activities, shopping, emergencies, and souvenirs.
        """
        
    models = [
        "gemini-3.6-flash",
        "gemini-3.6-turbo",
    ]

    for model in models:
        for attempt in range(3):
            # ERROR HANDLING
            try:
                print(f" using model: {model} (Attempt {attempt + 1})")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    # max_output_tokens=200000,
                    # temperature=1,
                )

                text = response.text.strip()

                # REMOVING MARKDOWN CODE BLOCKS
                text = text.replace("```json", "")
                text = text.replace("```", "")
                text = text.strip()

                return json.loads(text)

            except Exception as e:
                print(f"Error with model {model} on attempt {attempt + 1}: {e}")
                time.sleep(3)  # Wait before retrying
                continue

    raise Exception("Gemini API is currently unavailable.")


def get_place_image(place, country):
    """GETS THE IMAGE OF A PLACE USING GOOGLE SEARCH API"""
    
    url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{place}, {country}",
        "gsrlimit": 1,
        "prop": "pageimages | info",
        "inprop": "url",
        "titles": f"{place}, {country}",
        "pithumbsize": 500
    }
    
    headers = {"User-Agent": "AI-Travel-Planner"}
    
    try:
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        
        for page in pages.values():
            thumbnail = page.get("thumbnail", {})
            if thumbnail:
                return thumbnail["source"]
            
    except Exception as e:
        print(f"Image error: {e}")
        
    return None


def main():
    """Run the interactive travel planner CLI."""
    print("=" * 70)
    print(" ✈️ AI TRAVEL PLANNER")
    print("=" * 70)
    
    # USER INPUTS

    country = input("Please enter the country you want to visit: ")
    assert isinstance(country, str), "Input must be a string"
    assert len(country) > 0, "Please enter a valid country name."
    assert country.isalpha(), "The country name must contain only letters"
    
    days = int(input("How many days will you be traveling for? "))
    assert isinstance(days, int), "Input must be an integer"
    assert days > 0, "Please enter a valid number of days."
    assert days.isnumeric(), "The number of days must be a positive integer"

    budget = float(input("What is your travel budget? "))
    assert isinstance(budget, float), "Input must be a float"
    assert budget > 0, "Please enter a valid budget."
    assert budget.isnumeric(), "The budget must be a positive number"

    interests = input("What are your interests (e.g., history, nature, food)? ")
    assert isinstance(interests, str), "Input must be a string"
    assert len(interests) > 0, "Please enter valid interests."
    assert interests.isalpha(), "Please make sure your interests contain only letters"
    
    # OUTPUT
    print("\n")
    print("=" * 70)
    print("\nGENERATING TRAVEL PLAN...")
    print("=" * 70)

    plan = create_travel_plan(country, days, budget, interests)

    print("\n")
    print("=" * 70)
    print("\n ℹ️ BASIC INFORMATION:")
    print("=" * 70)
    print(f" 🌏 {country.upper()}")
    print("=" * 70)
    print("\n 📝 OVERVIEW:")
    print("=" * 70)
    print(plan["overview"])

    print("\n")
    print("=" * 70)
    print("🖼️ IMAGES OF FAMOUS PLACES")
    print("=" * 70)

    for place in plan["famous_places"]:
        name = place["name"]
        print(f" 🧭 {name}")
        place["image"] = get_place_image(name, country)

    print("\n")
    print("=" * 70)
    print("📍 FAMOUS PLACES")
    print("=" * 70)

    for index, place in enumerate(plan["famous_places"], 1):
        if place.get("image"):
            display(HTML(f'<img src="{place["image"]}" alt="{place["name"]}" width="400">'))

        print(f"    Cost: {place['cost']}")
        print(f"\n {index}. 📍 {place['name']}")
        print(f"Description: {place['description']}")
        print(f"Latitude: {place['latitude']}, Longitude: {place['longitude']}")
        print(f"Best Time to Visit: {place['best_time']}")
        print("Activities:")
        for activity in place["activities"]:
            print(f"        - {activity}")

        if place.get("image"):
            try:
                display(Image(url=place["image"], width=400))
            except Exception as error:
                print(f"Error displaying image for {place['name']}: {error}")

    print("\n")
    print("=" * 70)
    print("🗺️ GENERATE INTERACTIVE MAP")
    print("=" * 70)

    places = plan["famous_places"]
    avg_lat = sum(place["latitude"] for place in places) / len(places)
    avg_lon = sum(place["longitude"] for place in places) / len(places)
    travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="OpenStreetMap")

    for index, place in enumerate(places, 1):
        popup_content = f"""
        <div style="width: 300px;">
          <p>Cost:</b> {place['cost']}</p>
          <h3>📍 {place['name']}</h3>
          <p>{place['description']}</p>
          <p>Best Time to Visit:</b> {place['best_time']}</p>
          <p>Activities:</p>
        </div>
        """
        folium.Marker(
            location=[place["latitude"], place["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f" 📍 {index}. {place['name']}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(travel_map)

    print("\n")
    print("=" * 70)
    print("📅 COMPLETE DAY-BY-DAY ITINERARY")
    print("=" * 70)

    for day in plan["itinerary"]:
        print(f"\n{'=' * 70}")
        print(f"DAY {day['day']}")
        print(f"TITLE {day['title']}")
        print(f"\n{'=' * 70}")
        for section, label in (("morning", "🌄 MORNING"), ("afternoon", "☀️ AFTERNOON"),
                               ("evening", "🌇 EVENING"), ("food", "🍽️ FOOD"),
                               ("transportation", "🚌 TRANSPORTATION"), ("cost", "💰 COST")):
            print(f"\n{label}")
            print(day[section])

    print("\n")
    print("=" * 70)
    print("🥣 MUST-TRY FOOD")
    print("=" * 70)
    for food in plan["food"]:
        print(f"🍴 {food}")

    print("\n")
    print("=" * 70)
    print("💰 TRAVEL BUDGET BREAKDOWN")
    print("=" * 70)
    travel_budget = plan["budget"]
    for category in ("hotel", "food", "transportation", "activities", "shopping", "emergencies", "souvenirs"):
        print(f"\n {category.upper()}: {travel_budget[category]}")
    print("=" * 70)
    print(f"\n TOTAL: {travel_budget['total']}")
    print(f"\n REMAINING BUDGET: {travel_budget['remaining_budget']}")

    print("\n")
    print("=" * 70)
    print("💡 TRAVEL TIPS")
    print("=" * 70)
    for tip in plan["tips"]:
        print(f"✔️ {tip}")

    print("\n")
    print("=" * 70)
    print("🎉 TRAVEL PLAN COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
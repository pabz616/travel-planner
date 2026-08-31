from google import genai
import requests
import json
import time
import folium
from IPython.display import display, Image, HTML

"""
    TRAVEL PLANNER
"""

API_KEY = "#"

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
                    "description": "Detailed description of the famous place.",
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
               "transport": "Transport recommendations",
               "cost": "$200.00"
            }}
        ],
        
            "food_recommendations": 
            [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Cuisine Type",
                    "address": "Restaurant Address",
                    "rating": 4.5,
                    "cost": "$30.00"
                }}
            ],
            
            "budget_breakdown": 
            {{
                "hotel": "$1000.00",
                "food": "$300.00",
                "transportation": "$200.00",
                "activities": "$400.00",
                "shopping": "$150.00",
                "emergencies": "$100.00",
                "souvenirs": "$100.00",
                "total": "$2150.00",
                "remaining_budget": "$850.00"
            }}
            
            "top-5_travel_tips": 
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
                    max_output_tokens=2000,
                    temperature=0.7,
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

# ================================================
# USER INPUT
# ================================================


print("=" * 70)
print(" ✈️ AI TRAVEL PLANNER")
print("=" * 70)

country = input("Please enter the country you want to visit: ")
days = int(input("How many days will you be traveling for? "))
budget = float(input("What is your travel budget? "))
interests = input("What are your interests (e.g., history, nature, food)? ")

# ================================================
# GENERATE TRAVEL PLAN
# ================================================

print("\n")
print("=" * 70)
print("\nGenerating your travel plan...")
print("=" * 70)

plan = create_travel_plan(country, days, budget, interests)

# ================================================
# BASIC INFORMATION
# ================================================

print("\n")
print("=" * 70)
print("\n ℹ️ BASIC INFORMATION:")
print("=" * 70)
print(f" 🌏 {country.upper()}")
print("=" * 70)
print("\n 📝 OVERVIEW:")
print("=" * 70)
print(plan["overview"])

# ================================================
# IMAGES OF FAMOUS PLACES
# ================================================

print("\n")
print("=" * 70)
print("🖼️ IMAGES OF FAMOUS PLACES:")
print("=" * 70)

for place in plan["famous_places"]:
    name = place["name"]
    print(f" 🧭 {name}")
    image = get_place_image(name, country)
    
    place["image"] = image

# ================================================
# FAMOUS PLACES
# ================================================

print("\n")
print("=" * 70)
print("📍 FAMOUS PLACES:")
print("=" * 70)

for i, place in enumerate(plan["famous_places"], start=1):
    if place.get("image"):
        display(HTML(f'<img src="{place["image"]}" alt="{place["name"]}" width="400">'))
    
    print(f"    Cost: {place['cost']}")
    print(f"\n {i}. 📍 {place['name']}")
    print(f"    Description: {place['description']}")
    print(f"    Latitude: {place['latitude']}, Longitude: {place['longitude']}")
    print(f"    Best Time to Visit: {place['best_time']}")
    print(f"    Activities:")
    for activity in place["activities"]:
        print(f"        - {activity}")
        
    if place["image"]:
        try:
            display(Image(url=place["image"], width=400))
        
        except Exception as e:
            print(f"Error displaying image for {place['name']}: {e}")
    

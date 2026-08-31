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
               "transportation": "Transportation recommendations",
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
print("\nGENERATING TRAVEL PLAN...")
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
print("🖼️ IMAGES OF FAMOUS PLACES")
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
print("📍 FAMOUS PLACES")
print("=" * 70)

for i, place in enumerate(plan["famous_places"], 1):
    if place.get("image"):
        display(HTML(f'<img src="{place["image"]}" alt="{place["name"]}" width="400">'))
    
    print(f"    Cost: {place['cost']}")
    print(f"\n {i}. 📍 {place['name']}")
    print(f"Description: {place['description']}")
    print(f"Latitude: {place['latitude']}, Longitude: {place['longitude']}")
    print(f"Best Time to Visit: {place['best_time']}")
    print("Activities:")
    for activity in place["activities"]:
        print(f"        - {activity}")
        
    if place["image"]:
        try:
            display(Image(url=place["image"], width=400))
        
        except Exception as e:
            print(f"Error displaying image for {place['name']}: {e}")
    
# ================================================
# INTERACTIVE MAP
# ================================================

print("\n")
print("=" * 70)
print("🗺️ GENERATE INTERACTIVE MAP")
print("=" * 70)

places = plan["famous_places"]

# CALC CENTER OF MAP

avg_lat = sum(place["latitude"] for place in places) / len(places)
avg_lon = sum(place["longitude"] for place in places) / len(places)

travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="OpenStreetMap") 
# ================================================
# MAP MARKERS
# ================================================

for i, place in enumerate(places, 1):
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
        tooltip=f" 📍 {i}. {place['name']}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    )
    
# ================================================
# DAY-BY-DAY ITINERARY
# ================================================

print("\n")
print("=" * 70)
print("📅 COMPLETE DAY-BY-DAY ITINERARY")
print("=" * 70)

for day in plan["itinerary"]:
    print(f"\n{'=' * 70}")
    print(f"DAY {day['day']}")
    print(f"TITLE {day['title']}")
    print(f"\n{'=' * 70}")
    print("\n🌄 MORNING")
    print(day["morning"])
    print("\n☀️ AFTERNOON")
    print(day["afternoon"])
    print("\n🌇 EVENING")
    print(day["evening"])
    print("\n🍽️ FOOD")
    print(day["food"])
    print("\n🚌 TRANSPORTATION")
    print(day["transportation"])
    print("\n💰 COST")
    print(day["cost"])

# ================================================
# FOOD
# ================================================

print("\n")
print("=" * 70)
print("🥣 MUST-TRY FOOD")
print("=" * 70)

for food in plan["food_recommendations"]:
    print(f"🍴 {food}")
    
# ================================================
# TRAVEL BUDGET BREAKDOWN
# ================================================

print("\n")
print("=" * 70)
print("💰 TRAVEL BUDGET BREAKDOWN")
print("=" * 70)

travel_budget = plan["budget"]

print(f"\n HOTEL: {travel_budget['hotel']}")
print(f"\n FOOD: {travel_budget['food']}")
print(f"\n TRANSPORTATION: {travel_budget['transportation']}")
print(f"\n ACTIVITIES: {travel_budget['activities']}")
print(f"\n SHOPPING: {travel_budget['shopping']}")
print(f"\n EMERGENCIES: {travel_budget['emergency']}")
print(f"\n SOUVENIRS: {travel_budget['souvenirs']}")
print("=" * 70)
print(f"\n TOTAL: {travel_budget['total']}")
print(f"\n REMAINING BUDGET: {travel_budget['remaining_budget']}")

# ================================================
# TRAVEL TIPS
# ================================================

print("\n")
print("=" * 70)
print("💡 TRAVEL TIPS")
print("=" * 70)

for tip in plan["tips"]:
    print(f"✔️ {tip}")
    
# ================================================
# TRAVEL PLANNER COMPLETED
# ================================================
print("\n")
print("=" * 70)
print("🎉 TRAVEL PLAN COMPLETE!")
print("=" * 70)
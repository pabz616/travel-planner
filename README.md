# travel-planner

AI-Powered Travel Planner in Python

## SCOPE

Build an AI-powered Travel Planner using Python that can help generate personalized travel plans based on your preferences.

src. `https://pythonclcoding.substack.com/p/ai-powered-travel-planner-in-python?publication_id=1774494&post_id=212712591&r=1edyq1&triedRedirect=true`

### FEATURES

🔹 Destination planning
🔹 Personalized itineraries
🔹 Activities & places to explore
🔹 Travel recommendations
🔹 AI-powered suggestions
🔹 Python-based automation

### PRE-REQUISITE

Use the following libraries:

🔹 Google genai (Gemini), requests, json, time, folium, IPython
🔹 Wikipedia

Set `API_KEY` before running the planner. The app checks the Gemini API for
generation-capable models before making a request. By default it uses
`gemini-2.5-flash` and falls back to `gemini-2.5-flash-lite`; override these
with `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL` when needed. If neither model
is available, the planner reports the configuration change required.

### HOW IT WORKS

Run the script `python3 planner.py`
When the prompt is engaged, it will ask for specific information like, "place to visit," "number of days," and "travel budget"

### RESULTS

If the location entered is valid, the output will look something like the following (snippet):
<img width="1075" height="550" alt="Screenshot 2026-08-31 at 4 22 56 PM" src="https://github.com/user-attachments/assets/b5ab0b90-2bb7-4abe-9a4f-8c6a41bccfc8" />

### TESTING

The file `planner.py` has been tested for the following:

- Missing API key validation
- No input validation for days, budget, and interests
- Prompt template contains malformed JSON fragments
- Assumes LLM will always return valid JSON with the exact schema
- Hardcoded model list may be invalid or unavailable
- Sequential image requests for every place
- Map markers are created but never added to the map
- Notebook-only display dependencies
- No validation for place/coordinate realism
- Untrusted user input is passed directly into the prompt
- No handling for API quota, rate limiting, or network outages beyond a generic retry loop
- CLI input prompts are not user-friendly for invalid or blank values
- Budget and itinerary outputs are not cross-checked
- Secrets are handled implicitly via environment variables, but there is no safeguard or clear error if missing

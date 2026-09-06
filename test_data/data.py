from pathlib import Path
from random import choice, randint

# MODELS
CURRENT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"

# SAMPLE PAYLOAD
COUNTRIES = tuple(
    country.strip()
    for country in Path(__file__).with_name("countries.txt").read_text(encoding="utf-8").splitlines()
    if country.strip()
)

COUNTRY = choice(COUNTRIES)
DAYS = randint(1, 365)
BUDGET = randint(100, 5000)
INTERESTS = "food", "history", "nature"

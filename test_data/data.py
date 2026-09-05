from pathlib import Path
from faker import Faker

fake = Faker()

# MODELS
CURRENT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"

# SAMPLE PAYLOAD
COUNTRIES = tuple(
    country.strip()
    for country in Path(__file__).with_name("countries.txt").read_text(encoding="utf-8").splitlines()
    if country.strip()
)

COUNTRY = fake.random_element(elements=COUNTRIES)
DAYS = fake.random_int(min=1, max=365)
BUDGET = fake.random_int(min=100, max=5000)
INTERESTS = "food", "history", "nature"

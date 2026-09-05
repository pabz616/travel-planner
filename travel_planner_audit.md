# Critical bugs (will break or silently corrupt behavior)

1. The prompt's JSON schema template is itself malformed.
Inside `create_travel_plan`, the example schema has multiple syntax errors that you're literally showing to the model as the target format:

* "famous_places": [ {{ ... }} is never closed with ] before "itinerary": starts — the list bracket is missing.
* "best_time': "Best time", mixes a single quote and double quote.
* "cost": "$50"; uses a semicolon instead of a comma.

Since Gemini often pattern-matches the literal structure you show it, this significantly raises the odds of it returning invalid JSON — which then burns through your 3 retries × 2 models = 6 wasted API calls every single run, because the bug is systemic, not transient. Fix the template first; it's the highest-leverage change in this file.

2. The Folium map is built but never saved or shown.

python
```
travel_map = folium.Map(...)
for index, place in enumerate(places, 1):
    folium.Marker(...).add_to(travel_map)
```
...script moves on. travel_map is never referenced again.

## USABILITY

The "🗺️ GENERATE INTERACTIVE MAP" section header prints, but nothing is written to disk or displayed. Add travel_map.save("travel_map.html") and tell the user where it went.

3. food items are dicts but printed as if they were strings.
`plan["food"]` items have name, cuisine, address, rating, cost per your schema, but:

python
```
for food in plan["food"]:
    print(f"🍴 {food}")
```

This prints the raw dict repr ({'name': 'X', 'cuisine': 'Y', ...}) instead of formatted text.

4. `get_place_image` sends contradictory Wikipedia API params.
You pass both generator=search (which selects pages from a search query) and titles=f"{place}, {country}" (which selects pages by exact title) in the same request. These are two different page-selection mechanisms; mixing them is undefined/inconsistent behavior. Drop titles.

5. IPython display calls in a CLI script.
display(), Image(), HTML() are Jupyter-only. Run this as python script.py and the "image" HTML just prints as inert markup (or errors) rather than showing anything. Either commit to a notebook context or drop these calls in favor of just printing image URLs in a plain script.

### Security

6. assert is used for user-input validation.

python
```
assert value, f"Please enter a valid {field_name}."
```

assert statements are stripped entirely when Python runs with -O (optimized mode). That silently disables all your input validation — a real risk if this code is ever invoked non-interactively or packaged. Use explicit if not value: raise ValueError(...) instead.

7. Prompt injection surface, partially mitigated.
country and interests are interpolated directly into the LLM prompt. _validate_text_input restricts to letters/spaces/-&,.'(), which meaningfully limits injection payloads — good. But interests allows up to 100 chars of free text with those characters, which is still enough room for basic instruction-injection attempts (e.g., "ignore previous instructions"). Since this only affects the shape of the JSON you asked for and you validate the response schema afterward, the blast radius is low, but worth noting if you ever feed the "overview" or other model-generated text back into another prompt or into HTML unescaped.

8. Unescaped user/model content is interpolated into HTML.

python
```
popup_content = f"""<div>... <h3>📍 {place['name']}</h3> ... <p>{place['description']}</p> ...</div>"""
```

`place['name']`/description come from the LLM (which is influenced by user input). If any of that text contains <script> or similar, it lands unescaped in the Folium popup HTML — a stored XSS vector if this map is ever served rather than just opened locally. Use html.escape() on any text going into popup_content.

9. No timeout on the Gemini call.
requests.get(...) calls all pass timeout=10, good — but client.models.generate_content(...) has no timeout, so a hung connection can block the script indefinitely.

## Performance / reliability

10. _available_configured_models() calls client.models.list() on every create_travel_plan invocation. That's an extra network round-trip before you've even started generating. Cache it (e.g., functools.lru_cache) for the process lifetime.

11. Retry loop has no backoff strategy and retries indiscriminately. time.sleep(3) is a flat delay regardless of error type. An invalid API key or a malformed-prompt-driven JSON error will fail identically on every retry — you're paying the 3-second penalty 6 times for something retrying can't fix. Distinguish retryable (rate limit, transient network) from non-retryable (auth, validation) errors and fail fast on the latter.

12. No max_output_tokens set (it's commented out). Given you're asking for 8+ places, a full multi-day itinerary, and food/tips lists, a moderately long trip (10+ days) risks truncated JSON — which then looks like a parse failure rather than a token-limit issue, making it harder to diagnose. Set an explicit generous limit.

13. Consider Gemini's structured output mode instead of prompt-engineered JSON. The google-genai SDK supports response_mime_type="application/json" plus a response_schema (Pydantic model or JSON schema) on generate_content. That would eliminate the markdown-fence-stripping (text.replace("```json", "")), most malformed-JSON retries, and the schema-typo bug entirely — the API enforces the shape for you rather than you validating it after the fact.

## Correctness / validation gaps

14. `validate_travel_plan` checks `famous_places` deeply but not itinerary or food. If the model omits a field inside an itinerary day (e.g., `transportation`), you won't find out until `main()` does `day[section]` and throws a raw `KeyError` mid-print, after you've already printed half the itinerary. Validate all nested structures up front, consistently.

15. Budget arithmetic is trusted, not verified. `hotel + food + transportation + ...` should equal total, and total vs the user's stated budget should inform remaining_budget. Right now these are LLM-generated strings like "$1000" that are never parsed or cross-checked — the model can (and will, eventually) return numbers that don't add up. Parse the currency strings and verify the arithmetic server-side; correct or flag mismatches rather than displaying them as-is.

## Minor / style

* _model_name/_supports_content_generation are solid defensive helpers — good pattern, keep them.
* Custom exception hierarchy (PlanValidationError, ModelAvailabilityError, TravelPlanGenerationError) is a nice touch for a script this size.
* `print(f" Cost: {place['cost']}")` is printed before the place's name/index — reads oddly; move it after the header line.
* Swap bare `print()`-based error/debug output for the `logging` module if this ever runs unattended or gets deployed — easier to filter by severity and redirect.
* `dict.fromkeys(...)` dedupe in `_configured_models` is a nice touch, no notes there.

## Suggested priority order

1. Fix the malformed JSON schema in the prompt (or switch to response_schema structured output — kills several bugs at once).
2. Fix the food printing bug and the unsaved Folium map — both are "the feature silently doesn't work" bugs.
3. Replace `assert`-based validation with real exceptions.
4. Escape HTML in the map popups.
5. Add timeout + smarter retry logic to the Gemini call.
6. Deepen `validate_travel_plan` to cover itinerary/food, and verify budget arithmetic.
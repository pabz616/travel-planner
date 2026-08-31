# Invalid or malformed AI responses are assumed to be valid JSON

## Description

The script does not validate the structure or integrity of the Gemini response before parsing it. If the model returns malformed JSON or a mismatched schema, the program will fail unpredictably while trying to read keys like `famous_places` or `itinerary`.

## Section, URL, or area affected

- `planner.py`
- JSON parsing and application data handling
- `create_travel_plan()` return value consumption

## Issue Type

API / Reliability

## Severity

High

## Priority

P1

## Frequency of occurrence

Intermittent, depending on model output quality and prompt constraints.

## Steps to reproduce

1. Trigger the planner in an environment where the model returns malformed output or a truncated response.
2. The response is passed directly into `json.loads()`.
3. A JSON decode error or downstream `KeyError` occurs.

## Expected Result

The application should validate the response shape before using it and fail with a clear, actionable message.

## Actual Result

Malformed output is parsed with no guard, resulting in unhandled exceptions when the code later expects specific keys.

## Error Messages

- JSON parsing errors from `json.loads()`
- downstream `KeyError` errors when expected keys are missing from the response

## Screenshot

Not captured.

## Logs

No schema validation log was emitted before parsing.

## Root-Cause

The function assumes the model always returns valid JSON with the exact expected structure, but it never checks structural validity before data consumption.

## Recommended Fix

Validate the parsed JSON against the expected schema and fail gracefully when required fields are missing or malformed.

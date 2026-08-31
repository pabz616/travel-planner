# Unverified model list and retry behavior reduce reliability

## Description

The planner uses a hardcoded list of Gemini model names and retries without validating that the models are supported by the current runtime. This creates reliability risk when the configured environment does not support those model IDs or when API requests fail consistently.

## Section, URL, or area affected

- `planner.py`
- Gemini integration and retry loop
- `create_travel_plan()`

## Issue Type

API / Reliability

## Severity

Medium

## Priority

P2

## Frequency of occurrence

Depends on environment and model availability; can occur on unsupported model names or quota/network failures.

## Steps to reproduce

1. Run the planner with an environment that does not support the configured model names.
2. Observe the model loop begins with `gemini-3.6-flash` or similar values.
3. Let the request fail or be rejected.
4. Observe the script retries without meaningful recovery or validation.

## Expected Result

The app should validate model availability, fail clearly when unsupported, and provide a helpful fallback or actionable message.

## Actual Result

The script retries with a hardcoded list, and if all retries fail the user sees a generic API failure message.

## Error Messages

- `Gemini API is currently unavailable.`
- model-specific runtime errors from the backend

## Screenshot

Not captured.

## Logs

Observed output includes repeated model retry attempts with no environment-specific validation.

## Root-Cause

The model list is preset without compatibility checks, and the retry loop does not distinguish between invalid model IDs, quota exhaustion, network errors, or invalid prompt output.

## Recommended Fix

Validate or constrain supported models, add explicit error classification, and expose meaningful API failure handling to the user.

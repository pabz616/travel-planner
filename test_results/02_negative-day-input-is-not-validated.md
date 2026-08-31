# Negative or invalid day input is not validated before API call

## Description

The script accepts invalid day values such as negative numbers or zero without first rejecting them. This creates an unreliable workflow because invalid trip length values can propagate into prompt construction and the downstream API call.

## Section, URL, or area affected

- `planner.py`
- Travel request generation logic
- `create_travel_plan()` input handling

## Issue Type

Functional

## Severity

Medium

## Priority

P2

## Frequency of occurrence

Always for invalid inputs such as `0`, `-3`, or non-numeric values entered through the CLI.

## Steps to reproduce

1. Run the planner script.
2. Enter a non-positive day count such as `0` or `-3`.
3. Observe that the script continues without rejecting the value.
4. The invalid value is passed into the generated prompt and sent to the API layer.

## Expected Result

The planner should reject invalid values before generating a trip plan and display a clear user-facing validation message.

## Actual Result

The planner continues with the invalid input and produces downstream issues or misleading output.

## Error Messages

No explicit validation error was raised by the script.

## Screenshot

Not captured.

## Logs

No application-level validation error was logged.

## Root-Cause

There is no guard for input validation before the program calls `create_travel_plan()` and builds the prompt.

## Recommended Fix

Add explicit checks to ensure `days` is a positive integer before proceeding, and surface a friendly validation message to the user.

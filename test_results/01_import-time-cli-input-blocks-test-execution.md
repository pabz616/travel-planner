# Import-time CLI input blocks test execution

## Description

Importing the planner module triggers interactive `input()` calls immediately, which prevents test runners from importing the module in a non-interactive environment. This is a direct functional issue because the module is not safely importable for automated validation.

## Section, URL, or area affected

- `planner.py`
- Module import path and startup behavior
- Script entrypoint at the bottom of the file

## Issue Type

Functional

## Severity

High

## Priority

P1

## Frequency of occurrence

Always when the module is imported in a non-interactive session such as pytest or CI.

## Steps to reproduce

1. Open a Python session that is not interactive.
2. Import `planner` from the project root.
3. Observe that the script immediately prints the travel planner banner and waits for terminal input.
4. If run under pytest, the test process fails with an `OSError` because stdin is captured.

## Expected Result

The module should import without prompting the user for input. The CLI interaction should only happen when the script is explicitly executed as a command entry point.

## Actual Result

The module triggers `input()` during import. This blocks test execution and prevents automated validation.

## Error Messages

- `pytest: reading from stdin while output is captured! Consider using -s.`
- `OSError: pytest: reading from stdin while output is captured!`

## Screenshot

Not captured.

## Logs

Observed during pytest:

- `Please enter the country you want to visit:`
- `OSError: pytest: reading from stdin while output is captured!`

## Root-Cause

The script’s startup code is executed at the module level instead of being wrapped in a `main()` guard.

## Recommended Fix

Wrap the CLI logic in a `if __name__ == "__main__":` block so the module remains import-safe and testable.

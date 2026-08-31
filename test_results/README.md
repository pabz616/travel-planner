# Test Results Index

This directory documents the issues identified in the current planner implementation.

## Issues

1. [Import-time CLI input blocks test execution](01_import-time-cli-input-blocks-test-execution.md) — Severity: High | Priority: P1
2. [Negative or invalid day input is not validated before API call](02_negative-day-input-is-not-validated.md) — Severity: Medium | Priority: P2
3. [Unverified model list and retry behavior reduce reliability](03_risky-model-list-and-fallback-logic.md) — Severity: Medium | Priority: P2
4. [Invalid or malformed AI responses are assumed to be valid JSON](04_no-guard-against-malformed-ai-json.md) — Severity: High | Priority: P1
5. [Map markers are created but never attached to the map instance](05_map-markers-created-but-not-added-to-map.md) — Severity: Medium | Priority: P2

## Notes

- The findings are based on the current implementation and observed test behavior.
- These entries are intentionally written as actionable issue reports for follow-up fix work.

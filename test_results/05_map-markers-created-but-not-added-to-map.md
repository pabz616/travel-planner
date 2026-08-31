# Map markers are created but never attached to the map instance

## Description

The code builds `folium.Marker(...)` objects for each location but never adds them to the `travel_map`. As a result, the internal map may render without the expected markers even though the logic appears to create them.

## Section, URL, or area affected

- `planner.py`
- Interactive map generation section
- Folium map creation logic

## Issue Type

Functional

## Severity

Medium

## Priority

P2

## Frequency of occurrence

Always when the map is generated with non-empty place data.

## Steps to reproduce

1. Run the planner and generate a valid plan.
2. Reach the interactive map section.
3. Observe that markers are allocated but not attached to the map.

## Expected Result

Every place should appear as a clickable marker on the rendered map.

## Actual Result

The code creates markers but never calls `add_to(travel_map)`, so the map does not reflect the data.

## Error Messages

No direct error message; the bug is functional rather than exceptional.

## Screenshot

Not captured.

## Logs

No map-level error was produced.

## Root-Cause

The marker objects are instantiated but not attached to the `folium.Map` instance.

## Recommended Fix

Call `marker.add_to(travel_map)` inside the loop that builds markers.

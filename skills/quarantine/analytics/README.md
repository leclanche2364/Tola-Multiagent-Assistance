# analytics

## Trigger
Activated when the agent needs to retrieve or interpret analytics data. Fires before any analytics query is processed.

## Purpose
Provide structured access to analytics metrics and reports without exposing raw data dumps.

## Behaviour Rules
1. Analytics data must be aggregated before being presented to the model.
2. Return compact structured summaries, never raw row dumps.
3. All analytics retrieval is read-only — no write capability.

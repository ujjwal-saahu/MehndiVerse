"""The AI foundation — see docs/ai-foundation.md.

A deliberately self-contained package: every other part of the app that
needs an AI capability (design routes, admin routes, the background-job
worker) imports from here, never from a specific provider or job-table
implementation directly. This is the same "isolated module behind a
narrow interface" shape `app/services/payments/` and `app/services/search/`
already established — swapping the local heuristic provider for a real
cloud AI provider later, or the DB-table job queue for Celery/RQ, should
only ever mean changing files inside this package.
"""

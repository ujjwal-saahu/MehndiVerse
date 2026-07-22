"""Product analytics and recommendations — see docs/analytics-and-
recommendations.md.

A self-contained package, the same "isolated module behind a narrow
interface" shape `app/services/ai/` and `app/services/payments/` already
established: `events.py::record_event` is the only way anything in this
codebase writes an `AnalyticsEvent`, and every recommendation/reporting
module here only ever reads through the small set of functions in this
package — no route or other service reaches into `AnalyticsEvent` directly.
"""

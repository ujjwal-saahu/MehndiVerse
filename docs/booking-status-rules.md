# MehndiVerse — Booking Status Transition Rules (superseded)

Status: Superseded by [booking-lifecycle.md](booking-lifecycle.md) (Phase 13)
Last updated: 2026-07-19

This document described the Phase 2 placeholder 8-status booking lifecycle
(`requested → quoted → confirmed → completed`, plus `cancelled`/`disputed`/
`declined`/`expired`) before any booking-creation code existed. Phase 13
replaced it with a full 15-status state machine and the service layer that
enforces it — see **[booking-lifecycle.md](booking-lifecycle.md)** for the
current source of truth on booking states, transitions, quotes, cancellation,
rescheduling, and overlap prevention.

Kept as a stub (rather than deleted) since older docs still link here by
filename; update your links to point at booking-lifecycle.md going forward.

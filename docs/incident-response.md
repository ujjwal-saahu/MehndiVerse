# MehndiVerse — Incident Response Plan

Companion to [docs/security-review.md](security-review.md) and [docs/threat-model.md](threat-model.md). This is the operational plan for when a security incident is suspected or confirmed — MehndiVerse has no dedicated security team yet, so this assumes the on-call engineer(s) run it directly.

## 1. Severity levels

| Level | Definition | Examples | Response time |
|---|---|---|---|
| **SEV-1 — Critical** | Active data breach, credential/secret compromise, or full service outage caused by an attack | Service-role key leaked; mass unauthorized account access; payment data exposure | Immediate, all-hands |
| **SEV-2 — High** | Confirmed vulnerability being actively exploited, or a contained breach affecting a limited user set | Account takeover of specific users; RLS/authorization bypass confirmed in production | Within 1 hour |
| **SEV-3 — Medium** | Vulnerability discovered but no evidence of exploitation; abuse pattern detected but contained by existing controls | Login-lockout triggering unusually often against one account; a dependency CVE disclosed | Within 1 business day |
| **SEV-4 — Low** | Hardening opportunity, no immediate risk | A missing security header on a low-traffic route; a `pip-audit` moderate-severity finding with no known exploit | Next scheduled review |

## 2. Roles

Until a dedicated security team exists, these are responsibilities, not job titles:

- **Incident Commander (IC)** — whoever first triages the report; coordinates the response, owns the timeline, decides on severity/escalation. Does not have to be the person who fixes the issue.
- **Responder(s)** — engineer(s) actually investigating/fixing.
- **Communicator** — drafts and sends any user-facing or stakeholder notification (may be the same person as the IC for small incidents).

## 3. Detection sources

- CI failures from `pip-audit`, `npm audit`, or `gitleaks` (dependency-scan / secret-scan jobs in `.github/workflows/ci.yml`).
- `AuditLog` entries with `action` in `login.lockout_triggered`, `session.revoke_all`, `account.deletion_requested` — reviewable via `GET /admin/audit-logs` (admin/super_admin only).
- Structured application logs (structlog JSON, redacted per docs/security-review.md#sensitive-log-redaction) — `app_error`/`unhandled_exception` events at unusual volume.
- Direct reports: a user, a security researcher, or a payment-provider webhook anomaly.
- Manual code review / this phase's security-review process.

## 4. Response process

### Step 1 — Triage (first 15 minutes)

1. Confirm the report is real (reproduce if safely possible; don't speculate from an unverified claim).
2. Assign a severity level (§1).
3. For SEV-1/SEV-2: **contain first, investigate second**. Containment options, roughly in order of how disruptive they are:
   - Revoke a specific user's sessions: `POST /auth/sessions/revoke-all` (as that user, or an admin-initiated equivalent once one exists — see §6).
   - Rotate the suspected-compromised secret (Supabase JWT secret, service-role key, Razorpay keys, AI provider key) via the hosting platform's secret manager — **never** by editing a committed file, per docs/security-baseline.md#3.
   - Suspend the affected account(s): existing `admin_users.py::suspend_user`.
   - Disable the affected route/feature at the load balancer or via a feature flag, if one exists for it.
   - As a last resort for an active, unconfined breach: take the API offline.

### Step 2 — Investigate

4. Pull the relevant `AuditLog` rows (`GET /admin/audit-logs?action=...&actor_id=...`) and structured logs for the affected time window.
5. Determine: what was accessed/changed, which accounts/records are affected, how the attacker got in (which control failed or was missing).
6. Check whether the same class of issue exists elsewhere (e.g., if one endpoint was missing a `require_roles()` check, grep for the same pattern across other routes).

### Step 3 — Remediate

7. Fix the root cause, not just the symptom (per this project's engineering rules — no `--no-verify`-style shortcuts).
8. Add a regression test that would have caught it, mirroring this phase's pattern (`tests/core/`, `tests/auth/`).
9. If a secret was exposed: rotate it, and confirm the old value no longer works.
10. If user data was exposed: identify exactly which users/records, for the notification step below.

### Step 4 — Communicate

11. **Internal**: the IC keeps a running timeline (what was known when, what action was taken when) — needed for the post-mortem and, if applicable, for a compliance/legal review.
12. **User-facing**: required when personal data was actually exposed or accounts were compromised, not merely "a vulnerability existed." Notify affected users (not the whole user base, unless scope is unknown) with: what happened, what data was involved, what MehndiVerse did about it, what the user should do (e.g., reset password, review recent activity via revoke-all-sessions).
13. **Regulatory**: data-breach notification obligations depend on the jurisdiction(s) of affected users — flagged as an open question in docs/security-baseline.md#9/product-requirements.md's deferred decisions; if a real incident occurs, get this confirmed before or in parallel with user notification, not after.

### Step 5 — Post-mortem

14. Blameless written summary within a few days of resolution: timeline, root cause, impact (who/what was affected), what fixed it, what regression test now guards it, what (if anything) should change in process to catch this class of issue earlier.
15. Update [docs/threat-model.md](threat-model.md) if the incident revealed a threat/mitigation gap that document didn't cover.

## 5. Specific playbooks

### Leaked secret (JWT secret, service-role key, payment key, AI provider key)

1. Rotate the secret at the source (Supabase dashboard for JWT/service-role/anon keys; Razorpay dashboard for payment keys; provider dashboard for AI keys).
2. Update the hosting platform's secret manager with the new value; redeploy.
3. Rotating the Supabase JWT secret invalidates *every* existing session app-wide — expected and correct for this scenario, not a bug to work around.
4. Confirm via `gitleaks` (or a manual search) that the old value isn't still present anywhere in git history if it was ever committed; if it was, treat the secret as permanently compromised even after removal from the working tree (git history retains it) and rotation is mandatory regardless of whether it was ever actually misused.

### Suspected account takeover

1. Confirm via `AuditLog`/login history whether the access pattern is genuinely anomalous.
2. Revoke all sessions for the account (`POST /auth/sessions/revoke-all` — requires the account's own current password, so if the attacker already has full control including the password, an admin-side forced revocation is needed instead; this codebase does not yet have an admin-initiated force-revoke endpoint — recommended follow-up, see §6).
3. Trigger a password reset for the user (`POST /auth/password-reset/request`).
4. Review what the attacker did while in the account (bookings created, messages sent, profile changes) via `AuditLog` and relevant tables' own timestamps.

### Authorization/RLS bypass discovered

1. Identify every route/table affected, not just the one reported.
2. Add the missing `require_roles()`/RLS policy immediately (this is a code fix, deploy it as the containment step, not after).
3. Audit what was actually accessed through the gap while it existed (best-effort, from logs — RLS/authorization gaps don't necessarily leave their own audit trail, which is itself a lesson to fold into the post-mortem).

### Payment webhook anomaly (signature failures, unexpected event volume)

1. `handle_webhook` already rejects anything that fails HMAC verification (400, never processed) — a spike in these is either a misconfigured webhook secret (check it matches the provider dashboard) or a spoofing attempt, not by itself a breach.
2. Cross-check against Razorpay's own dashboard/logs for the same window to distinguish "our secret is wrong" from "someone is probing us."

## 6. Known gaps to close before this plan is fully load-bearing

- No admin-initiated "force revoke all sessions for account X" endpoint yet (only self-service, reauth-gated) — needed for the account-takeover playbook when the attacker controls the password.
- No paging/alerting wired to `AuditLog` suspicious-event types yet — detection today is manual (an admin querying `/admin/audit-logs`) or via CI job failure, not real-time.
- Regulatory notification obligations are not yet resolved for any specific jurisdiction (see docs/security-baseline.md#9).

## Related documents

- [docs/security-review.md](security-review.md)
- [docs/threat-model.md](threat-model.md)
- [docs/security-baseline.md](security-baseline.md)

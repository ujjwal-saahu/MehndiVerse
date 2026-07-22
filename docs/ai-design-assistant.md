# MehndiVerse — Personalized AI Design Assistant (Phase 21)

Phase 21 adds a customer-facing generative-design feature on top of Phase 20's AI foundation (`apps/api/app/services/ai/`): a structured form (style/occasion/body part/difficulty/density/symmetry/pattern elements/theme/personalization/additional instructions) that gets turned into a prompt, generated in the background, moderated, and made available for the user to view, retry, save, share, or send to an artist — with every generated result clearly labeled as AI-generated, never as a human artist's work.

This phase reuses Phase 20's job queue (`AiJob`), request-record table (`AiGeneration`), quota system (Phase 18's entitlements), and moderation hook (`AiProvider.moderate_image`) rather than building parallel infrastructure — the only new pieces are the structured-form table (`AiDesignRequest`), the prompt-construction/moderation logic, and one new provider method (`generate_design_image`).

## Structured form

`app/schemas/ai_design.py::DesignGenerationRequest` — the ten fields the task asked for, each independently validated:

| Field | Type | Notes |
|---|---|---|
| `style` | free text (≤100 chars) | e.g. "Arabic", "Indian bridal", "minimalist" — too varied for a fixed enum |
| `occasion` | `BookingEventType` enum | reuses the *existing* booking-event taxonomy (wedding/engagement/festival/baby_shower/party/corporate_event/other) rather than inventing a parallel one |
| `body_placement` | `BodyPlacement` enum | reuses the *existing* design-catalog taxonomy (hand/foot/arm/back/other) |
| `difficulty_level` | `DesignDifficulty` enum | reuses the *existing* design-catalog taxonomy (beginner/intermediate/advanced) |
| `density` | `PatternDensity` enum (new) | light/medium/bold/intricate — no existing enum fit, so this phase adds one |
| `is_symmetric` | bool | symmetric vs. asymmetric/freeform layout |
| `pattern_elements` | list[str] (≤10 items, ≤40 chars each) | e.g. `["peacock", "paisley", "mandala"]` |
| `theme` | free text, optional (≤100 chars) | e.g. "royal", "floral", "nature" |
| `personalization_text` | free text, optional (≤50 chars) | initials or a short phrase to incorporate |
| `additional_instructions` | free text, optional (≤500 chars) | freeform extra guidance |

Reusing `BookingEventType`/`BodyPlacement`/`DesignDifficulty` instead of inventing occasion/body-part/difficulty enums specific to this feature means a design generated here speaks the same vocabulary as the rest of the catalog (bookings, designs) — a future feature correlating "what customers ask the AI for" against "what artists actually book" doesn't need a translation table.

Every enum field is typed as the actual `StrEnum` in the Pydantic schema, so an invalid value is rejected with a normal `422` before the request reaches any service code — on top of the `CHECK` constraint the database itself enforces on `AiDesignRequest`, the same belt-and-suspenders pattern every other enum-backed column in this codebase uses.

## Request validation

Three layers, each catching something the previous one can't:

1. **Pydantic** (`DesignGenerationRequest`) — types, enum membership, length caps, list size caps. Runs before any code in this phase's routes executes.
2. **Prompt moderation** (`moderate_form_text`, see [Moderate prompts and outputs](#moderate-prompts-and-outputs)) — content-safety keyword check on every free-text field, before quota is charged or any job is enqueued.
3. **Database `CHECK` constraints** — the same enum/positivity constraints as every other table in this codebase, as a backstop against anything that reaches the database through a path other than the validated route (defense in depth, not the primary gate).

## Prompt construction

`app/services/ai/design_generation.py::build_prompt()` deterministically folds every structured field into one plain-English instruction:

```
A bold Arabic mehndi (henna) design for a wedding, intended for the hand,
at intermediate difficulty. Symmetric layout. Include these pattern
elements: peacock, paisley. Theme: royal. Tastefully incorporate the
following initials or text into the design: "R+K". Leave space at the
wrist for a bracelet. Traditional henna line-art style, brown henna paste
on skin, no text overlays, no watermarks.
```

The constructed prompt — never the raw form fields — is what's sent to the provider, and it's stored verbatim on `AiDesignRequest.prompt` (and mirrored into `AiGeneration.request_payload`) for auditability: given a result, you can always see exactly what was asked for, without reconstructing it from the structured fields.

## Provider abstraction

`app/services/ai/provider.py::AiProvider` (Phase 20) gains one new abstract method:

```python
def generate_design_image(self, *, prompt: str, allow_training: bool = False) -> DesignImageResult: ...
```

`DesignImageResult` (`provider`, `model`, `image_bytes`, `content_type`, `width`, `height`, `cost_usd`) mirrors the shape of Phase 20's other result dataclasses (`TagSuggestionResult`, `EmbeddingResult`, `ModerationResult`) — `cost_usd` is always populated (`0.0` for a provider with no real per-call cost) rather than left `None`, so cost reporting never has to special-case "the provider didn't say."

### Keep generation provider replaceable

`LocalHeuristicProvider.generate_design_image` (the only implementation today, selected by `ai_provider = "local"`) renders a deterministic radial henna-motif image with Pillow — concentric "petal" arcs whose count/size/stroke color derive from a hash of the prompt, so the same prompt always produces the same image (useful for tests) while different prompts visibly differ. This is honestly not a generative model; it's a real, working rendering behind the same interface a real one would sit behind. Swapping in a real text-to-image provider (DALL-E, Stable Diffusion, a hosted API) later means writing one new module implementing `AiProvider` and adding one branch to `app/services/ai/factory.py::get_ai_provider()` — no route, job, or capability-module code changes, exactly the guarantee Phase 20 already established for tagging/embeddings/moderation.

`allow_training` is accepted by every implementation (including the local one, which has nothing to honor it with) specifically so a real provider's implementation is the one place that decision can actually be acted on — see [Consent for provider training](#consent-for-provider-training).

## Background generation

Reuses Phase 20's job queue exactly (`app/services/ai/jobs.py` — DB-table queue, `SELECT ... FOR UPDATE SKIP LOCKED` claiming, exponential backoff, `python -m app.cli.process_ai_jobs` worker). `create_design_request()` does one `AiGeneration` INSERT, one `AiDesignRequest` INSERT, one `AiJob` INSERT (`job_type = "design_generation"`), commits, and returns `202 Accepted` — the actual provider call happens later in the separate worker process, so a slow/hanging provider can never hold up a request-handling API worker. `app/services/ai/handlers.py` registers this capability's `process_job` alongside Phase 20's four.

## Job status

`GET /ai/designs/{id}` returns the current state by joining `AiDesignRequest` with its linked `AiGeneration` (`status`: pending/processing/completed/failed; `provider`/`model_name`/`cost_usd` once known; `error_message` if failed). A client polls this endpoint the same way it would poll Phase 20's `GET /ai/generations/{id}`.

## Generation history

`GET /ai/designs` — cursor-paginated (same keyset-pagination shape every other list endpoint in this codebase uses), scoped to the caller's own requests, newest first. `DELETE /ai/designs/{id}` soft-deletes an entry a user doesn't want in their history anymore (mirrors `PreviewProject`'s deletability from Phase 19) — the underlying `AiGeneration` audit row is never deleted, only the user-facing `AiDesignRequest` is.

## Result moderation

### Moderate prompts and outputs

Two independent checks, one on each end of generation:

- **Prompt-side** (`moderate_form_text`, runs inside `create_design_request` before quota is charged or any job is enqueued): a deliberately small, foundation-level keyword blocklist across every free-text field (`style`, `theme`, `personalization_text`, `additional_instructions`, `pattern_elements`). Real content-safety classification needs a trained model; this catches the most obviously disallowed requests without one — the same "heuristic foundation, not a classifier" precedent `app/services/ai/local_provider.py` already sets for image moderation. A rejected prompt never reaches a provider and never costs the user a generation credit.
- **Output-side** (`process_job`, after the provider returns an image): the generated image is run through the *same* `AiProvider.moderate_image` hook Phase 20 built for catalog images. A flagged or low-confidence result sets `AiGeneration.requires_human_review = True` / `review_status = pending` — exactly Phase 20's [human-review](ai-foundation.md#human-review) mechanism, reused verbatim rather than duplicated. Staff resolve it through the existing `POST /admin/ai/review-queue/{id}/resolve` endpoint; nothing here is a new moderation surface.

A `review_status` of `rejected` (staff has explicitly rejected the result) blocks `send_design_request_to_artist` — you cannot forward something staff has already rejected to an artist. It does **not** block the owner from viewing their own result, or from sharing a signed link to it themselves — the same "never auto-hide from the creator, human decides for distribution" balance Phase 20 struck for duplicate-detection matches.

## Save result

`POST /ai/designs/{id}/save` / `DELETE /ai/designs/{id}/save` set/clear `AiDesignRequest.is_saved` + `saved_at`. Not every generation a user makes is one they want to keep — explicit "save" is how they mark the ones that matter, distinct from the full (unfiltered) generation history.

## Share result

`GET /ai/designs/{id}/share` mints a short-lived (1-hour) signed URL into the private `ai-generated-designs` storage bucket — mirrors `PreviewProject.share_preview` exactly (Phase 19), including the "never persist the signed URL, mint a fresh one on every read" discipline. Requires a completed result (`422` otherwise) and the caller to be the request's owner.

## Send result to artist

`POST /ai/designs/{id}/send-to-artist` mirrors `PreviewProject.send_to_artist` (Phase 19) exactly: the caller must be the booking's customer, a conversation is created if needed, `AiDesignRequest.shared_with_booking_id` is set (granting that booking's artist read access via `require_viewable`, the same pattern `previews.py` uses), and a **text-only** message is sent — never a durable `attachment_url`, since the result lives in a private bucket behind short-lived signed URLs that would go stale sitting in a message row. The artist views the actual image by opening the app, which mints a fresh signed URL on read, same as the owner does.

## AI-generated label

`AiDesignRequest.is_ai_generated` is a column that is always `True` — stored explicitly, not just implied by the table's existence, so a schema/serializer bug can never silently drop the label. Every `AiDesignRequestOut` response includes both `is_ai_generated: true` and a literal `ai_generated_label` string (`app/services/ai/design_generation.py::AI_GENERATED_LABEL`: *"AI-generated design — not created by a human artist."*). The same literal string is included in the `send_to_artist` message body, so the label travels with the content wherever it goes — an API response, a chat message — not just in one response shape. This is the concrete mechanism behind "do not claim an AI design was made by a human artist": there is no code path in this feature that produces a `Design` catalog entry, an artist-attributed portfolio piece, or any other representation that could imply human authorship — generation results only ever exist as `AiDesignRequest` rows, always labeled.

## Subscription quota

Reuses Phase 18's entitlements system exactly (`app/services/entitlements.py::check_and_increment_usage`, `UsageType.AI_GENERATION`, `limit_key = "ai_credits_per_month"`) — the identical quota Phase 20's freeform `create_ai_generation` already gates on. A user past their plan's monthly AI-credit quota gets `403` before any row is written for a new request, and again before a retry (see below) — a retry is a genuine new provider call and costs a fresh credit exactly like the original request did.

## Generation failure and retry flow

`AiDesignRequest.retry_count` / `max_retries` (default `settings.ai_design_request_max_retries = 3`) — a hard, per-request ceiling that exists specifically to "prevent unlimited retries," independent of (and stacked with) the monthly quota above. `POST /ai/designs/{id}/retry`:

- Only allowed when the linked `AiGeneration.status == "failed"` — a completed result isn't "retried" (the user would start a new request instead); `422` otherwise.
- Only allowed while `retry_count < max_retries`; `429` once exhausted, with a message pointing the user at starting a new request.
- Consumes a fresh quota credit (same 403-on-exhaustion behavior as the original request).
- Resets the *existing* `AiGeneration` back to `pending` and enqueues a *new* `AiJob` against it — history stays as one row per original request (with `retry_count` visible), not a proliferating chain of near-duplicate entries.

This is layered on top of, not a replacement for, `AiJob`'s own system-level retry/backoff (Phase 20): a transient failure (e.g. a storage hiccup) is retried automatically by the job queue itself, up to `ai_job_max_attempts` (default 3), before the `AiGeneration` ever reaches a user-visible `failed` state that this retry flow would apply to.

## Record cost and usage metadata

`AiGeneration.cost_usd` and `latency_ms` (Phase 20 columns, populated for the first time by a capability that has real per-call cost/timing semantics) are set from the provider's own `DesignImageResult.cost_usd` and a wall-clock measurement around the `generate_design_image` call, every time a job completes. `UsageRecord` (Phase 18) already tracks monthly usage counts per user via `check_and_increment_usage` — no new usage-tracking table was needed. Together these answer "how much did this cost" and "how many has this user made this period" without any new schema.

## Consent for provider training

`AiDesignRequest.allow_provider_training` defaults to `False` and is **never** inferred from a subscription tier, a role, or any other implicit signal — the caller must explicitly set it `True` in the request body. It is passed verbatim to `AiProvider.generate_design_image(..., allow_training=...)`; the local provider has nothing to honor it with (it doesn't train on anything, ever), but a real cloud provider's implementation is the only place this flag can actually be acted on (e.g. passed through as an API parameter that opts an image out of — or into — a training dataset). This phase involves no uploaded user photos at all (the form is entirely text; nothing like a hand/foot photo is ever sent to a provider here, unlike Phase 19's preview feature), so the "private user images" the requirement refers to are, at minimum, never at risk from this feature's inputs — the consent flag exists for the generated *output* and for forward-compatibility with any future feature that does send user images through this same provider abstraction.

## Settings reference

Added to `app/core/config.py`:

| Setting | Default | Purpose |
|---|---|---|
| `ai_design_rate_limit` | `"10/minute"` | Rate limit on `POST /ai/designs` — tighter than Phase 20's general `ai_rate_limit` since this endpoint both enqueues a job and consumes a quota credit. |
| `ai_design_request_max_retries` | `3` | The hard per-request retry ceiling — see [Generation failure and retry flow](#generation-failure-and-retry-flow). |

Reused from Phase 20 without changes: `ai_provider`, `ai_provider_timeout_seconds`, `ai_job_max_attempts`, `ai_job_stuck_after_seconds`, `ai_moderation_review_confidence_threshold`.

## API surface

- `POST /ai/designs` — create a request (rate-limited, quota-gated, prompt-moderated).
- `GET /ai/designs` — generation history (own requests only, cursor-paginated).
- `GET /ai/designs/{id}` — job status / detail (owner, or the artist a result was shared with).
- `POST /ai/designs/{id}/retry` — retry a failed request (owner only, capped).
- `POST /ai/designs/{id}/save`, `DELETE /ai/designs/{id}/save` — save/unsave (owner only).
- `GET /ai/designs/{id}/share` — short-lived signed share URL (owner only).
- `POST /ai/designs/{id}/send-to-artist` — attach to a booking conversation (owner only, booking must be the caller's own).
- `DELETE /ai/designs/{id}` — remove from history (owner only, soft delete).

## Storage

New private Supabase Storage bucket `ai-generated-designs` (`infrastructure/supabase/storage_policies.sql`), owner-read/owner-delete policies mirroring `preview-projects` (Phase 19) exactly. Written only by the background worker (the service-role key, which bypasses RLS), never uploaded directly by a client — there is no owner-write policy, unlike `preview-projects`, since nothing here ever accepts a client-supplied image.

## What this phase deliberately does not do

- **No catalog publishing.** A generated result never becomes a `Design` row, an artist-attributed portfolio piece, or anything else that could imply human authorship — see [AI-generated label](#ai-generated-label).
- **No real cloud provider.** `LocalHeuristicProvider.generate_design_image` is a genuine, deterministic rendering, not a trained text-to-image model.
- **No image-input generation.** The form is entirely text/structured fields; no photo upload is part of this feature (unlike Phase 19's hand/foot preview).
- **No new moderation surface.** Result moderation reuses Phase 20's `AiGeneration.review_status`/admin review-queue verbatim; nothing new for staff to learn.

## Related documents

- docs/ai-foundation.md — the provider abstraction, job queue, and human-review mechanisms this phase builds directly on top of.
- docs/hand-foot-preview.md — the save/share/send-to-artist shape this phase's equivalents are mirrored from.
- docs/subscriptions-and-entitlements.md — the quota system reused for both the original request and each retry.

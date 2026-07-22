# MehndiVerse — AI Foundation (Phase 20)

Phase 20 adds a self-contained AI module (`apps/api/app/services/ai/`) that gives every future AI-powered feature the same starting point: a provider abstraction, a request/usage ledger, a background-job queue, and five real (if heuristic) capabilities — automatic tag suggestion, image embeddings, similar-design search, duplicate-image detection, and moderation hooks — plus recommendation-event collection and a quota-enforcement foundation reused from Phase 18's entitlements system.

**This phase deliberately does not implement image generation.** `AiGenerationType.GENERATIVE_DESIGN` exists as an enum value (carried over from Phase 2/18 scaffolding) but nothing in this phase produces images from it — that is explicit future scope.

## Provider abstraction

`app/services/ai/provider.py` defines `AiProvider`, an ABC with three methods every provider must implement:

```python
class AiProvider(ABC):
    name: str
    def suggest_tags(self, *, image_bytes: bytes, existing_tags: tuple[str, ...] = ()) -> TagSuggestionResult: ...
    def generate_embedding(self, *, image_bytes: bytes) -> EmbeddingResult: ...
    def moderate_image(self, *, image_bytes: bytes) -> ModerationResult: ...
```

`app/services/ai/factory.py::get_ai_provider()` reads `settings.ai_provider` and constructs the matching implementation — the *only* place that picks a concrete provider. Every capability module (`tagging.py`, `embeddings.py`, `moderation.py`) calls `get_ai_provider()`, never a concrete class directly. This mirrors `app/services/payments/factory.py` and `app/services/search/factory.py` exactly: adding a real cloud AI provider later means adding one new module and one `if` branch here, with no caller changes.

Every result type (`TagSuggestionResult`, `EmbeddingResult`, `ModerationResult`) is a frozen dataclass carrying `provider` and `model` fields — this is how "store model and provider metadata" (a hard requirement of this phase) reaches the database without every capability module repeating the bookkeeping.

## Local heuristic provider

`app/services/ai/local_provider.py::LocalHeuristicProvider` (`ai_provider = "local"`, the default) is the only implementation shipped in this phase. It is a *real*, deterministic, dependency-light implementation — not a stub that returns fixed values — built entirely on Pillow, with no network call and no API key:

- **Embeddings**: an 8×8 grayscale downsample (64 values) concatenated with a 4×4 RGB downsample (48 values) = a 112-dimension vector, each component normalized to `[0, 1]`. This is a perceptual-hash-style fingerprint: visually similar images produce nearby vectors; it is not a trained model and makes no claim to semantic understanding.
- **Tag suggestion**: classifies the image's average color against twelve mehndi-catalog-relevant named buckets (black, brown, red, orange, gold, cream, white, gray, green, blue, pink, purple), its aspect ratio into orientation (landscape/portrait/square), and its grayscale pixel variance into density (bold/delicate). Each candidate gets a confidence score; tags the design already carries are excluded.
- **Moderation**: flags an image whose grayscale variance is far below what a real photograph typically has (a common signature of a broken upload, a placeholder, or a blank/near-solid image) or whose dimensions are implausibly small. This is a signal-quality pre-filter, not a content classifier — see [Moderation hooks](#moderation-hooks) below for what it is and is not responsible for.

`cosine_similarity(a, b)` is exported alongside the provider and shared by `similarity.py` and `duplicates.py` so both compare `DesignEmbedding` vectors identically. It clamps its result to `[0, 1]` — every component here is non-negative, so the true value is always in that range, but floating-point drift on a near-identical pair can push the raw dot-product a hair over `1.0`, which would violate `DesignDuplicateMatch.similarity`'s database check constraint if left unclamped.

Swapping this for a real cloud provider later (OpenAI embeddings, a vision moderation API, etc.) means writing one new module implementing `AiProvider` and adding one branch to `factory.py` — no route, job, or capability-module code changes.

## Never expose provider keys

`settings.ai_provider_api_key` exists as a placeholder for a future real provider. It is read only inside that provider's own module (never today, since the local provider needs no key), is never logged, and is never included in any API response — `AiGeneration`/`AiJob` only ever store `provider` (a short name like `"local"`) and `model_name` (like `"local-heuristic-v1"`), never a credential. The same discipline Phase 15 established for `razorpay_key_secret` applies here.

## AI request records

`AiGeneration` (`app/db/models/ai.py`) is the append-only log every AI call in this module writes to, for audit and future cost tracking — one row per discovery query, tag-suggestion run, embedding computation, duplicate check, or moderation check. Its `entity_type`/`entity_id` columns are a polymorphic reference to whatever the call is *about* (a `Design`, for every capability in this phase), mirroring `Report.reported_entity_type`/`reported_entity_id`'s precedent from Phase 16.

Two status concepts live on this one row, and they are orthogonal:

- **`status`** (`AiGenerationStatus`: `pending` → `processing` → `completed`/`failed`) tracks the *job's* lifecycle.
- **`review_status`** (`AiReviewStatus`: `not_required`/`pending`/`approved`/`rejected`) tracks whether the *outcome* needs a human. A moderation check can be `completed` as a job while its result sits `pending` review — see [Human review](#human-review).

`provider`, `model_name`, `cost_usd`, `latency_ms`, `attempt_count`/`max_attempts`, and `confidence` all live on this table, giving every future cost/quality dashboard a single source of truth without joining across job tables.

## Background job processing

No task-queue infrastructure (Celery/RQ/etc.) is provisioned in this environment — the same constraint every prior phase's "queued work" has run into. Rather than running provider calls inline inside a request (which would violate "AI calls must not block normal API workers"), this phase adds a small, durable, DB-table-backed queue: `AiJob` (`app/db/models/ai.py`), processed by `app/services/ai/jobs.py` and driven by the CLI worker `python -m app.cli.process_ai_jobs`.

**Enqueuing** (`enqueue_job`) is a single fast INSERT — any route that triggers a capability just enqueues and returns; the actual provider work happens in the separate worker process.

**Claiming** (`claim_due_jobs`) uses the standard safe pattern for concurrent queue consumers:

```sql
SELECT ... FROM ai_jobs WHERE status = 'pending' AND next_run_at <= now()
ORDER BY next_run_at LIMIT :n FOR UPDATE SKIP LOCKED;
-- then:
UPDATE ai_jobs SET status = 'running', ... WHERE id IN (:ids) AND status = 'pending';
```

`FOR UPDATE SKIP LOCKED` plus a conditional `UPDATE ... WHERE status = 'pending'` means more than one `process_ai_jobs` process can run at once without ever double-processing a job — no Redis-as-a-queue or external broker required.

**Retrying** (`fail_job`): a failed job is retried with exponential backoff (`60s × 2^attempt`, capped at one hour) until `attempt_count >= max_attempts` (default `ai_job_max_attempts = 3`), at which point it — and the `AiGeneration` it belongs to — moves to a terminal `failed` state with the error message recorded. Nothing is retried forever, and nothing is silently dropped.

**Dispatch** (`process_due_jobs`) claims a batch, looks up each job's handler in a plain dict registry (`register_handler`/`_HANDLERS`, populated by `app/services/ai/handlers.py`'s side-effect-only imports), and runs it synchronously in the caller's own session. A handler exception never crashes the worker loop — it's caught, the job is failed/retried, and the loop continues to the next job.

### Why handlers run synchronously (and where the actual timeout lives)

An earlier version of this module ran each handler in a `ThreadPoolExecutor` with its own freshly-opened database session, specifically to enforce a hard wall-clock timeout around provider calls. That design was abandoned: a `Session` is not safe to hand to a worker thread while the caller's thread might still be using it, and Python cannot forcibly cancel a thread that's still running once `.result(timeout=...)` gives up waiting on it — the "hard timeout" would have been fake safety. Handlers now run in-line, in the same session and thread that claimed the job. See [Timeouts are soft](#timeouts-are-soft) for how a real timeout is still enforced.

## Timeouts are soft

The actual timeout enforcement lives one layer down from the job queue, at the only place in this whole module that talks to the network: `app/services/ai/imaging.py::fetch_image_bytes`, which wraps its `httpx.Client` call in `settings.ai_provider_timeout_seconds` (default 15s). If a provider or image host hangs, that `httpx` timeout is what actually cuts the request off.

That still leaves a gap: what if the *worker process itself* dies or hangs mid-handler, after claiming a job but before it finishes? `requeue_stuck_jobs()` is the backstop — it scans for `AiJob` rows left `running` with a `started_at` older than `ai_job_stuck_after_seconds` (default 300s), and resets them (to `pending` for another attempt, or `failed` if attempts are exhausted). This is the same "reconciliation" shape `app/services/payments/service.py::reconcile_pending_payments` already uses for the analogous "did the external step actually finish" problem — see docs/payments.md#10-reconciliation-command. `python -m app.cli.process_ai_jobs` runs this pass before every batch of `process_due_jobs`.

## AI calls must not block API workers

This requirement is satisfied structurally, not by anything clever inside a single function: a route that triggers a capability (e.g. `POST /designs/{id}/ai/tag-suggestions`) only ever calls the capability's `enqueue_*` function — one `AiGeneration` INSERT, one `AiJob` INSERT, then `db.commit()` and return `202 Accepted`. All of the actual Pillow decoding, network fetch, and provider computation happens later, in the separate `process_ai_jobs` worker process, which by construction cannot hold up a request-handling worker. The one synchronous exception is [similar-design search](#similar-design-search), which only reads already-computed embeddings and is cheap enough to serve directly.

## Automatic design-tag suggestion

`app/services/ai/tagging.py`. `enqueue_tag_suggestion(db, design=..., triggered_by=...)` creates an `AiGeneration` (`generation_type = "tag_suggestion"`) and an `AiJob` (`job_type = "tag_suggestion"`). The handler fetches the design's primary ready image (`imaging.py::get_primary_ready_image_url`), calls `provider.suggest_tags(image_bytes=..., existing_tags=...)`, and upserts one `DesignTagSuggestion` row per suggested tag.

Suggestions are **never auto-applied** to the design's real `design_tags` join table — they sit in `pending` status until the owning artist or staff explicitly accepts or rejects them (`POST /designs/{id}/ai/tag-suggestions/{suggestion_id}/resolve`, backed by `review.py::resolve_tag_suggestion`). `DesignTagSuggestion` has a `UniqueConstraint(design_id, tag_name)`, making a re-run retry-safe: it refreshes the confidence on an existing `pending` row, and never touches one a human has already `accepted`/`rejected`.

## Image embedding generation

`app/services/ai/embeddings.py`. `enqueue_embedding_generation(db, design=..., triggered_by=...)` enqueues a `job_type = "embedding_generation"` job. The handler fetches the primary image, calls `provider.generate_embedding(...)`, and upserts the design's single `DesignEmbedding` row — `UniqueConstraint(design_id)` makes this idempotent: re-running it for the same design just refreshes the vector rather than creating a duplicate.

On success, the handler chains a [duplicate-detection](#duplicate-image-detection) job for the same design via a local import (`from .duplicates import enqueue_duplicate_detection`, imported inside the function body, not at module top level) — duplicate detection needs an embedding to compare against, so it can only meaningfully run after one exists. This local-import pattern is also how `embeddings.py` and `duplicates.py` avoid a circular top-level import between the two capability modules.

The design's image-upload route (`app/api/routes/designs.py::upload_design_image`) enqueues tag-suggestion, embedding-generation, and moderation jobs together the moment an uploaded image reaches `ready` status — see `_queue_ai_jobs_for_new_image`.

## Similar-design search

`app/services/ai/similarity.py::find_similar_designs(db, design_id=..., limit=10, exclude_design_ids=...)`. Unlike every other capability in this module, this is a **synchronous read, not a job** — it only scans embeddings that already exist (cheap in-process arithmetic, no provider call, no network I/O), so there's nothing to gain by deferring it to a worker. `GET /designs/{id}/ai/similar` calls it directly.

This endpoint requires authentication like every other design read in this codebase (`GET /designs/{id}` also requires a bearer token — there is no anonymous-access pattern here), and enforces the same visibility rule: the query design must be `published`, or the caller must own it or hold a staff role, otherwise `404` (not `403`, to avoid confirming a non-visible design's existence). Matches are filtered to `published` designs only, so an unpublished design that happens to score as "similar" never leaks through the results either.

### Similarity search is a foundation

`find_similar_designs` is an O(n) full scan over every other design's embedding, ranked by `cosine_similarity`. That is acceptable at this phase's expected catalog size and deliberately not optimized further: no pgvector extension is provisioned in this environment (see `DesignEmbedding.embedding`'s plain-JSONB-array column, chosen for exactly this reason), and no approximate-nearest-neighbor index exists. A future phase that needs this to scale past a full scan only needs to change this one function's internals — every caller (the route, `duplicates.py`) is insulated from that change.

## Duplicate-image detection

`app/services/ai/duplicates.py`. `enqueue_duplicate_detection(db, design_id=..., triggered_by=...)` enqueues a `job_type = "duplicate_detection"` job (normally chained automatically from a successful embedding job — see above). The handler compares the design's embedding against every other design's via `cosine_similarity`, and any pair scoring at or above `settings.ai_duplicate_similarity_threshold` (default `0.97`) is upserted as a `DesignDuplicateMatch` row.

A match is `pending` until staff `confirms` or `dismisses` it (`POST /admin/ai/duplicate-matches/{id}/resolve`) — **nothing is ever auto-removed or auto-flagged as a policy violation**; the triggering `AiGeneration` is simply marked `requires_human_review = True` / `review_status = pending`. `DesignDuplicateMatch` has `UniqueConstraint(design_id, matched_design_id)` and a `CHECK (design_id <> matched_design_id)`; note that this is intentionally not symmetric-deduplicated — running detection from both sides of a pair can independently produce both `(A, B)` and `(B, A)` rows, since each row records "when detection ran *for A*, B looked like a duplicate," which is a legitimate, independent fact each direction.

## Moderation hooks

`app/services/ai/moderation.py`. `enqueue_moderation_check(db, design=..., triggered_by=...)` enqueues a `job_type = "moderation_check"` job. The handler calls `provider.moderate_image(...)` and records `is_flagged`, `confidence`, and `categories` onto the triggering `AiGeneration`.

### Moderation hooks are a heuristic foundation

This is explicitly a *hook*, not an auto-moderation pipeline. `LocalHeuristicProvider.moderate_image` can only catch broad signal-quality problems (a near-blank image, an implausibly tiny thumbnail) — it has no ability to detect actual policy violations, and never will without a real trained classifier behind it. Consequently:

- A flagged result never changes a `Design`'s own `status` column directly. It only sets `requires_human_review = True` on the `AiGeneration` row.
- Per this phase's explicit requirement ("require human review for uncertain moderation outcomes"), a result the provider itself is *unsure* about — `confidence` below `settings.ai_moderation_review_confidence_threshold` (default `0.5`) — also routes to human review, even when it isn't flagged. Certainty and cleanliness are two different reasons a result might need a second look, and both are handled the same way.

Staff resolve a pending moderation review the same way they resolve a duplicate match — see [Human review](#human-review).

## Recommendation-event collection

`app/services/ai/recommendations.py::record_event(db, *, event_type, user_id=None, session_id=None, design_id=None, metadata=None)` writes one append-only `RecommendationEvent` row. This phase only *collects* — nothing reads this table to actually recommend anything yet; it exists as raw material for a future recommendation model.

Events split into two collection paths:

- **Server-observed** (`view`, `like`, `save`): recorded automatically at the existing call sites that already know these things happened — `app/services/view_tracking.py::record_design_view`, `app/services/engagement.py::like_design`, and `app/services/engagement.py::add_item_to_collection` (only when adding to the user's *default* "Saved Designs" collection, i.e. a real save, not an arbitrary custom-collection add).
- **Client-reported** (`search_click`, `booking_request`): things that happen after a response has already been sent (a user later taps a search result) that the server has no other way to observe. `POST /ai/events` accepts these two event types only — `view`/`like`/`save` are rejected with `422` to prevent double-counting through both paths.

## AI quota enforcement foundation

Reuses Phase 18's entitlements system (`app/services/entitlements.py::check_and_increment_usage`) rather than inventing a second quota mechanism. `app/services/ai/generations.py::create_ai_generation` (the direct replacement for the old flat `app/services/ai.py` from Phase 18) calls `check_and_increment_usage(db, user=user, usage_type=UsageType.AI_GENERATION.value, limit_key="ai_credits_per_month")` before logging a freeform `AiGeneration` — a user past their plan's monthly AI-credit quota gets a `403` before any row is written.

This quota gate covers the freeform generation types (`design_discovery`, `photo_preview`, `generative_design` — the ones with no dedicated job handler in this phase). The five job-backed capabilities added in this phase (tagging, embeddings, duplicate detection, moderation) are gated by [feature flags](#feature-flags) instead, not per-user credits — they're triggered by the platform (on image upload) or by an artist/staff managing their own content, not a metered "generation" a customer spends credits on.

## Feature flags

`app/services/ai/flags.py`. Reuses Phase 17's `SystemSetting` table (`key`/`value` JSONB, already given a staff read/write surface by `admin_settings.py`) rather than a new flags table or config file — a flag is exactly "a piece of runtime configuration staff can change."

- `is_ai_enabled(db)` reads the `ai.enabled` key; if no row exists, **the default is enabled** (a fresh environment behaves as if AI is on until an operator deliberately turns it off).
- `is_feature_enabled(db, feature)` checks the master flag first, then a per-feature key (`ai.{feature}.enabled`, e.g. `ai.tag_suggestions.enabled`). Turning the master flag off disables every capability regardless of the per-feature flags.

Every route that enqueues a job-backed capability checks `is_feature_enabled` first and returns `503` if the operator has disabled it — see `app/api/routes/ai.py::_require_feature`. The image-upload hook (`designs.py::_queue_ai_jobs_for_new_image`) checks the same flags before enqueuing, so a disabled capability produces zero new jobs, not jobs that silently never process.

## Human review

Two independent things in this module ask a human to look at an AI result, and both follow the same "never act automatically, always leave a record of who decided and why" discipline `app/services/reports.py::resolve_report`/`dismiss_report` established in Phase 16:

- **`AiGeneration.review_status`** (`app/services/ai/review.py::resolve_generation_review`) — set to `pending` by [moderation](#moderation-hooks) (a flagged or uncertain result) or [duplicate detection](#duplicate-image-detection) (a match found). Staff resolve it via `POST /admin/ai/review-queue/{generation_id}/resolve` (`approved`/`notes`), visible to `moderator`/`admin`/`super_admin`, resolvable only by `admin`/`super_admin` — the same view/edit role split `admin_moderation.py` uses for reports.
- **`DesignDuplicateMatch.status`** (`review.py::resolve_duplicate_match`) — resolved separately via `POST /admin/ai/duplicate-matches/{match_id}/resolve` (`confirmed`/`dismissed`), since "is this actually a duplicate" is a more specific decision than the generic review-queue verdict.

Both resolution functions reject a second resolution attempt (`422`) — a decision, once made, is final; re-running detection or moderation creates a *new* `AiGeneration`/match to review rather than reopening an old one.

Resolving is deliberately record-keeping only: neither function unpublishes a design, deletes anything, or suspends anyone. Staff take that action through the existing dedicated surfaces (`designs.py`, `admin_users.py`) after reviewing here — exactly the separation `admin_moderation.py`'s docstring already establishes for reports.

## Retrieval-quality evaluation

`apps/api/tests/ai/test_retrieval_quality.py` evaluates the local provider's embedding quality against a small, hand-built, fully documented synthetic dataset (this environment has no access to a real photo corpus): nine 64×64 solid-color swatches spanning three color families (red, gold, blue; three shades each). For every image used as a query, `find_similar_designs` is asked for its top 2 results, and recall@2 is computed against the expectation that same-family images should rank above different-family ones. The test asserts the mean recall@2 across all nine queries is at least `0.7` — a deliberately low bar meant to catch a similarity-ranking regression, not to benchmark state-of-the-art retrieval quality (the local provider's color-downsample heuristic is not a trained embedding model and isn't being held to that standard).

## Settings reference

All added to `app/core/config.py`:

| Setting | Default | Purpose |
|---|---|---|
| `ai_provider` | `"local"` | Which `AiProvider` `factory.py` constructs. |
| `ai_provider_api_key` | placeholder | Read only by a future real provider; never logged or returned. |
| `ai_provider_timeout_seconds` | `15.0` | Per-call network timeout ([Timeouts are soft](#timeouts-are-soft)). |
| `ai_job_max_attempts` | `3` | Default retry ceiling for a new `AiJob`. |
| `ai_job_stuck_after_seconds` | `300` | Age past which `requeue_stuck_jobs` treats a `running` job's worker as dead. |
| `ai_rate_limit` | `"20/minute"` | Rate limit on the job-enqueuing AI routes. |
| `ai_duplicate_similarity_threshold` | `0.97` | Minimum cosine similarity to record a `DesignDuplicateMatch`. |
| `ai_moderation_review_confidence_threshold` | `0.5` | Below this, a moderation result routes to human review even if not flagged. |

## API surface

- `POST /ai/generations`, `GET /ai/generations/{id}` — freeform quota-gated generations (Phase 18) plus status polling for any `AiGeneration`, job-backed or not.
- `POST /ai/events` — client-reported recommendation events (`search_click`, `booking_request` only).
- `POST /designs/{id}/ai/tag-suggestions`, `GET .../tag-suggestions`, `POST .../tag-suggestions/{id}/resolve`
- `POST /designs/{id}/ai/embeddings`
- `POST /designs/{id}/ai/moderation-check`
- `GET /designs/{id}/ai/similar` — any authenticated user, for a published design (or its owner/staff for an unpublished one).
- `GET /admin/ai/jobs` — job-queue visibility (`moderator`/`admin`/`super_admin`).
- `GET /admin/ai/review-queue`, `POST /admin/ai/review-queue/{id}/resolve` — moderator/admin can view, admin/super_admin can resolve.
- `GET /admin/ai/duplicate-matches`, `POST /admin/ai/duplicate-matches/{id}/resolve` — same role split.

Every design-scoped write endpoint (`tag-suggestions`, `embeddings`, `moderation-check`) requires the caller to own the design or hold a staff role (`app/api/routes/ai.py::_require_manage_permission`), and returns `503` if the relevant feature flag is off.

## CLI worker

`python -m app.cli.process_ai_jobs [--limit N] [--stuck-after-seconds N] [--dry-run]` — mirrors `app/cli/reconcile_payments.py`/`app/cli/process_subscriptions.py`'s shape exactly. Running more than one instance concurrently is safe (see `claim_due_jobs`'s `SKIP LOCKED` claim). `--dry-run` only covers the stuck-job requeue pass (rolled back); it does not cover `process_due_jobs`, since each claimed job is committed the instant it finishes as part of the queue's own crash-safety design, leaving nothing meaningful for a dry run to preview or discard.

## What this phase deliberately does not do

- **No image generation.** `AiGenerationType.GENERATIVE_DESIGN` is a recognized value with no handler behind it.
- **No real cloud AI provider.** `LocalHeuristicProvider` is genuine, working, and deterministic, but is explicitly a heuristic foundation, not a trained model.
- **No recommendation model.** Events are collected; nothing yet reads them to rank or recommend anything.
- **No auto-moderation.** A moderation flag never changes a design's publish status by itself; a human always decides.
- **No approximate-nearest-neighbor index.** Similarity search is a full O(n) scan, acceptable at this phase's scale.

## Related documents

- docs/subscriptions-and-entitlements.md — the quota system [AI quota enforcement](#ai-quota-enforcement-foundation) reuses.
- docs/community-and-trust.md — the human-review discipline [Human review](#human-review) mirrors.
- docs/payments.md — the reconciliation-command shape [Timeouts are soft](#timeouts-are-soft)'s `requeue_stuck_jobs` mirrors.
- docs/design-search.md, docs/design-catalog.md — the provider-abstraction and image-pipeline precedents this phase follows.

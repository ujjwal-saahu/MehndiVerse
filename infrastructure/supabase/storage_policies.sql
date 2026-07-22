-- MehndiVerse — Supabase Storage bucket & policy foundations (Phase 3)
--
-- This is a REFERENCE script, not an Alembic migration: Supabase Storage's
-- `storage.buckets` / `storage.objects` tables only exist on an actual
-- Supabase project (the storage extension), not on the vanilla
-- `postgres:16-alpine` container this repo's docker-compose.yml runs for
-- local development — running this against local Postgres would fail with
-- "relation storage.buckets does not exist". Run it against a real Supabase
-- project's SQL editor once one is provisioned.
--
-- No file upload endpoints exist yet (portfolio/verification-document upload
-- is Phase 4+) — this establishes the bucket layout and access rules ahead of
-- that work, per docs/authentication.md#5.
--
-- Convention: every object path is prefixed `{user_id}/...`, so ownership is
-- checkable from the path alone via `storage.foldername(name)`.

-- ---------------------------------------------------------------------------
-- Buckets
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    ('avatars', 'avatars', true, 5242880, array['image/png', 'image/jpeg', 'image/webp']),
    ('portfolio', 'portfolio', true, 10485760, array['image/png', 'image/jpeg', 'image/webp']),
    ('verification-documents', 'verification-documents', false, 10485760, array['image/png', 'image/jpeg', 'application/pdf']),
    ('chat-attachments', 'chat-attachments', false, 10485760, array['image/png', 'image/jpeg', 'image/webp']),
    ('preview-projects', 'preview-projects', false, 15728640, array['image/png', 'image/jpeg', 'image/webp']),
    ('ai-generated-designs', 'ai-generated-designs', false, 15728640, array['image/png', 'image/jpeg', 'image/webp'])
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- avatars — public read, owner-only write, path: {user_id}/{filename}
-- ---------------------------------------------------------------------------

create policy avatars_public_read on storage.objects
    for select using (bucket_id = 'avatars');

create policy avatars_owner_write on storage.objects
    for insert with check (
        bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy avatars_owner_update on storage.objects
    for update using (
        bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy avatars_owner_delete on storage.objects
    for delete using (
        bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ---------------------------------------------------------------------------
-- portfolio — public read (artist portfolio images are marketing content),
-- owner (artist) write. Path: {artist_user_id}/{filename}
-- ---------------------------------------------------------------------------

create policy portfolio_public_read on storage.objects
    for select using (bucket_id = 'portfolio');

create policy portfolio_owner_write on storage.objects
    for insert with check (
        bucket_id = 'portfolio' and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy portfolio_owner_update on storage.objects
    for update using (
        bucket_id = 'portfolio' and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy portfolio_owner_delete on storage.objects
    for delete using (
        bucket_id = 'portfolio' and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ---------------------------------------------------------------------------
-- verification-documents — private. Owner (artist) can upload/read their own;
-- staff (moderator/administrator/super_administrator) can read for review.
-- No update/delete once submitted — a re-submission is a new object, keeping
-- prior submissions as an audit trail (mirrors artist_documents' no-soft-
-- delete policy, see docs/database-schema.md#3).
-- ---------------------------------------------------------------------------

create policy verification_documents_owner_or_staff_read on storage.objects
    for select using (
        bucket_id = 'verification-documents'
        and ((storage.foldername(name))[1] = auth.uid()::text or app_is_staff())
    );

create policy verification_documents_owner_write on storage.objects
    for insert with check (
        bucket_id = 'verification-documents'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ---------------------------------------------------------------------------
-- chat-attachments — private. Readable/writable only by conversation members
-- (mirrors the `messages` RLS policy — see migrations/versions/
-- 3f28fa5a570a_auth_row_level_security_foundations.py).
-- ---------------------------------------------------------------------------

create policy chat_attachments_conversation_member_read on storage.objects
    for select using (
        bucket_id = 'chat-attachments'
        and exists (
            select 1 from conversation_members cm
            where cm.conversation_id::text = (storage.foldername(name))[1]
            and cm.user_id = auth.uid()
        )
    );

create policy chat_attachments_conversation_member_write on storage.objects
    for insert with check (
        bucket_id = 'chat-attachments'
        and exists (
            select 1 from conversation_members cm
            where cm.conversation_id::text = (storage.foldername(name))[1]
            and cm.user_id = auth.uid()
        )
    );

-- ---------------------------------------------------------------------------
-- preview-projects — private. Owner-only at the storage-policy level: these
-- are real photos of a customer's hand/foot, not marketing content. The
-- "artist the preview was shared with may also view it"
-- (preview_projects.shared_with_booking_id — see docs/hand-foot-preview.md
-- #send-to-artist) is enforced entirely in application code when minting a
-- signed URL, not here — clients never talk to Supabase Storage directly
-- (see app/integrations/supabase_storage.py's module docstring), so this
-- policy only matters as defense-in-depth against the service-role key
-- itself ever being used from a context that does respect RLS.
-- ---------------------------------------------------------------------------

create policy preview_projects_owner_read on storage.objects
    for select using (
        bucket_id = 'preview-projects'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy preview_projects_owner_write on storage.objects
    for insert with check (
        bucket_id = 'preview-projects'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy preview_projects_owner_delete on storage.objects
    for delete using (
        bucket_id = 'preview-projects'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ---------------------------------------------------------------------------
-- ai-generated-designs — private (Phase 21, docs/ai-design-assistant.md).
-- Owner-only at the storage-policy level, same shape as preview-projects:
-- these are a customer's personalized generation results, not catalog
-- marketing content. Written only by the background job worker (the
-- service-role key), never uploaded directly by a client, so there is no
-- owner-write policy here — only owner-read and owner-delete for when a
-- user removes an entry from their generation history. The "artist a result
-- was sent to may also view it" case (ai_design_requests.shared_with_
-- booking_id) is enforced in application code when minting a signed URL,
-- exactly like preview_projects' equivalent policy above.
-- ---------------------------------------------------------------------------

create policy ai_generated_designs_owner_read on storage.objects
    for select using (
        bucket_id = 'ai-generated-designs'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy ai_generated_designs_owner_delete on storage.objects
    for delete using (
        bucket_id = 'ai-generated-designs'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

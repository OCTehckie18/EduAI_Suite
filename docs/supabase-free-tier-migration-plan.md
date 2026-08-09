# Supabase free-tier database infrastructure migration plan

Status: planning only  
Branch: `plan/supabase-free-tier-migration`  
Baseline: current `development` tree, including pre-existing working-tree changes

## Outcome

Move authentication and file storage to Supabase while keeping MongoDB as the general application-data system of record and keeping the FastAPI boundary and both React applications stable:

- MongoDB/Beanie remains responsible for application data, including academic records, games, sessions, reports, and counters.
- Supabase Auth replaces the custom password/JWT issuer; MongoDB remains the profile/role/approval store and the API continues to enforce roles, approval state, and inactivity rules.
- Supabase Storage replaces local `/uploads`, MinIO, and the S3/AWS production path.
- WebSocket game flows remain API-owned and continue to use MongoDB for durable state. Supabase Realtime is out of scope for this migration.
- Local development uses MongoDB plus a local storage adapter; production uses MongoDB Atlas plus Supabase Auth/Storage and has no local-disk persistence.

## Free-tier guardrails

The design must enforce quotas rather than merely document them. For this option, the relevant Supabase Free limits are 1 GB Storage, 50 MB maximum file upload, 5 GB cached egress plus 5 GB uncached egress, and 50,000 monthly active Auth users. Free projects may pause after a week of inactivity and the organization is limited to two active projects. Verify these values in the Supabase dashboard before launch because plan limits can change.

Application safeguards:

1. Reject files over 45 MB at the API boundary, leaving headroom under the 50 MB platform limit; use resumable uploads only if a real upload requires it.
2. Store only metadata and references in MongoDB; never store binary file contents in MongoDB documents or Postgres.
3. Use private buckets and short-lived signed URLs for student submissions, OMR scans, reports, assignments, and templates. Use public access only for explicitly public assets.
4. Add a `storage_usage`/quota service that tracks bytes by bucket and tenant/user, rejects uploads when the configured soft limit is reached, and reports database/storage/egress usage.
5. Apply retention jobs for generated reports, temporary OMR artifacts, stale game sessions, and abandoned uploads. Do not delete user-owned source files without an explicit retention policy.
6. Avoid polling and duplicate downloads. Cache signed URLs briefly in clients and use immutable object keys rather than overwriting files.

## Current-state inventory

The backend currently initializes Motor/Beanie against MongoDB in `backend/app/database.py`, registers more than 30 document models, and generates sequential integer IDs from a Mongo `counters` collection. Authentication signs and verifies HS256 tokens in `backend/app/utils/auth.py` and then updates `User.last_active` on every request.

File persistence currently has three paths that must be unified:

- `backend/app/utils/file_uploads.py` writes directly to `backend/uploads` and returns `/uploads/...` URLs.
- `backend/app/services/storage_service.py` uses MinIO locally or AWS S3 when configured, with a local `local_uploads` fallback.
- `omr_routes.py`, `report_routes.py`, and other routes construct `/uploads/...` paths directly.

The main realtime surfaces are quiz, word cloud, Slido, and chain-answer WebSockets in `backend/app/routes/websocket_routes.py`; the frontend game synchronization hook is `apps/edugames/src/features/games/useGameSync.ts`.

## Target architecture

```text
React apps
  | Supabase Auth session + FastAPI bearer token
  v
FastAPI routes/services
  | existing Beanie/Motor repositories
  | storage adapter (Supabase Storage; local adapter in development)
  v
Supabase
  ├─ Auth: auth.users + JWT sessions
  ├─ Storage: private buckets + object metadata
  ├─ MongoDB Atlas: existing Beanie document collections
  ├─ Storage: private buckets + object metadata
  └─ FastAPI: business authorization and MongoDB access
```

Keep the Supabase service-role key server-side only. Browser clients use the publishable/anon key for Auth and Storage; they never receive a service-role credential or MongoDB connection string.

## MongoDB compatibility strategy

Do not rewrite the existing Beanie document model layer. Keep the current collections, embedded documents, integer IDs, counters, indexes, and Mongo-specific query behavior. The only general-data changes are:

- add `auth_user_id` to `User`, indexed and unique, mapping each Mongo profile to `auth.users.id`;
- preserve the existing `email`, role, status, approval, and `last_active` fields for application authorization;
- add a `file_objects` collection for Supabase Storage metadata and ownership, or add equivalent metadata fields to existing documents where the relationship is one-to-one;
- add migration scripts to backfill `auth_user_id` after Supabase Auth users are created;
- keep MongoDB Atlas backups, indexes, and connection-pool sizing within the selected MongoDB plan's limits.

No Mongo-to-Postgres data migration is required for this option.

## Phased implementation

### Phase 0 — baseline and measurement

- Record current Mongo collections, document counts, approximate BSON sizes, upload directory sizes, and the largest files.
- Capture route-level read/write behavior and all direct model/storage imports.
- Define retention, tenant ownership, role visibility, and whether existing data must be migrated or only new data.
- Add a migration ledger and repeatable export/checksum process; do not modify production data yet.

Exit criteria: inventory is complete, quota estimates fit within Free limits, and every model/file path has an owner in the plan.

### Phase 1 — provider boundaries

- Keep the existing Beanie/Motor repository behavior for CRUD, pagination, filtering, transactions, and ID compatibility.
- Add `backend/app/storage/` with `SupabaseStorageAdapter` and `LocalStorageAdapter`.
- Add typed settings for Supabase URL, publishable key, service-role key, bucket names, file-size limits, and retention settings.
- Replace direct filesystem writes and direct S3/MinIO calls behind the adapter, preserving current route response URLs during the transition.
- Add tests for path sanitization, content-type/extension validation, size limits, signed URL access, and failed-upload cleanup.

Exit criteria: no route needs to know whether storage is local, MinIO, S3, or Supabase.

### Phase 2 — Supabase Auth and identity bridge

- Create the Supabase project and configure Auth providers, redirect URLs, email settings, and environment secrets.
- Add `auth_user_id` to Mongo `User` documents and create a deterministic mapping/backfill command based on verified email and provider ID.
- Implement FastAPI Supabase JWT verification using the project JWKS or official auth client; map `sub` to Mongo `User` and retain the 15-minute inactivity check in application code.
- Migrate Google OAuth configuration to Supabase Auth providers; keep admin approval as application data/policy, not as a password-table concern.
- Keep password hashes in Mongo only during the transition; new password handling belongs to Supabase Auth. Define a reset/recovery path for legacy accounts before deleting old hashes.

Exit criteria: a new user can authenticate through Supabase, receive the same API authorization behavior, and cannot read another user's protected data through either REST or Storage.

### Phase 3 — file migration and route cutover

- Create separate private buckets, for example `user-submissions`, `course-materials`, `presentations`, `reports`, and `processing-temp`; keep bucket policies narrow.
- Upload existing files using stable, collision-resistant paths such as `{owner_id}/{entity}/{uuid}-{safe_name}`.
- Populate the Mongo `file_objects` metadata collection and update model references from `/uploads/...` to file-object IDs or API download endpoints.
- Make the API issue signed download URLs after authorization; never expose raw service-role URLs.
- Move direct OMR/report file reads to an adapter that streams/downloads from Storage and deletes temporary objects on completion.
- Replace frontend assumptions about static `/uploads` URLs with an API/storage URL helper.

Exit criteria: all upload routes work against Supabase Storage, all download paths enforce authorization, and the backend container can run without writable persistent disk.

### Phase 4 — operational hardening

- Keep FastAPI WebSockets and MongoDB for existing game behavior.
- Add MongoDB indexes, connection-pool sizing, query timeouts, pagination limits, and health checks.
- Add a scheduled cleanup/usage job and an admin usage endpoint with alerts at 60%, 80%, and 95% of configured quotas.
- Remove MinIO, AWS S3, local upload mounts, and direct filesystem paths only after a full rollback window. Keep MongoDB, Beanie, and Motor.

Exit criteria: staging and production smoke tests pass, quota alarms are observable, and the rollback procedure is tested.

## RLS and authorization rules

Supabase Storage policies must be the second line of defense; FastAPI remains the place for complex business authorization against MongoDB. Policies should cover:

- students can read/update only their own profile and permitted submissions;
- teachers can access only courses/classes they own or are assigned;
- admins can manage approvals and tenant-wide records;
- file objects are readable only by the owning user or an authorized course/class relationship;
- service-role access is limited to backend-only jobs and never used by browsers.

Test both API-mediated access and direct Supabase client access with anonymous, student, teacher, and admin JWTs.

## Verification and rollback

- Contract-test every existing route family before and after cutover.
- Add migration tests for nullability, enum conversion, timestamps, integer-ID compatibility, and nested game/Slido records.
- Add storage tests for upload, signed download, unauthorized download, duplicate path, oversize file, cleanup, and expiry.
- Load-test concurrent game sessions against the free-tier connection/message budgets.
- Use a feature flag for the Supabase Auth and Storage adapters; retain the current Mongo read/write path throughout the rollback window.
- Roll back by disabling the flag and restoring the old storage URL resolver. Do not attempt bidirectional writes after cutover unless a concrete conflict-resolution design exists.

## Planned deliverables

1. Supabase Auth configuration and Mongo-to-Supabase identity mapping command.
2. Backend Supabase Auth verifier, Storage adapter, quota, migration, and usage-monitoring modules.
3. File migration commands with dry-run, resume, reconciliation, and checksum output.
4. Updated frontend auth/session and file URL helpers.
5. Contract, integration, authorization, storage, migration, and quota tests.
6. Deployment configuration and a rollback/runbook document.

## Open decisions before implementation

- Is this a single-tenant deployment or must Mongo ownership fields support multiple institutions? The plan assumes tenant-ready ownership fields even if only one tenant is active.
- Must all existing Mongo data and files be retained, or may temporary/generated artifacts be pruned before migration?
- Which deployment host will run FastAPI and scheduled cleanup? Supabase Free covers the data plane, not arbitrary application compute.
- Which MongoDB deployment/plan will be used, and what are its storage, connection, backup, and egress limits?

## References

- Supabase database scope: https://supabase.com/docs/guides/database/overview
- Supabase Storage overview: https://supabase.com/docs/guides/storage
- Resumable and signed uploads: https://supabase.com/docs/guides/storage/uploads/resumable-uploads
- Storage bandwidth/egress accounting: https://supabase.com/docs/guides/storage/serving/bandwidth

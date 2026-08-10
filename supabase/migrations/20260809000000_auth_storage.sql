-- EduAI Auth/Storage foundation for Supabase project ahqabwehrbnieawsxxpd.
-- Application profiles and business data remain in MongoDB. Supabase Auth is
-- the identity provider and this bucket is accessed by the FastAPI service.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'edui-presentations',
  'edui-presentations',
  false,
  47185920,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'text/csv'
  ]
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- Direct browser access is denied by default. The backend uses the service-role
-- key for server-side uploads/downloads after enforcing MongoDB authorization.
drop policy if exists "authenticated users can read own objects" on storage.objects;
drop policy if exists "authenticated users can upload own objects" on storage.objects;
drop policy if exists "authenticated users can delete own objects" on storage.objects;
drop policy if exists "authenticated users can update own objects" on storage.objects;

create policy "authenticated users can read own objects"
on storage.objects for select
to authenticated
using (
  bucket_id = 'edui-presentations'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "authenticated users can upload own objects"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'edui-presentations'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "authenticated users can delete own objects"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'edui-presentations'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "authenticated users can update own objects"
on storage.objects for update
to authenticated
using (
  bucket_id = 'edui-presentations'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
)
with check (
  bucket_id = 'edui-presentations'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

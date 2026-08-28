create extension if not exists vector with schema extensions;

do $$ begin
  create type public.paper_reading_status as enum ('unread', 'reading', 'read');
exception when duplicate_object then null;
end $$;

do $$ begin
  create type public.paper_origin as enum ('upload', 'doi', 'arxiv', 'recommendation');
exception when duplicate_object then null;
end $$;

do $$ begin
  create type public.recommendation_action as enum ('saved', 'later', 'dismissed');
exception when duplicate_object then null;
end $$;

create table if not exists public.paper_profiles (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  interest_topics jsonb not null default '[]'::jsonb,
  exploration_ratio numeric(3, 2) not null default 0.20 check (exploration_ratio between 0 and 1),
  daily_count integer not null default 10 check (daily_count between 1 and 50),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.papers (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  slug text not null,
  title text not null,
  authors jsonb not null default '[]'::jsonb,
  abstract text,
  published_year integer,
  venue text,
  doi text,
  arxiv_id text,
  topic text,
  reading_status public.paper_reading_status not null default 'unread',
  origin public.paper_origin not null default 'upload',
  source_url text,
  pdf_storage_path text,
  analysis_storage_path text,
  is_in_library boolean not null default true,
  title_abstract_embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, slug),
  unique (owner_id, doi),
  unique (owner_id, arxiv_id)
);

create table if not exists public.paper_chunks (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  paper_id uuid not null references public.papers(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  unique (paper_id, chunk_index)
);

create table if not exists public.daily_recommendations (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  paper_id uuid not null references public.papers(id) on delete cascade,
  recommendation_date date not null,
  rank integer not null check (rank > 0),
  score numeric(5, 4),
  reason text,
  action public.recommendation_action,
  acted_at timestamptz,
  created_at timestamptz not null default now(),
  unique (owner_id, recommendation_date, rank),
  unique (owner_id, recommendation_date, paper_id)
);

create index if not exists papers_owner_created_idx on public.papers (owner_id, created_at desc);
create index if not exists papers_owner_status_idx on public.papers (owner_id, reading_status);
create index if not exists papers_title_search_idx on public.papers using gin (to_tsvector('simple', title));
create index if not exists paper_chunks_paper_idx on public.paper_chunks (paper_id, chunk_index);
create index if not exists recommendations_owner_date_idx on public.daily_recommendations (owner_id, recommendation_date desc, rank);

alter table public.paper_profiles enable row level security;
alter table public.papers enable row level security;
alter table public.paper_chunks enable row level security;
alter table public.daily_recommendations enable row level security;

drop policy if exists "owners manage their paper profile" on public.paper_profiles;
create policy "owners manage their paper profile"
  on public.paper_profiles for all to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
  with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

drop policy if exists "owners manage their papers" on public.papers;
create policy "owners manage their papers"
  on public.papers for all to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
  with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

drop policy if exists "owners manage their paper chunks" on public.paper_chunks;
create policy "owners manage their paper chunks"
  on public.paper_chunks for all to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
  with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

drop policy if exists "owners manage their recommendations" on public.daily_recommendations;
create policy "owners manage their recommendations"
  on public.daily_recommendations for all to authenticated
  using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
  with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.paper_profiles to authenticated;
grant select, insert, update, delete on public.papers to authenticated;
grant select, insert, update, delete on public.paper_chunks to authenticated;
grant select, insert, update, delete on public.daily_recommendations to authenticated;
grant usage, select on all sequences in schema public to authenticated;

revoke all on public.paper_profiles from anon;
revoke all on public.papers from anon;
revoke all on public.paper_chunks from anon;
revoke all on public.daily_recommendations from anon;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('papers', 'papers', false, 52428800, array['application/pdf', 'text/markdown', 'text/plain'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "owners read their paper files" on storage.objects;
create policy "owners read their paper files"
  on storage.objects for select to authenticated
  using (bucket_id = 'papers' and owner_id = (select auth.uid())::text and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "owners upload their paper files" on storage.objects;
create policy "owners upload their paper files"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'papers' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "owners update their paper files" on storage.objects;
create policy "owners update their paper files"
  on storage.objects for update to authenticated
  using (bucket_id = 'papers' and owner_id = (select auth.uid())::text and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'papers' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "owners delete their paper files" on storage.objects;
create policy "owners delete their paper files"
  on storage.objects for delete to authenticated
  using (bucket_id = 'papers' and owner_id = (select auth.uid())::text and (storage.foldername(name))[1] = (select auth.uid())::text);

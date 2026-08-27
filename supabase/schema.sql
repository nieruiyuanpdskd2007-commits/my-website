create extension if not exists vector with schema extensions;

create type public.paper_reading_status as enum ('unread', 'reading', 'read');
create type public.paper_origin as enum ('upload', 'doi', 'arxiv', 'recommendation');
create type public.recommendation_action as enum ('saved', 'later', 'dismissed');

create table public.paper_profiles (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  interest_topics jsonb not null default '[]'::jsonb,
  exploration_ratio numeric(3, 2) not null default 0.20 check (exploration_ratio between 0 and 1),
  daily_count integer not null default 10 check (daily_count between 1 and 50),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.papers (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
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
  unique (owner_id, doi),
  unique (owner_id, arxiv_id)
);

create table public.paper_chunks (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  paper_id uuid not null references public.papers(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  unique (paper_id, chunk_index)
);

create table public.daily_recommendations (
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

create index papers_owner_created_idx on public.papers (owner_id, created_at desc);
create index papers_owner_status_idx on public.papers (owner_id, reading_status);
create index papers_title_search_idx on public.papers using gin (to_tsvector('simple', title));
create index paper_chunks_paper_idx on public.paper_chunks (paper_id, chunk_index);
create index recommendations_owner_date_idx on public.daily_recommendations (owner_id, recommendation_date desc, rank);

alter table public.paper_profiles enable row level security;
alter table public.papers enable row level security;
alter table public.paper_chunks enable row level security;
alter table public.daily_recommendations enable row level security;

create policy "owners manage their paper profile"
  on public.paper_profiles for all
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

create policy "owners manage their papers"
  on public.papers for all
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

create policy "owners manage their paper chunks"
  on public.paper_chunks for all
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

create policy "owners manage their recommendations"
  on public.daily_recommendations for all
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

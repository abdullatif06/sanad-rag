-- Sanad: initial schema (workspaces, documents, chunks, evals) + hybrid search.
-- All access goes through the FastAPI backend using the service role key,
-- so RLS is enabled with no policies: anon/authenticated clients see nothing.

create extension if not exists vector with schema extensions;

-- Workspaces: one per client (or per demo visitor) ----------------------------
create table public.workspaces (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid references auth.users (id) on delete cascade,  -- null for demos
  name        text not null,
  public_key  text not null unique default replace(gen_random_uuid()::text, '-', ''),
  is_demo     boolean not null default false,
  created_at  timestamptz not null default now()
);
create index workspaces_owner_id_idx on public.workspaces (owner_id);
create index workspaces_demo_created_idx on public.workspaces (created_at) where is_demo;

-- Documents ---------------------------------------------------------------------
create table public.documents (
  id            uuid primary key default gen_random_uuid(),
  workspace_id  uuid not null references public.workspaces (id) on delete cascade,
  filename      text not null,
  status        text not null default 'processing'
                check (status in ('processing', 'ready', 'failed')),
  error         text,
  page_count    int,
  created_at    timestamptz not null default now()
);
create index documents_workspace_id_idx on public.documents (workspace_id);

-- Chunks: searchable pieces of documents ----------------------------------------
create table public.chunks (
  id                  bigint generated always as identity primary key,
  document_id         uuid not null references public.documents (id) on delete cascade,
  workspace_id        uuid not null references public.workspaces (id) on delete cascade,
  chunk_index         int not null,
  page                int not null,
  content             text not null,
  content_normalized  text not null,
  embedding           extensions.vector(768) not null,
  -- 'simple' = no stemming: good for exact names/numbers in both Arabic and English.
  fts                 tsvector generated always as (to_tsvector('simple', content_normalized)) stored,
  unique (document_id, chunk_index)
);
create index chunks_workspace_id_idx on public.chunks (workspace_id);
create index chunks_embedding_idx on public.chunks
  using hnsw (embedding extensions.vector_cosine_ops);
create index chunks_fts_idx on public.chunks using gin (fts);

-- Evaluations -------------------------------------------------------------------
create table public.eval_runs (
  id            uuid primary key default gen_random_uuid(),
  workspace_id  uuid not null references public.workspaces (id) on delete cascade,
  status        text not null default 'running'
                check (status in ('running', 'done', 'failed')),
  metrics       jsonb,
  created_at    timestamptz not null default now()
);
create index eval_runs_workspace_id_idx on public.eval_runs (workspace_id);

create table public.eval_items (
  id                 bigint generated always as identity primary key,
  run_id             uuid not null references public.eval_runs (id) on delete cascade,
  question           text not null,
  language           text not null,
  expected_chunk_id  bigint references public.chunks (id) on delete set null,
  answer             text,
  cited_chunk_ids    bigint[] not null default '{}',
  scores             jsonb
);
create index eval_items_run_id_idx on public.eval_items (run_id);
create index eval_items_expected_chunk_id_idx on public.eval_items (expected_chunk_id);

-- Lock everything down: backend only --------------------------------------------
alter table public.workspaces enable row level security;
alter table public.documents  enable row level security;
alter table public.chunks     enable row level security;
alter table public.eval_runs  enable row level security;
alter table public.eval_items enable row level security;

-- Hybrid search: vector similarity + keyword match, merged with
-- Reciprocal Rank Fusion (score = sum of 1 / (k + rank) across both lists).
create function public.hybrid_search(
  p_workspace_id     uuid,
  p_query_embedding  extensions.vector(768),
  p_query_text       text,
  p_match_count      int default 8,
  p_rrf_k            int default 60
)
returns table (
  id           bigint,
  document_id  uuid,
  page         int,
  content      text,
  score        double precision
)
language plpgsql
stable
set search_path = public, extensions, pg_catalog
as $$
declare
  -- OR the words together: a question rarely contains every word of the answer.
  v_query tsquery := replace(plainto_tsquery('simple', p_query_text)::text, '&', '|')::tsquery;
begin
  -- Keep scanning the HNSW index until enough rows match this workspace.
  perform set_config('hnsw.iterative_scan', 'relaxed_order', true);

  return query
  with semantic as (
    select c.id, row_number() over (order by c.embedding <=> p_query_embedding) as rank
    from chunks c
    where c.workspace_id = p_workspace_id
    order by c.embedding <=> p_query_embedding
    limit p_match_count * 2
  ),
  keyword as (
    select c.id, row_number() over (order by ts_rank_cd(c.fts, v_query) desc) as rank
    from chunks c
    where c.workspace_id = p_workspace_id and c.fts @@ v_query
    order by ts_rank_cd(c.fts, v_query) desc
    limit p_match_count * 2
  )
  select
    c.id,
    c.document_id,
    c.page,
    c.content,
    (coalesce(1.0 / (p_rrf_k + s.rank), 0) + coalesce(1.0 / (p_rrf_k + k.rank), 0))::double precision
  from semantic s
  full outer join keyword k on k.id = s.id
  join chunks c on c.id = coalesce(s.id, k.id)
  order by 5 desc
  limit p_match_count;
end;
$$;

revoke execute on function public.hybrid_search from public, anon, authenticated;

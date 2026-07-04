create table if not exists public.study_sessions (
  id uuid primary key default gen_random_uuid(),
  query_id text not null unique,
  mode text not null check (mode in ('auto', 'manual')),
  research_problem text not null,
  status text not null default 'created',
  last_error text,
  backend_snapshot jsonb not null default '{}'::jsonb,
  frontend_snapshot jsonb not null default '{}'::jsonb,
  export_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.study_session_events (
  id bigserial primary key,
  query_id text not null references public.study_sessions(query_id) on delete cascade,
  event_type text not null,
  stage text,
  step text,
  payload jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);

create index if not exists study_session_events_query_id_idx
  on public.study_session_events(query_id, occurred_at);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_study_sessions_updated_at on public.study_sessions;
create trigger set_study_sessions_updated_at
before update on public.study_sessions
for each row execute function public.set_updated_at();

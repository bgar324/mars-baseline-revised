alter table public.study_sessions
  add column if not exists condition text not null default 'mars';

alter table public.study_sessions
  drop constraint if exists study_sessions_condition_check;

alter table public.study_sessions
  add constraint study_sessions_condition_check
  check (condition in ('mars', 'baseline'));

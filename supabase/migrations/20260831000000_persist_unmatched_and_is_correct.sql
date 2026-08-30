-- Add is_correct column to questions and create unmatched_answers table

alter table public.questions
    add column if not exists is_correct boolean not null default false;

-- Backfill is_correct for legacy records
update public.questions
set is_correct = (case when max_marks > 0 then obtained_score >= max_marks else true end)
where is_correct = false;

create table if not exists public.unmatched_answers (
    id uuid primary key default gen_random_uuid(),
    assessment_id uuid not null references public.assessments(id) on delete cascade,
    answer_key varchar(64) not null,
    order_index integer not null default 0,
    page_number integer not null check (page_number >= 1),
    box_2d jsonb not null,
    transcribed_text text not null,
    reason text not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (assessment_id, answer_key)
);

create index if not exists idx_unmatched_answers_assessment
    on public.unmatched_answers (assessment_id, order_index);

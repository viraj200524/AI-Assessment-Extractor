-- VedaAI Assessment Extractor: PostgreSQL Schema Initialization
-- Run through the Supabase CLI or paste into the project's SQL editor.

create extension if not exists pgcrypto;

create table if not exists public.assessments (
    id uuid primary key default gen_random_uuid(),
    title varchar(255) not null default 'Untitled Assessment',
    question_paper_url text not null,
    answer_sheet_url text not null,
    page_count integer not null default 1 check (page_count > 0),
    total_score numeric(5, 2) not null default 0.00 check (total_score >= 0),
    max_score numeric(5, 2) not null default 0.00 check (max_score >= 0),
    percentage numeric(5, 2) not null default 0.00 check (percentage between 0 and 100),
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.questions (
    id uuid primary key default gen_random_uuid(),
    assessment_id uuid not null references public.assessments(id) on delete cascade,
    question_key varchar(50) not null,
    order_index integer not null default 0, -- printed sequence (FR-03); created_at is not a usable tiebreak
    full_label varchar(50) not null,
    question_text text not null,
    max_marks numeric(5, 2) not null default 0.00 check (max_marks >= 0),
    obtained_score numeric(5, 2) not null default 0.00 check (obtained_score between 0 and max_marks),
    status varchar(20) not null check (status in ('answered', 'unanswered', 'out_of_order')),
    is_correct boolean not null default false,
    transcribed_answer text,
    feedback text,
    answer_regions jsonb not null default '[]'::jsonb check (jsonb_typeof(answer_regions) = 'array'),
    created_at timestamptz not null default timezone('utc', now()),
    unique (assessment_id, question_key)
);

create index if not exists idx_questions_assessment_id on public.questions(assessment_id);
create index if not exists idx_questions_assessment_order on public.questions(assessment_id, order_index);

-- Extra or mislabelled student writing that maps to no question (FR-09).
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

-- Storage Buckets Configuration
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    ('question-papers', 'question-papers', false, 52428800, array['application/pdf', 'image/png', 'image/jpeg']),
    ('answer-sheets', 'answer-sheets', false, 52428800, array['application/pdf', 'image/png', 'image/jpeg'])
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

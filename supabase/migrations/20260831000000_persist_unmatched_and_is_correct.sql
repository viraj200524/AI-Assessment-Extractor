-- VedaAI Assessment Extractor: stop losing FR-09 and the examiner's correctness verdict.
--
-- 1. unmatched_answers (FR-09) was produced by the pipeline but never stored, so extra or
--    mislabelled student writing vanished the moment an assessment was reloaded.
-- 2. questions.is_correct was not stored either; it was re-derived on read as
--    obtained_score >= max_marks, which silently overrides the model on any partial credit
--    it judged substantially correct.

alter table public.questions
    add column if not exists is_correct boolean not null default false;

-- Backfill legacy rows with the same rule the read path used, so nothing changes for them.
update public.questions
set is_correct = (case when max_marks > 0 then obtained_score >= max_marks else true end)
where is_correct = false;

create table if not exists public.unmatched_answers (
    id uuid primary key default gen_random_uuid(),
    assessment_id uuid not null references public.assessments(id) on delete cascade,
    answer_key varchar(64) not null,          -- the pipeline's id, e.g. 'unmatched_1'
    order_index integer not null default 0,   -- preserves emission order on read
    page_number integer not null check (page_number >= 1),
    box_2d jsonb not null,                    -- { ymin, xmin, ymax, xmax } in Gemini 0-1000 space
    transcribed_text text not null,
    reason text not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (assessment_id, answer_key)
);

create index if not exists idx_unmatched_answers_assessment
    on public.unmatched_answers (assessment_id, order_index);

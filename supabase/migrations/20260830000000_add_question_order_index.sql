-- VedaAI Assessment Extractor: preserve printed question order at rest (FR-03).
--
-- Every question row in an assessment is written in a single batch, so they all share one
-- created_at value. Ordering by it is therefore an unspecified tiebreak that an
-- upsert-update can silently reshuffle. order_index records the printed sequence explicitly.

alter table public.questions
    add column if not exists order_index integer not null default 0;

create index if not exists idx_questions_assessment_order
    on public.questions (assessment_id, order_index);

-- Backfill rows written before this column existed. Their created_at values are identical,
-- so this locks in whatever order the id tiebreak gives - stable from here on, even if it
-- is not guaranteed to match the original printed sequence for those legacy rows.
with ordered as (
    select id, row_number() over (partition by assessment_id order by created_at, id) - 1 as position
    from public.questions
)
update public.questions as q
set order_index = ordered.position
from ordered
where q.id = ordered.id
  and q.order_index = 0;

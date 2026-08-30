-- Add explicit order_index column to questions table to preserve printed question sequence

alter table public.questions
    add column if not exists order_index integer not null default 0;

create index if not exists idx_questions_assessment_order
    on public.questions (assessment_id, order_index);

-- Backfill order_index for existing rows
with ordered as (
    select id, row_number() over (partition by assessment_id order by created_at, id) - 1 as position
    from public.questions
)
update public.questions as q
set order_index = ordered.position
from ordered
where q.id = ordered.id
  and q.order_index = 0;

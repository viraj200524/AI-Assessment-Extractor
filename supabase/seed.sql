-- Seed data for local Supabase testing

INSERT INTO public.assessments (id, title, question_paper_url, answer_sheet_url, page_count, total_score, max_score, percentage)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Physics Mid-Term Examination',
    'https://placeholder.supabase.co/storage/v1/object/public/question-papers/sample_qp.pdf',
    'https://placeholder.supabase.co/storage/v1/object/public/answer-sheets/sample_ans.pdf',
    3,
    18.00,
    25.00,
    72.00
) ON CONFLICT (id) DO NOTHING;

INSERT INTO public.questions (assessment_id, question_key, full_label, question_text, max_marks, obtained_score, status, transcribed_answer, feedback, answer_regions)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'q11_a',
    '11(a)',
    'State Newton''s Second Law of Motion.',
    2.00,
    2.00,
    'answered',
    'The rate of change of momentum of a body is directly proportional to the applied force.',
    'Clear and complete physical law definition provided.',
    '[{"page_number": 1, "box_2d": {"ymin": 120, "xmin": 80, "ymax": 260, "xmax": 920}}]'::jsonb
) ON CONFLICT (assessment_id, question_key) DO NOTHING;

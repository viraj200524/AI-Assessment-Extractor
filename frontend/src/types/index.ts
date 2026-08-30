export type QuestionStatus = "answered" | "unanswered" | "out_of_order";

export interface BoundingBox {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface AnswerRegion {
  page_number: number;
  box_2d: BoundingBox;
}

export interface Evaluation {
  score: number;
  max_marks: number;
  is_correct: boolean;
  feedback: string;
}

export interface QuestionItem {
  id: string;
  number: string;
  subpart?: string | null;
  full_label: string;
  text: string;
  max_marks: number;
  status: QuestionStatus;
  transcribed_answer?: string | null;
  evaluation: Evaluation;
  answer_regions: AnswerRegion[];
}

export interface UnmatchedAnswer {
  id: string;
  page_number: number;
  box_2d: BoundingBox;
  transcribed_text: string;
  reason: string;
}

export interface JobStage {
  key: string;
  label: string;
}

export type JobState = "queued" | "running" | "succeeded" | "failed";

/** Current snapshot of a parsing job returned by status or event stream. */
export interface JobStatus {
  job_id: string;
  state: JobState;
  stages: JobStage[];
  stage_index: number;
  stage_key: string;
  stage_label: string;
  detail: string | null;
  progress: number;
  assessment_id: string | null;
  persisted: boolean;
  error: string | null;
  error_status: number | null;
}

export interface AssessmentData {
  assessment_id: string;
  total_score: number;
  max_possible_score: number;
  percentage: number;
  questions: QuestionItem[];
  unmatched_answers: UnmatchedAnswer[];
}

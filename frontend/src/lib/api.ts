import { accessKeyHeaders } from "@/lib/accessKey";
import type { AssessmentData, JobStatus } from "@/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function documentFormData(questionPaper: File, answerSheet: File): FormData {
  const formData = new FormData();
  formData.append("question_paper", questionPaper);
  formData.append("answer_sheet", answerSheet);
  return formData;
}

/**
 * One-shot parse. Kept for parity with the backend, but it reports no progress and can
 * exceed platform request timeouts on longer documents — the UI uses the job flow below.
 */
export async function parseAssessment(questionPaper: File, answerSheet: File): Promise<AssessmentData> {
  const response = await fetch(`${apiBaseUrl}/parse`, {
    method: "POST",
    headers: accessKeyHeaders(),
    body: documentFormData(questionPaper, answerSheet),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? "The assessment could not be processed.");
  }
  return body as AssessmentData;
}

/** Upload both documents and start the pipeline in the background. */
export async function createParseJob(questionPaper: File, answerSheet: File): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/parse/jobs`, {
    method: "POST",
    headers: accessKeyHeaders(),
    body: documentFormData(questionPaper, answerSheet),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? "The assessment could not be submitted for processing.");
  }
  return body as JobStatus;
}

/**
 * Follow a job to completion, invoking `onStatus` on every stage transition.
 *
 * Prefers Server-Sent Events and falls back to polling if the stream cannot be opened
 * (some corporate proxies and older Safari builds buffer or drop text/event-stream).
 * Resolves with the terminal status; rejects with the server's specific error message.
 */
export function watchParseJob(
  jobId: string,
  onStatus: (status: JobStatus) => void,
  options: { signal?: AbortSignal; pollIntervalMs?: number } = {}
): Promise<JobStatus> {
  const { signal, pollIntervalMs = 1000 } = options;

  return new Promise<JobStatus>((resolve, reject) => {
    let settled = false;
    let source: EventSource | null = null;
    let pollTimer: number | null = null;

    const cleanup = () => {
      source?.close();
      source = null;
      if (pollTimer !== null) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }
    };

    const succeed = (status: JobStatus) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(status);
    };

    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };

    const handle = (status: JobStatus) => {
      if (settled) return;
      onStatus(status);
      if (status.state === "succeeded") succeed(status);
      else if (status.state === "failed") fail(new Error(status.error ?? "Processing failed."));
    };

    if (signal) {
      if (signal.aborted) {
        fail(new Error("Processing was cancelled."));
        return;
      }
      signal.addEventListener("abort", () => fail(new Error("Processing was cancelled.")), { once: true });
    }

    const startPolling = () => {
      source?.close();
      source = null;

      const tick = async () => {
        if (settled) return;
        try {
          const response = await fetch(`${apiBaseUrl}/parse/jobs/${jobId}`);
          if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new Error(body?.detail ?? "Lost contact with the processing job.");
          }
          handle((await response.json()) as JobStatus);
          if (!settled) pollTimer = window.setTimeout(tick, pollIntervalMs);
        } catch (error) {
          fail(error instanceof Error ? error : new Error("Lost contact with the processing job."));
        }
      };

      void tick();
    };

    try {
      source = new EventSource(`${apiBaseUrl}/parse/jobs/${jobId}/events`);
      source.addEventListener("status", (event) => {
        try {
          handle(JSON.parse((event as MessageEvent<string>).data) as JobStatus);
        } catch {
          fail(new Error("Received an unreadable progress update."));
        }
      });
      source.addEventListener("expired", () => fail(new Error("This processing job expired.")));
      // Also fires when the server closes the stream after a terminal event; the `settled`
      // guard means that path is already resolved and this becomes a no-op.
      source.onerror = () => {
        if (!settled) startPolling();
      };
    } catch {
      startPolling();
    }
  });
}

/** Collect the finished assessment once its job has succeeded. */
export async function getParseJobResult(jobId: string): Promise<AssessmentData> {
  const response = await fetch(`${apiBaseUrl}/parse/jobs/${jobId}/result`);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? "The processed assessment could not be retrieved.");
  }
  return body as AssessmentData;
}

export interface HealthStatus {
  status: string;
  environment: string;
  supabase_configured: boolean;
  gemini_configured: boolean;
  /** True when this deployment gates writes behind a shared key. */
  access_key_required: boolean;
}

export async function getHealth(): Promise<HealthStatus | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`);
    if (!response.ok) return null;
    return (await response.json()) as HealthStatus;
  } catch {
    return null;
  }
}

export interface FetchedAssessmentResponse {
  assessment: AssessmentData;
  answer_document_url: string;
  answer_document_type: string;
}

export async function getAssessmentById(assessmentId: string): Promise<FetchedAssessmentResponse> {
  const response = await fetch(`${apiBaseUrl}/assessments/${assessmentId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? "Failed to load assessment.");
  }
  return body as FetchedAssessmentResponse;
}

export interface AssessmentSummaryItem {
  id: string;
  title: string;
  page_count: number;
  total_score: number;
  max_score: number;
  percentage: number;
  created_at: string;
}

export async function listAssessments(): Promise<AssessmentSummaryItem[]> {
  const response = await fetch(`${apiBaseUrl}/assessments`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as AssessmentSummaryItem[];
}

export async function deleteAssessmentById(assessmentId: string): Promise<boolean> {
  const response = await fetch(`${apiBaseUrl}/assessments/${assessmentId}`, {
    method: "DELETE",
    headers: accessKeyHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "The assessment could not be deleted.");
  }
  return true;
}

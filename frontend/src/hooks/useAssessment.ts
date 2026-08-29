"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createParseJob, getParseJobResult, watchParseJob } from "@/lib/api";
import { useAssessmentStore } from "@/store/useAssessmentStore";
import type { JobStage } from "@/types";

/**
 * Fallback stage list rendered before the server's first status frame arrives.
 * The server is authoritative: every status update carries its own `stages` array.
 */
export const DEFAULT_STAGES: JobStage[] = [
  { key: "uploading", label: "Uploading documents" },
  { key: "rasterizing", label: "Rasterizing pages" },
  { key: "parsing_questions", label: "Parsing questions" },
  { key: "grounding_answers", label: "Grounding answers" },
  { key: "persisting", label: "Saving results" },
];

export function useAssessment() {
  const router = useRouter();
  const setAssessmentSession = useAssessmentStore((state) => state.setAssessmentSession);

  const [questionPaper, setQuestionPaper] = useState<File | null>(null);
  const [answerSheet, setAnswerSheet] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stages, setStages] = useState<JobStage[]>(DEFAULT_STAGES);
  const [currentStage, setCurrentStage] = useState(-1);
  const [stageDetail, setStageDetail] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const processAssessment = useCallback(async () => {
    if (!questionPaper || !answerSheet) {
      setError("Please select both a question paper and student answer sheet.");
      return;
    }

    setError(null);
    setIsProcessing(true);
    setStages(DEFAULT_STAGES);
    setCurrentStage(0);
    setStageDetail("Uploading documents");
    setProgress(0);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const job = await createParseJob(questionPaper, answerSheet);
      setStages(job.stages);
      setCurrentStage(job.stage_index);
      setProgress(job.progress);

      // Every update below reflects real server-side pipeline state, not a timer.
      await watchParseJob(
        job.job_id,
        (status) => {
          setStages(status.stages);
          setCurrentStage(status.stage_index);
          setStageDetail(status.detail ?? status.stage_label);
          setProgress(status.progress);
        },
        { signal: controller.signal }
      );

      const assessmentData = await getParseJobResult(job.job_id);
      const answerDocUrl = URL.createObjectURL(answerSheet);

      setAssessmentSession(assessmentData, answerDocUrl, answerSheet.type);
      router.push(`/assessment/${assessmentData.assessment_id}`);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Processing failed. Please check your backend connection and try again."
      );
      setCurrentStage(-1);
      setStageDetail(null);
      setProgress(0);
    } finally {
      abortRef.current = null;
      setIsProcessing(false);
    }
  }, [questionPaper, answerSheet, router, setAssessmentSession]);

  const cancelProcessing = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    questionPaper,
    setQuestionPaper,
    answerSheet,
    setAnswerSheet,
    isProcessing,
    currentStage,
    stageDetail,
    progress,
    error,
    processAssessment,
    cancelProcessing,
    stages,
  };
}

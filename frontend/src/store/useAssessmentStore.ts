"use client";

import { create } from "zustand";

import type { AssessmentData } from "@/types";

interface AssessmentStore {
  assessment: AssessmentData | null;
  answerDocumentUrl: string | null;
  answerDocumentType: string | null;
  activeQuestionId: string | null;
  setAssessmentSession: (assessment: AssessmentData, documentUrl: string, documentType: string) => void;
  setActiveQuestionId: (questionId: string | null) => void;
  clearSession: () => void;
}

export const useAssessmentStore = create<AssessmentStore>((set) => ({
  assessment: null,
  answerDocumentUrl: null,
  answerDocumentType: null,
  activeQuestionId: null,
  setAssessmentSession: (assessment, answerDocumentUrl, answerDocumentType) =>
    set({ assessment, answerDocumentUrl, answerDocumentType, activeQuestionId: assessment.questions[0]?.id ?? null }),
  setActiveQuestionId: (activeQuestionId) => set({ activeQuestionId }),
  clearSession: () => set({ assessment: null, answerDocumentUrl: null, answerDocumentType: null, activeQuestionId: null }),
}));

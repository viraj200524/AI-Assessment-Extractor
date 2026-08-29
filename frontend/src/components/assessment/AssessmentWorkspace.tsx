"use client";

import React from "react";
import { DocumentViewer } from "@/components/assessment/DocumentViewer";
import { QuestionListPanel } from "@/components/assessment/QuestionListPanel";
import { SummaryHeaderBar } from "@/components/assessment/SummaryHeaderBar";
import { useAssessmentStore } from "@/store/useAssessmentStore";

export function AssessmentWorkspace() {
  const {
    assessment,
    answerDocumentUrl,
    answerDocumentType,
    activeQuestionId,
    setActiveQuestionId,
  } = useAssessmentStore();

  if (!assessment || !answerDocumentUrl || !answerDocumentType) {
    return null;
  }

  return (
    <main className="app-shell flex h-screen w-screen overflow-hidden flex-col bg-slate-100">
      {/* Top Header Summary Bar */}
      <SummaryHeaderBar assessment={assessment} />

      {/* Split-View Dual Panel Workspace (Full Screen Height) */}
      <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(360px,35%)_1fr]">
        {/* Left Panel: Question Navigation Sidebar (Full Screen Length) */}
        <QuestionListPanel
          questions={assessment.questions}
          unmatchedAnswers={assessment.unmatched_answers}
          activeQuestionId={activeQuestionId}
          onSelectQuestion={setActiveQuestionId}
        />

        {/* Right Panel: Interactive Document Canvas Viewer (65% Width) */}
        <section className="flex h-full min-h-0 flex-col overflow-hidden">
          <DocumentViewer
            documentUrl={answerDocumentUrl}
            documentType={answerDocumentType}
            questions={assessment.questions}
            activeQuestionId={activeQuestionId}
          />
        </section>
      </div>
    </main>
  );
}

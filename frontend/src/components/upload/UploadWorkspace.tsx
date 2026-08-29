"use client";

import React from "react";
import { FileText, Sparkles, AlertCircle } from "lucide-react";
import { AccessKeyField } from "@/components/AccessKeyField";
import { FileDropzone } from "@/components/upload/FileDropzone";
import { ProcessingProgress } from "@/components/upload/ProcessingProgress";
import { useAssessment } from "@/hooks/useAssessment";

export function UploadWorkspace() {
  const {
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
    stages,
  } = useAssessment();

  return (
    <main className="app-shell hero-grid flex items-center justify-center px-5 py-12">
      <div className="w-full max-w-5xl rounded-3xl border border-slate-200/90 bg-white/95 p-7 panel-shadow sm:p-10 backdrop-blur-xs">
        {/* Header Hero Section */}
        <div className="mx-auto max-w-2xl text-center">
          <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-navy text-white shadow-md">
            <Sparkles size={28} className="text-blue-400" />
          </div>
          <p className="text-xs font-bold uppercase tracking-[.18em] text-blue-600">
            VedaAI Educator Assessment Suite
          </p>
          <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            AI Assessment Extraction &amp; Answer Mapping
          </h1>
          <p className="mt-3.5 text-base leading-7 text-slate-600">
            Upload the printed question paper alongside the student&apos;s handwritten answer sheet.
            VedaAI extracts questions, maps handwritten answers with spatial 2D bounding boxes, and automatically evaluates responses.
          </p>
        </div>

        {/* Ingestion Dual Dropzone */}
        <div className="mt-9 grid gap-6 md:grid-cols-2">
          <FileDropzone
            label="Printed Question Paper"
            description="Upload the official question paper (PDF or images) in its original printed order."
            file={questionPaper}
            onChange={setQuestionPaper}
          />
          <FileDropzone
            label="Student Answer Sheet"
            description="Upload the student's handwritten answer sheet (multi-page PDF or images)."
            file={answerSheet}
            onChange={setAnswerSheet}
          />
        </div>

        {/* Multi-Stage Loading Progress Indicator */}
        {isProcessing && (
          <ProcessingProgress
            currentStage={currentStage}
            stages={stages}
            detail={stageDetail}
            progress={progress}
          />
        )}

        {/* Error Alert */}
        {error && (
          <div
            role="alert"
            className="mt-6 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-800"
          >
            <AlertCircle size={18} className="shrink-0 text-rose-600 mt-0.5" />
            <div>
              <p className="font-bold">Extraction Pipeline Error</p>
              <p className="mt-0.5 text-xs text-rose-700">{error}</p>
            </div>
          </div>
        )}

        {/* Submit Action */}
        <div className="mt-8 flex flex-col items-center gap-3 border-t border-slate-100 pt-7">
          {/* Only rendered when the deployment gates writes behind a shared key. */}
          <AccessKeyField className="mb-1 w-full justify-center" />
          <button
            type="button"
            disabled={isProcessing || !questionPaper || !answerSheet}
            onClick={processAssessment}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-7 py-3.5 font-bold text-white shadow-md transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
          >
            <FileText size={19} />
            <span>{isProcessing ? "Processing Assessment..." : "Extract, Map & Evaluate"}</span>
          </button>
          <p className="text-center text-xs text-slate-400">
            Powered by PyMuPDF rasterization &amp; Google Gemini 3.6 Flash Vision spatial grounding.
          </p>
        </div>
      </div>
    </main>
  );
}

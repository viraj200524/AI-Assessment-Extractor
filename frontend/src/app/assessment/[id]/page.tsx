"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, LoaderCircle } from "lucide-react";
import { AssessmentWorkspace } from "@/components/assessment/AssessmentWorkspace";
import { getAssessmentById } from "@/lib/api";
import { useAssessmentStore } from "@/store/useAssessmentStore";

export default function AssessmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { assessment, setAssessmentSession } = useAssessmentStore();
  const [loading, setLoading] = useState<boolean>(!assessment || assessment.assessment_id !== id);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If session is already loaded in Zustand for this ID, no need to refetch
    if (assessment && assessment.assessment_id === id) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function loadAssessment() {
      setLoading(true);
      setError(null);

      try {
        const data = await getAssessmentById(id);
        if (!cancelled) {
          setAssessmentSession(
            data.assessment,
            data.answer_document_url,
            data.answer_document_type || "application/pdf"
          );
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Unable to load the requested assessment."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAssessment();

    return () => {
      cancelled = true;
    };
  }, [id, assessment, setAssessmentSession]);

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 p-6 text-center">
        <div className="flex flex-col items-center gap-3">
          <LoaderCircle className="animate-spin text-blue-600" size={36} />
          <h2 className="text-base font-bold text-ink">Loading Assessment Session...</h2>
          <p className="text-xs text-slate-500">Retrieving mapped questions and document assets.</p>
        </div>
      </main>
    );
  }

  if (error || !assessment) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 p-6 text-center">
        <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-rose-50 text-rose-600">
            <AlertCircle size={24} />
          </div>
          <h1 className="text-xl font-bold text-ink">Assessment Unavailable</h1>
          <p className="mt-2 text-xs text-slate-600 leading-relaxed">
            {error || "This review session could not be found or has expired."}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700"
            >
              <ArrowLeft size={14} />
              <span>Start New Assessment</span>
            </Link>
            <Link
              href="/history"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-100"
            >
              <span>View History</span>
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return <AssessmentWorkspace />;
}

"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Download, Award } from "lucide-react";
import type { AssessmentData } from "@/types";

interface SummaryHeaderBarProps {
  assessment: AssessmentData;
  title?: string;
}

export function SummaryHeaderBar({ assessment, title = "Assessment Review" }: SummaryHeaderBarProps) {
  const handleExport = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  const getScoreBadgeClass = (pct: number) => {
    if (pct >= 75) return "bg-emerald-500 text-white";
    if (pct >= 50) return "bg-blue-600 text-white";
    return "bg-amber-500 text-white";
  };

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-3.5 sm:px-7">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          title="Return to Upload"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600">
              VedaAI Evaluation
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs font-semibold text-slate-500">{title}</span>
          </div>
          <h1 className="text-lg font-bold text-ink sm:text-xl">
            Interactive Answer Mapping &amp; Grading
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-3 rounded-xl bg-slate-900 px-4 py-2 text-white shadow-sm">
          <Award size={20} className="text-amber-400" />
          <div>
            <div className="text-[11px] font-medium text-slate-400">Total Score</div>
            <div className="flex items-center gap-1.5 font-bold">
              <span>{assessment.total_score}</span>
              <span className="text-slate-400">/</span>
              <span>{assessment.max_possible_score} marks</span>
              <span
                className={`ml-1.5 rounded-full px-2 py-0.5 text-xs font-extrabold ${getScoreBadgeClass(
                  assessment.percentage
                )}`}
              >
                {assessment.percentage}%
              </span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:border-slate-300"
          title="Print or Export Evaluation Report"
        >
          <Download size={15} />
          <span>Export PDF</span>
        </button>
      </div>
    </header>
  );
}

"use client";

import React from "react";
import { CheckCircle2, ChevronRight, HelpCircle, XCircle } from "lucide-react";
import type { QuestionItem, QuestionStatus } from "@/types";

const statusConfig: Record<QuestionStatus, { label: string; badgeClass: string; icon: React.ReactNode }> = {
  answered: {
    label: "Answered",
    badgeClass: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    icon: <CheckCircle2 size={13} className="text-emerald-600" />,
  },
  unanswered: {
    label: "Unanswered",
    badgeClass: "bg-rose-50 text-rose-700 ring-rose-200",
    icon: <XCircle size={13} className="text-rose-600" />,
  },
  out_of_order: {
    label: "Out of order",
    badgeClass: "bg-violet-50 text-violet-700 ring-violet-200",
    icon: <HelpCircle size={13} className="text-violet-600" />,
  },
};

interface QuestionCardProps {
  question: QuestionItem;
  isActive: boolean;
  onSelect: (id: string) => void;
}

export function QuestionCard({ question, isActive, onSelect }: QuestionCardProps) {
  const status = statusConfig[question.status] ?? statusConfig.unanswered;

  return (
    <button
      type="button"
      onClick={() => onSelect(question.id)}
      className={`w-full rounded-xl border p-4 text-left transition-all ${
        isActive
          ? "border-blue-500 bg-blue-50/70 shadow-sm ring-1 ring-blue-400/50"
          : "border-slate-200 bg-white hover:border-blue-200 hover:bg-slate-50/50"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-extrabold text-navy">Q {question.full_label}</span>
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ${status.badgeClass}`}>
            {status.icon}
            {status.label}
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs font-bold text-slate-700">
          <span className={question.evaluation.score > 0 ? "text-blue-700" : "text-slate-500"}>
            {question.evaluation.score}
          </span>
          <span className="text-slate-400">/</span>
          <span>{question.max_marks} marks</span>
        </div>
      </div>

      <p className="mt-2 text-sm leading-5 text-slate-700 font-medium line-clamp-3">
        {question.text}
      </p>

      {question.transcribed_answer && (
        <div className="mt-2.5 rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600 border border-slate-100">
          <span className="font-semibold text-slate-500 block mb-0.5">Student Answer:</span>
          <p className="italic line-clamp-2">&ldquo;{question.transcribed_answer}&rdquo;</p>
        </div>
      )}

      <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2 text-xs">
        <p className="text-slate-500 line-clamp-2 flex-1 pr-2">
          <strong className="text-slate-600 font-semibold">Feedback: </strong>
          {question.evaluation.feedback}
        </p>
        <ChevronRight size={16} className={isActive ? "text-blue-600 shrink-0" : "text-slate-400 shrink-0"} />
      </div>
    </button>
  );
}

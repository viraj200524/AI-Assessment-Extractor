"use client";

import React, { useMemo, useState } from "react";
import { FileWarning, Filter } from "lucide-react";
import { FilterOption, FilterPills } from "@/components/assessment/FilterPills";
import { QuestionCard } from "@/components/assessment/QuestionCard";
import type { QuestionItem, UnmatchedAnswer } from "@/types";

interface QuestionListPanelProps {
  questions: QuestionItem[];
  unmatchedAnswers: UnmatchedAnswer[];
  activeQuestionId: string | null;
  onSelectQuestion: (id: string) => void;
}

export function QuestionListPanel({
  questions,
  unmatchedAnswers,
  activeQuestionId,
  onSelectQuestion,
}: QuestionListPanelProps) {
  const [filter, setFilter] = useState<FilterOption>("all");

  const visibleQuestions = useMemo(() => {
    if (filter === "all") return questions;
    return questions.filter((q) => q.status === filter);
  }, [questions, filter]);

  return (
    <aside className="scrollbar-thin flex h-full min-h-0 flex-col overflow-y-auto border-b border-slate-200 bg-white lg:border-b-0 lg:border-r shadow-xs">
      <div className="sticky top-0 z-10 border-b border-slate-100 bg-white px-5 py-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-ink">
            <Filter size={16} className="text-blue-600" />
            <span>Questions ({questions.length})</span>
          </div>
          <span className="text-xs font-semibold text-slate-400">
            {visibleQuestions.length} shown
          </span>
        </div>
        <FilterPills
          currentFilter={filter}
          onFilterChange={setFilter}
          questions={questions}
        />
      </div>

      <div className="space-y-3 p-4 flex-1">
        {visibleQuestions.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">
            No questions match the current filter.
          </div>
        ) : (
          visibleQuestions.map((question) => (
            <QuestionCard
              key={question.id}
              question={question}
              isActive={activeQuestionId === question.id}
              onSelect={onSelectQuestion}
            />
          ))
        )}
      </div>

      {unmatchedAnswers.length > 0 && (
        <div className="mx-4 mb-5 rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-800">
          <div className="flex items-center gap-2 font-bold text-amber-900">
            <FileWarning size={17} />
            <span>
              {unmatchedAnswers.length} Unmatched Response{unmatchedAnswers.length === 1 ? "" : "s"}
            </span>
          </div>
          <p className="mt-1 text-xs text-amber-700 leading-relaxed">
            Additional student handwriting was detected that could not be mapped to any question item.
          </p>
          <div className="mt-2 space-y-1.5 border-t border-amber-200/60 pt-2">
            {unmatchedAnswers.map((item, idx) => (
              <div key={item.id || idx} className="text-xs">
                <span className="font-semibold">Page {item.page_number}:</span> &ldquo;{item.transcribed_text}&rdquo;
                <span className="text-amber-600 block italic">{item.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
